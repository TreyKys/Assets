#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track G — ApplicantPhotos upload surface (G1.0 baseline + G1.1 SVG + G1.2 html/xhtml).

Raw-XHR uploads to `POST /ApplicantPhotos` with client-controlled
Content-Type + slug header. Read-back via `GET /ApplicantPhotos('0')/$value`
returns the stored bytes (verbatim or transcoded — that's the key question).

Mandatory: capture A's real photo bytes + metadata FIRST, restore in
`finally:` via byte-compare verification. Every payload has an inert
marker (KLG_*) so any renderable content is neutered — no alert(),
no OOB in G1.1/G1.2 (OOB reserved for G1.4/G3 only).

Budget: ~5 non-safe (baseline safe reads + 3 uploads + 1 restore).
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
VALUE_URL  = f"https://{m.ALLOWED_HOST}/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/ApplicantPhotos('0')/$value?sap-client=200"
ENTITY_URL = f"https://{m.ALLOWED_HOST}/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/ApplicantPhotos('0')?sap-client=200"

_ssl_ctx = ssl.create_default_context()


def raw_get_binary(session, url, timeout=30):
    """Direct GET returning (status, headers_dict, body_bytes)."""
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
    """POST to /ApplicantPhotos with raw bytes + custom Content-Type + slug."""
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


def save_bytes(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def summarize_headers(headers):
    """Extract the four G1.0 headers that decide exploitability."""
    return {
        "Content-Type": headers.get("Content-Type", headers.get("content-type")),
        "X-Content-Type-Options": headers.get("X-Content-Type-Options",
                                                 headers.get("x-content-type-options")),
        "Content-Disposition": headers.get("Content-Disposition",
                                             headers.get("content-disposition")),
        "Content-Security-Policy": headers.get("Content-Security-Policy",
                                                  headers.get("content-security-policy")),
    }


def phase_g1_0(sA, logger):
    print("\n=== G1.0 — baseline the serve behavior ===", file=sys.stderr)

    # 1) Read the entity metadata
    st_e, hdr_e, body_e = raw_get_binary(sA, ENTITY_URL)
    logger.log("g1.0", "ApplicantPhotos('0')", "GET (entity)",
               "G1.0 baseline entity", {"status": st_e, "text": ""},
               [f"status={st_e}", f"body_len={len(body_e)}"])
    try:
        entity_json = json.loads(body_e.decode("utf-8"))
    except Exception as e:
        entity_json = {"_parse_error": str(e), "_raw": body_e[:200].decode(errors="replace")}
    save_json(f"{EVIDENCE_DIR}/g1_0_entity_metadata.json", entity_json)

    # 2) Read the $value bytes
    st_v, hdr_v, body_v = raw_get_binary(sA, VALUE_URL)
    logger.log("g1.0", "ApplicantPhotos('0')/$value", "GET ($value)",
               "G1.0 baseline $value bytes", {"status": st_v, "text": ""},
               [f"status={st_v}", f"body_len={len(body_v)}",
                f"content_type={hdr_v.get('Content-Type', hdr_v.get('content-type', '?'))}"])
    save_bytes(f"{EVIDENCE_DIR}/g1_0_baseline_photo.bin", body_v)
    save_json(f"{EVIDENCE_DIR}/g1_0_baseline_value_headers.json",
              {"status": st_v, "headers": hdr_v,
               "size_bytes": len(body_v)})

    # 3) Summarize the four key headers
    key = summarize_headers(hdr_v)
    save_json(f"{EVIDENCE_DIR}/g1_0_key_headers.json", key)
    logger.log("g1.0", "ApplicantPhotos('0')/$value", "SUMMARY",
               "G1.0 four key headers", {"status": "n/a", "text": ""},
               [f"Content-Type={key['Content-Type']!r}",
                f"X-Content-Type-Options={key['X-Content-Type-Options']!r}",
                f"Content-Disposition={key['Content-Disposition']!r}",
                f"Content-Security-Policy={key['Content-Security-Policy']!r}"])

    return {
        "entity_json": entity_json,
        "baseline_bytes": body_v,
        "baseline_headers": hdr_v,
        "key_headers": key,
        "value_status": st_v,
    }


def _upload_probe(sA, blob, ctype, slug, label, logger, marker=""):
    """Upload + re-read entity + re-read $value. Record everything."""
    save_bytes(f"{EVIDENCE_DIR}/g_{label}_probe_uploaded.bin", blob)
    st_u, hdr_u, body_u = raw_upload(sA, blob, ctype, slug)
    logger.log("g1", "ApplicantPhotos", "POST (upload)",
               f"G1 upload {label} ct={ctype!r} slug={slug!r}",
               {"status": st_u, "text": ""},
               [f"upload_status={st_u}",
                f"resp_len={len(body_u)}",
                f"resp_ct={hdr_u.get('Content-Type', hdr_u.get('content-type', '?'))}"])
    save_bytes(f"{EVIDENCE_DIR}/g_{label}_upload_response.bin", body_u)

    if st_u not in (201, 202, 204, 200):
        return {"status": st_u, "landed": False, "read_back": None,
                "response_body": body_u[:400]}

    # Read entity metadata
    st_e, hdr_e, body_e = raw_get_binary(sA, ENTITY_URL)
    try:
        entity_after = json.loads(body_e.decode("utf-8"))
    except Exception:
        entity_after = None
    save_json(f"{EVIDENCE_DIR}/g_{label}_entity_after.json",
              entity_after or {"raw": body_e[:400].decode(errors="replace")})

    # Read $value bytes
    st_v, hdr_v, body_v = raw_get_binary(sA, VALUE_URL)
    served_ct = hdr_v.get("Content-Type", hdr_v.get("content-type", "?"))
    save_bytes(f"{EVIDENCE_DIR}/g_{label}_readback_value.bin", body_v)
    save_json(f"{EVIDENCE_DIR}/g_{label}_readback_headers.json",
              {"status": st_v, "headers": hdr_v})

    bytes_verbatim = (body_v == blob)
    marker_in_body = (marker.encode() in body_v) if marker else False
    ct_reflected = (served_ct == ctype)

    logger.log("g1", "ApplicantPhotos('0')/$value", "COMPARE",
               f"G1 readback {label}", {"status": "n/a", "text": ""},
               [f"upload_status={st_u}",
                f"readback_status={st_v}",
                f"served_content_type={served_ct!r}",
                f"content_type_reflected={ct_reflected}",
                f"bytes_verbatim={bytes_verbatim}",
                f"marker_in_body={marker_in_body}",
                f"readback_len={len(body_v)}",
                "ANOMALY_content_type_reflected_active" if ct_reflected and ctype in (
                    "image/svg+xml", "text/html", "application/xhtml+xml") else ""])
    return {"upload_status": st_u,
            "readback_status": st_v,
            "served_content_type": served_ct,
            "content_type_reflected": ct_reflected,
            "bytes_verbatim": bytes_verbatim,
            "marker_in_body": marker_in_body,
            "readback_bytes": body_v,
            "readback_headers": hdr_v,
            "entity_after": entity_after}


def phase_g1_1_svg(sA, logger):
    print("\n=== G1.1 — SVG with inert script marker ===", file=sys.stderr)
    blob = (b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
            b'<script>/*KLG_SVG_MARKER*/</script></svg>')
    return _upload_probe(sA, blob, "image/svg+xml",
                          "ZCM_ADM027|klg_probe.svg", "g1_1_svg",
                          logger, marker="KLG_SVG_MARKER")


def phase_g1_2_html(sA, logger):
    print("\n=== G1.2a — text/html ===", file=sys.stderr)
    html_blob = (b'<!--KLG_HTML_MARKER-->'
                 b'<html><body>KLG_HTML_MARKER_body</body></html>')
    r1 = _upload_probe(sA, html_blob, "text/html",
                       "ZCM_ADM027|klg_probe.html", "g1_2_html",
                       logger, marker="KLG_HTML_MARKER")

    print("\n=== G1.2b — application/xhtml+xml ===", file=sys.stderr)
    xhtml_blob = (b'<?xml version="1.0"?>'
                  b'<html xmlns="http://www.w3.org/1999/xhtml">'
                  b'<body>KLG_XHTML_MARKER</body></html>')
    r2 = _upload_probe(sA, xhtml_blob, "application/xhtml+xml",
                       "ZCM_ADM027|klg_probe.xhtml", "g1_2_xhtml",
                       logger, marker="KLG_XHTML_MARKER")
    return r1, r2


def restore(sA, baseline, logger):
    """Restore A's original photo bytes with the original Content-Type."""
    print("\n=== RESTORE — putting A's original photo back ===", file=sys.stderr)
    baseline_ct = baseline["key_headers"]["Content-Type"] or "image/jpeg"
    baseline_bytes = baseline["baseline_bytes"]

    # Determine slug: entity's fileName if available, else generic
    entity = baseline.get("entity_json") or {}
    d = entity.get("d", {}) if isinstance(entity, dict) else {}
    orig_name = d.get("fileName") or "restore.jpg"
    slug = f"ZCM_ADM027|{orig_name}"

    st_u, hdr_u, body_u = raw_upload(sA, baseline_bytes, baseline_ct, slug)
    logger.log("g_restore", "ApplicantPhotos", "POST (restore)",
               f"RESTORE original photo ({baseline_ct}, {len(baseline_bytes)} B)",
               {"status": st_u, "text": ""},
               [f"restore_status={st_u}",
                f"restore_ct={baseline_ct!r}",
                f"restore_slug={slug!r}"])

    # Verify by byte-compare
    st_v, hdr_v, body_v = raw_get_binary(sA, VALUE_URL)
    ok = (body_v == baseline_bytes)
    logger.log("g_restore", "ApplicantPhotos('0')/$value", "RESTORE_VERIFY",
               f"byte-compare vs baseline",
               {"status": "n/a", "text": ""},
               [f"cleanup_ok={ok}",
                f"baseline_len={len(baseline_bytes)}",
                f"observed_len={len(body_v)}",
                f"served_ct={hdr_v.get('Content-Type', hdr_v.get('content-type', '?'))!r}"])
    save_bytes(f"{EVIDENCE_DIR}/g_restore_final_photo.bin", body_v)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-interval", type=float, default=8.0)
    args = ap.parse_args()
    m.MIN_INTERVAL = args.min_interval
    print(f"[cadence] MIN_INTERVAL={m.MIN_INTERVAL}", file=sys.stderr)

    client = m.Client()
    logger = m.MatrixLogger(m.JSONL_PATH, append=True)
    sA = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))
    client.fetch_csrf(sA)
    print(f"[csrf] A={sA.csrf[:14]}...", file=sys.stderr)

    os.makedirs(EVIDENCE_DIR, exist_ok=True)

    # ----- G1.0 baseline -------------------------------------------------
    baseline = phase_g1_0(sA, logger)

    if baseline["value_status"] != 200 or not baseline["baseline_bytes"]:
        print(f"[HALT] G1.0 couldn't capture baseline "
              f"(status={baseline['value_status']}, "
              f"bytes={len(baseline['baseline_bytes'])}). "
              f"Cannot proceed without restore target.", file=sys.stderr)
        return 2

    print(f"[baseline] photo captured: {len(baseline['baseline_bytes'])} bytes, "
          f"Content-Type={baseline['key_headers']['Content-Type']!r}",
          file=sys.stderr)

    try:
        # ----- G1.1 SVG probe ---------------------------------------------
        svg_result = phase_g1_1_svg(sA, logger)
        # ----- G1.2 HTML + XHTML probes -----------------------------------
        html_result, xhtml_result = phase_g1_2_html(sA, logger)

        # Summary of G1 results
        print("\n=== G1 SUMMARY ===", file=sys.stderr)
        for label, r in [("SVG", svg_result), ("HTML", html_result),
                          ("XHTML", xhtml_result)]:
            us = r.get("upload_status") if r else "n/a"
            if us not in (201, 202, 204, 200):
                print(f"  {label:<6} upload {us} (rejected)",
                      file=sys.stderr)
            else:
                print(f"  {label:<6} upload {us}, "
                      f"served-ct={r.get('served_content_type')!r}, "
                      f"ct-reflected={r.get('content_type_reflected')}, "
                      f"bytes-verbatim={r.get('bytes_verbatim')}, "
                      f"marker-in-body={r.get('marker_in_body')}",
                      file=sys.stderr)
    finally:
        # ----- Mandatory restore -----------------------------------------
        restore_ok = restore(sA, baseline, logger)
        print(f"\n[restore] byte-compare_ok={restore_ok}", file=sys.stderr)


if __name__ == "__main__":
    main()
