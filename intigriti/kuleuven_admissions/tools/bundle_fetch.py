#!/usr/bin/env python3
"""Track C/D fetcher — GET-only, strict scope /sap/bc/ui5_ui5/sap/zc_ad_appl/*, 1 req/sec.

Uses A's SAP cookies from ~/kuleuven_creds/A.cookies (or the symlink under
intigriti/kuleuven_admissions/creds/). Refuses any URL outside the sanctioned
bundle path. Refuses any method other than GET. Rotates the session cookie on
every response (SAP rotates SAP_SESSIONID_* per request).

    python3 bundle_fetch.py <relative-path> [out_file]

Example:
    python3 bundle_fetch.py Component-preload.js  vm-results/03-bundle/Component-preload.js
"""
import os
import sys
import ssl
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m  # reuse cookie loader + Session

ALLOWED_HOST = "webwsp.aps.kuleuven.be"
BASE_PATH = "/sap/bc/ui5_ui5/sap/zc_ad_appl"
BASE = f"https://{ALLOWED_HOST}{BASE_PATH}"
MIN_INTERVAL = 1.05  # >= 1 req/sec

_last = 0.0
_ctx = ssl.create_default_context()


def _throttle():
    global _last
    dt = time.monotonic() - _last
    if dt < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - dt)
    _last = time.monotonic()


def assert_scope(url):
    if not url.startswith(f"https://{ALLOWED_HOST}"):
        raise SystemExit(f"[FATAL] host out of scope: {url}")
    path = url.split("?", 1)[0].split("//", 1)[1].split("/", 1)[1]
    path = "/" + path
    if not (path.startswith(BASE_PATH + "/") or path == BASE_PATH):
        raise SystemExit(f"[FATAL] path out of scope: {path}")


def get(session, rel):
    url = rel if rel.startswith("http") else f"{BASE}/{rel.lstrip('/')}"
    assert_scope(url)
    _throttle()
    req = urllib.request.Request(url, method="GET", headers={
        "Accept": "*/*",
        "Cookie": session.cookie_header,
    })
    try:
        resp = urllib.request.urlopen(req, timeout=30, context=_ctx)
        sc = resp.headers.get_all("Set-Cookie") or []
        session.update_from_set_cookie(sc)
        return resp.getcode(), dict(resp.getheaders()), resp.read()
    except urllib.error.HTTPError as e:
        sc = e.headers.get_all("Set-Cookie") if e.headers else []
        session.update_from_set_cookie(sc)
        body = e.read() if e.fp else b""
        return e.code, (dict(e.headers.items()) if e.headers else {}), body


def load_session():
    return m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        raise SystemExit("usage: bundle_fetch.py <relative-path> [out_file]")
    rel = argv[0]
    out = argv[1] if len(argv) > 1 else None
    session = load_session()
    st, headers, body = get(session, rel)
    ct = headers.get("Content-Type", headers.get("content-type", "?"))
    sys.stderr.write(f"GET {rel} -> {st}  {ct}  {len(body)} bytes\n")
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "wb") as fh:
            fh.write(body)
        sys.stderr.write(f"wrote {out}\n")
    else:
        sys.stdout.buffer.write(body)
    return 0 if st == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
