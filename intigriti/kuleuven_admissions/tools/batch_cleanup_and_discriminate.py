#!/usr/bin/env python3
"""Cleanup A's row + discriminator probe.

1. Restore A's HigherEducations('0') row 000001 to nameSchool='KLTEST_S10_SEED_A'.
2. Verify cleanup on both A and B.
3. Discriminator probe: batch MERGE with body higherEducationId='999999' (id
   neither account has). Two outcomes:
     - Server writes to A's OWN row 000001 (body id ignored) => URL-key routed.
     - Server creates a new row 999999 under A's tenant => body-id routed,
       own-tenant scoped (Hyp C).
4. Cleanup: if a phantom row was created, DELETE it (best effort).
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m

BOUNDARY = "batch_klxb"
CHANGESET = "changeset_klxc"

def build_batch(higher_body):
    body_json = json.dumps(higher_body)
    parts = [
        f"--{BOUNDARY}",
        f"Content-Type: multipart/mixed; boundary={CHANGESET}",
        "",
        f"--{CHANGESET}",
        "Content-Type: application/http",
        "Content-Transfer-Encoding: binary",
        "Content-ID: 1",
        "",
        "MERGE HigherEducations('0')?sap-client=200 HTTP/1.1",
        "Content-Type: application/json",
        f"Content-Length: {len(body_json)}",
        "",
        body_json,
        "",
        f"--{CHANGESET}--",
        "",
        f"--{BOUNDARY}--",
        "",
    ]
    return ("\r\n".join(parts)).encode("utf-8"), BOUNDARY

def parse_inner(text):
    import re
    return [int(m2.group(1)) for m2 in re.finditer(r"HTTP/1\.\d\s+(\d{3})", text or "")]

def rows(text):
    try:
        return json.loads(text)["d"]["results"]
    except Exception:
        return []

c = m.Client()
sA = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))
sB = m.Session("B", m.load_cookie_header(m.CREDS_DIR + "/B.cookies"))
c.fetch_csrf(sA); c.fetch_csrf(sB)
print(f"[csrf] A={sA.csrf[:12]}... B={sB.csrf[:12]}...", file=sys.stderr)

# --------------------------------------------------------------------------
# STEP 1: restore A's row
# --------------------------------------------------------------------------
body, bnd = build_batch({"higherEducationId": "000001",
                         "nameSchool": "KLTEST_S10_SEED_A"})
r = c.request(sA, "POST", "$batch", body=body,
              extra_headers={"Content-Type":
                             f"multipart/mixed; boundary={bnd}"},
              note="cleanup A row")
print(f"[cleanup] outer={r.get('status')} inner={parse_inner(r.get('text',''))}",
      file=sys.stderr)

# --------------------------------------------------------------------------
# STEP 2: verify cleanup on both sessions
# --------------------------------------------------------------------------
rA = c.request(sA, "GET", "Curriculums('0')/HigherEducations", note="verify A")
rB = c.request(sB, "GET", "Curriculums('0')/HigherEducations", note="verify B")
for label, rr in [("A", rA), ("B", rB)]:
    for row in rows(rr.get("text", "")):
        print(f"[verify-{label}] id={row.get('higherEducationId')!r} "
              f"nameSchool={row.get('nameSchool')!r}", file=sys.stderr)

# --------------------------------------------------------------------------
# STEP 3: discriminator probe — body id = '999999' (neither account has it)
# --------------------------------------------------------------------------
body, bnd = build_batch({"higherEducationId": "999999",
                         "nameSchool": "KLTEST_S10_DISCRIM"})
r = c.request(sA, "POST", "$batch", body=body,
              extra_headers={"Content-Type":
                             f"multipart/mixed; boundary={bnd}"},
              note="discriminator id=999999")
print(f"[discrim] outer={r.get('status')} inner={parse_inner(r.get('text',''))}",
      file=sys.stderr)

# --------------------------------------------------------------------------
# STEP 4: read back both — did A get a new row 999999? Was A's 000001 changed?
# --------------------------------------------------------------------------
rA = c.request(sA, "GET", "Curriculums('0')/HigherEducations", note="post-discrim A")
rB = c.request(sB, "GET", "Curriculums('0')/HigherEducations", note="post-discrim B")
print("=== POST-DISCRIM ===", file=sys.stderr)
a_has_999999 = False
a_000001_changed = False
for label, rr in [("A", rA), ("B", rB)]:
    for row in rows(rr.get("text", "")):
        rid = str(row.get("higherEducationId"))
        ns  = row.get("nameSchool")
        print(f"  [{label}] id={rid!r} nameSchool={ns!r}", file=sys.stderr)
        if label == "A" and rid == "999999":
            a_has_999999 = True
        if label == "A" and rid == "000001" and ns == "KLTEST_S10_DISCRIM":
            a_000001_changed = True

# --------------------------------------------------------------------------
# STEP 5: verdict + cleanup any phantom row
# --------------------------------------------------------------------------
if a_has_999999:
    verdict = "HYP_C_OWN_TENANT_CREATE_WITH_ATTACKER_ID"
elif a_000001_changed:
    verdict = "HYP_A_PRIME_URL_KEY_ROUTED_BODY_ID_IGNORED"
else:
    verdict = "HYP_A_URL_KEY_ROUTED_NO_ROW_TOUCHED"
print(f"[VERDICT] {verdict}", file=sys.stderr)

# Cleanup: if 000001 got clobbered again, revert. Also try to delete 999999 if present.
if a_000001_changed:
    body, bnd = build_batch({"higherEducationId": "000001",
                             "nameSchool": "KLTEST_S10_SEED_A"})
    r = c.request(sA, "POST", "$batch", body=body,
                  extra_headers={"Content-Type":
                                 f"multipart/mixed; boundary={bnd}"},
                  note="cleanup revert 000001 again")
    print(f"[re-cleanup] outer={r.get('status')} inner={parse_inner(r.get('text',''))}",
          file=sys.stderr)
if a_has_999999:
    # best-effort delete via composite key form
    for path in ["HigherEducations('999999')",
                 "HigherEducations(higherEducationId='999999')"]:
        r = c.request(sA, "DELETE", path, note=f"delete phantom {path}")
        print(f"[phantom-del] {path} -> {r.get('status')}", file=sys.stderr)
        if r.get("status") in (200, 204):
            break

# Final verify
rA = c.request(sA, "GET", "Curriculums('0')/HigherEducations", note="final verify A")
rB = c.request(sB, "GET", "Curriculums('0')/HigherEducations", note="final verify B")
print("=== FINAL ===", file=sys.stderr)
for label, rr in [("A", rA), ("B", rB)]:
    for row in rows(rr.get("text", "")):
        print(f"  [{label}] id={row.get('higherEducationId')!r} "
              f"nameSchool={row.get('nameSchool')!r}", file=sys.stderr)
