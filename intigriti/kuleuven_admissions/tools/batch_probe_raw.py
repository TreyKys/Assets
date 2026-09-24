#!/usr/bin/env python3
# Raw $batch probe — sends one $batch and prints the FULL response body so we
# can see what SAP says beyond the 200-char JSONL truncation.
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m

c = m.Client()
sA = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))
c.fetch_csrf(sA)
print(f"[csrf] {sA.csrf[:20]}...", file=sys.stderr)

# Handcraft the batch body per SAP OData v2 spec — several potential fixes:
#   1) inner Content-Type: application/http; msgtype=request
#   2) inner URL carries sap-client=200
#   3) no leading slash on inner method line
BOUNDARY = "batch_klxb"
CHANGESET = "changeset_klxc"
inner_body = '{"higherEducationId": "000001", "nameSchool": "KLTEST_BATCH_RAW2"}'
parts = [
    f"--{BOUNDARY}",
    f"Content-Type: multipart/mixed; boundary={CHANGESET}",
    "",
    f"--{CHANGESET}",
    "Content-Type: application/http",
    "Content-Transfer-Encoding: binary",
    "Content-ID: 1",
    "",
    f"MERGE HigherEducations('0')?sap-client=200 HTTP/1.1",
    "Content-Type: application/json",
    f"Content-Length: {len(inner_body)}",
    "",
    inner_body,
    "",
    f"--{CHANGESET}--",
    "",
    f"--{BOUNDARY}--",
    "",
]
body = ("\r\n".join(parts)).encode("utf-8")
boundary = BOUNDARY
print(f"=== BODY ({len(body)} bytes) ===", file=sys.stderr)
print(body.decode(), file=sys.stderr)
print("=== SEND ===", file=sys.stderr)
time.sleep(1)
r = c.request(sA, "POST", "$batch", body=body,
              extra_headers={"Content-Type":
                             f"multipart/mixed; boundary={boundary}"},
              note="raw batch probe")
print(f"status={r.get('status')}", file=sys.stderr)
print("=== FULL RESPONSE BODY ===")
print(r.get("text", ""))
