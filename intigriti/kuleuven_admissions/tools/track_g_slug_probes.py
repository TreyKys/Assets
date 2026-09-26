#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track G — G2.1 filename injection + G2.2 doc-type routing.

G1 verified:
  * Server rejects non-image MIMEs (SVG/HTML/XHTML → 400).
  * Server accepts valid JPEG (baseline restore → 201).
  * Server normalizes/re-encodes bytes on JPEG upload (4-byte diff).
  * Served Content-Type is `image/jpeg`, `nosniff`, `attachment` disposition.

G2 uses a valid minimal JPEG for every probe (so MIME allowlist passes),
varying only:
  G2.1: the FILENAME half of `slug: ZCM_ADM027|<filename>`
  G2.2: the DOCTYPE half of `slug: <doctype>|klg_g2.jpg`

Budget: 4 non-safe upload probes + 4 metadata reads + 1 baseline read
(safe) + 1 final restore = 5 non-safe. Well under 10 cap given the
prior G1 run used ~4 non-safe (need fresh egress if we roll over).

Cleanup: restore A's original photo bytes at the very end.
"""
import argparse
import json
import os
import sys
import ssl
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m

EVIDENCE_DIR = "intigriti/kuleuven_admissions/vm-results/06-track-g-evidence"
UPLOAD_URL = f"https://{m.ALLOWED_HOST}/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/ApplicantPhotos?sap-client=200"
ENTITY_URL = f"https://{m.ALLOWED_HOST}/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/ApplicantPhotos('0')?sap-client=200"
VALUE_URL  = f"https://{m.ALLOWED_HOST}/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/ApplicantPhotos('0')/$value?sap-client=200"

# Use the G1.0 baseline photo bytes as the "valid JPEG body" for G2 probes.
# Loaded lazily in main() from vm-results/06-track-g-evidence/g1_0_baseline_photo.bin
MINIMAL_JPEG = None  # set at runtime

_ssl_ctx = ssl.create_default_context()


def raw_get_binary(session, url, timeout=30):
    time.sleep(m.MIN_INTERVAL)
    req = urllib.request.Request(url, method="GET",
                                  headers={"Accept": "*/*",
                                           "Cookie": session.cookie_header})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx)
        return resp.getcode(), dict(resp.getheaders()), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items() if e.headers else {}), \
               (e.read() if e.fp else b"")


def raw_upload(session, blob_bytes, content_type, slug, timeout=30):
    time.sleep(m.MIN_INTERVAL)
    csrf = session.csrf or "Fetch"
    headers = {
        "Accept": "application/json",
        "Cookie": session.cookie_header,
        "Content-Type": content_type,
        "slug": slug,
        "x-csrf-token": csrf,
    }
    req = urllib.request.Request(UPLOAD_URL, data=blob_bytes, method="POST",
                                  headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx)
        return resp.getcode(), dict(resp.getheaders()), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items() if e.headers else {}), \
               (e.read() if e.fp else b"")


def probe_upload(sA, label, slug, logger):
    """Upload minimal JPEG with the given slug. Read back metadata."""
    print(f"\n=== {label} — slug={slug!r} ===", file=sys.stderr)
    st_u, hdr_u, body_u = raw_upload(sA, MINIMAL_JPEG, "image/jpeg", slug)
    logger.log("g2", "ApplicantPhotos", "POST (upload)",
               f"{label} slug={slug!r}",
               {"status": st_u, "text": ""},
               [f"upload_status={st_u}",
                f"resp_len={len(body_u)}"])
    # Try to parse response body — SAP returns the created entity JSON on 201
    try:
        rj = json.loads(body_u.decode("utf-8"))
        d = rj.get("d", {})
    except Exception:
        d = {"parse_error": True,
             "raw": body_u[:400].decode(errors="replace")}
    fn_returned = d.get("fileName") if isinstance(d, dict) else None
    dt_returned = d.get("docType") if isinstance(d, dict) else None
    mt_returned = d.get("mimetype") if isinstance(d, dict) else None
    logger.log("g2", "ApplicantPhotos", "COMPARE",
               f"{label} response metadata",
               {"status": "n/a", "text": ""},
               [f"upload_status={st_u}",
                f"fileName_returned={fn_returned!r}",
                f"docType_returned={dt_returned!r}",
                f"mimetype_returned={mt_returned!r}"])
    save_response(f"{EVIDENCE_DIR}/g2_{label}_response.json", d)
    # Also read the entity metadata via GET
    st_e, hdr_e, body_e = raw_get_binary(sA, ENTITY_URL)
    try:
        ej = json.loads(body_e.decode("utf-8")).get("d", {})
    except Exception:
        ej = {}
    logger.log("g2", "ApplicantPhotos('0')", "GET (entity)",
               f"{label} entity readback",
               {"status": st_e, "text": ""},
               [f"read_status={st_e}",
                f"fileName={ej.get('fileName')!r}",
                f"docType={ej.get('docType')!r}",
                f"mimetype={ej.get('mimetype')!r}"])
    save_response(f"{EVIDENCE_DIR}/g2_{label}_entity_after.json", ej)
    return {"upload_status": st_u,
            "fn_returned": fn_returned,
            "dt_returned": dt_returned,
            "mt_returned": mt_returned,
            "entity_after": ej}


def save_response(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


def load_baseline_bytes():
    p = f"{EVIDENCE_DIR}/g1_0_baseline_photo.bin"
    with open(p, "rb") as fh:
        return fh.read()


def restore(sA, logger):
    baseline = load_baseline_bytes()
    slug = "ZCM_ADM027|restore.jpg"
    st_u, hdr_u, body_u = raw_upload(sA, baseline, "image/jpeg", slug)
    logger.log("g2_restore", "ApplicantPhotos", "POST (restore)",
               "FINAL RESTORE from g1_0 baseline",
               {"status": st_u, "text": ""},
               [f"restore_status={st_u}",
                f"restore_bytes={len(baseline)}"])
    st_v, hdr_v, body_v = raw_get_binary(sA, VALUE_URL)
    logger.log("g2_restore", "ApplicantPhotos('0')/$value", "RESTORE_VERIFY",
               "final byte-compare vs g1_0 baseline",
               {"status": "n/a", "text": ""},
               [f"observed_len={len(body_v)}",
                f"baseline_len={len(baseline)}",
                f"served_ct={hdr_v.get('Content-Type', hdr_v.get('content-type', '?'))}"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-interval", type=float, default=8.0)
    args = ap.parse_args()
    m.MIN_INTERVAL = args.min_interval
    print(f"[cadence] MIN_INTERVAL={m.MIN_INTERVAL}", file=sys.stderr)

    global MINIMAL_JPEG
    MINIMAL_JPEG = load_baseline_bytes()
    print(f"[baseline] loaded {len(MINIMAL_JPEG)} bytes as probe body",
          file=sys.stderr)

    client = m.Client()
    logger = m.MatrixLogger(m.JSONL_PATH, append=True)
    sA = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))
    client.fetch_csrf(sA)

    results = {}
    try:
        # G2.1 — filename injection variants (all with valid ZCM_ADM027 docType)
        results["g2_1_html_meta"] = probe_upload(
            sA, "g2_1_html_meta",
            "ZCM_ADM027|<img src=x onerror=/*KLG_FN*/>.jpg", logger)
        results["g2_1_traversal"] = probe_upload(
            sA, "g2_1_traversal",
            "ZCM_ADM027|../../../klg_trav.jpg", logger)

        # G2.2 — doc-type routing variants (all with sane filename)
        results["g2_2_adm028"] = probe_upload(
            sA, "g2_2_adm028",
            "ZCM_ADM028|klg_g2_2_adm028.jpg", logger)
        results["g2_2_admletter"] = probe_upload(
            sA, "g2_2_admletter",
            "ZCM_ADM_LETTER|klg_g2_2_letter.jpg", logger)
    finally:
        restore(sA, logger)

    print("\n=== G2 SUMMARY ===", file=sys.stderr)
    for label, r in results.items():
        us = r.get("upload_status")
        fn = r.get("fn_returned")
        dt = r.get("dt_returned")
        e_fn = r.get("entity_after", {}).get("fileName")
        e_dt = r.get("entity_after", {}).get("docType")
        print(f"  {label:<22} upload={us}  "
              f"fn_returned={fn!r}  dt_returned={dt!r}  "
              f"entity_fn={e_fn!r}  entity_dt={e_dt!r}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
