#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track H.1 — confirm programDescription raw-HTML storage (inert probes only).

Steps per VM-BRIEF-track-h1-programdescription-confirm.md:
  0. Baseline read of Applications('<A>'). Save.
  1. Batched MERGE programDescription = "KLXSSPD_INERT_1"; read back;
     record field_changed.
  2. IF writable: MERGE "<b>KLXSSPD_2</b>", read back, classify raw/enc/strip.
     Then MERGE "<img src=x>KLXSSPD_3" (NO onerror), read back, classify.
  4. Restore programDescription to baseline; verify byte-equal.

Follow-up (my proposed extension of Track B):
  Also try the CREATE-path — MERGE Applications('0') with programDescription
  to see if the CREATE self-alias has looser field filtering than the UPDATE
  path with a real applicationId. This creates a NEW application record if
  it lands; must be delete-able cleanly.

All payloads are INERT (no onerror/onload/JS handlers). Nothing that
executes ever gets persisted from the VM.

Budget: 5 non-safe (batched) + 1 safe baseline GET + 4 safe re-reads.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m

APP_A = "000000503432"
ENT = f"Applications('{APP_A}')"
EVIDENCE_DIR = "intigriti/kuleuven_admissions/vm-results/07-track-h1-evidence"


def batched_merge(client, session, entity_rel, body_dict, logger, note):
    body, boundary = m._batch_body(
        [], changeset=[("MERGE", entity_rel, body_dict)])
    r = client.request(session, "POST", "$batch", body=body,
                       extra_headers={"Content-Type":
                                      f"multipart/mixed; boundary={boundary}"},
                       note=note)
    inners = m._parse_batch_inner_statuses(r.get("text", "") or "")
    inner = inners[0] if inners else None
    logger.log("h1c", entity_rel, "POST $batch", note, r,
               [f"outer={r.get('status')}", f"inner={inner}",
                f"payload={json.dumps(body_dict)[:120]}"])
    return r.get("status"), inner


def classify_readback(observed, marker, payload):
    """Return one of 'stored_RAW', 'stored_encoded', 'stored_stripped',
    'stored_marker_only', 'unchanged' based on the readback value."""
    if observed is None:
        return "readback_none"
    s = str(observed)
    if s == payload:
        return "stored_RAW"
    # Encoded HTML entities
    if ("&lt;" in s or "&gt;" in s or "&amp;" in s) and marker in s:
        return "stored_encoded"
    if marker in s and "<" not in s and ">" not in s:
        return "stored_stripped_marker_kept"
    if marker in s and "<" in s:
        return "stored_partial_" + hex(hash(s) & 0xffff)
    return "unchanged_or_other"


def save_json(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-interval", type=float, default=8.0)
    ap.add_argument("--try-create-path", action="store_true",
                    help="Also try MERGE /Applications('0') (CREATE self-alias) — "
                         "may leave a new Application record; must delete after.")
    args = ap.parse_args()
    m.MIN_INTERVAL = args.min_interval
    print(f"[cadence] MIN_INTERVAL={m.MIN_INTERVAL}", file=sys.stderr)

    client = m.Client()
    logger = m.MatrixLogger(m.JSONL_PATH, append=True)
    sA = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))
    client.fetch_csrf(sA)

    # ---- Step 0: baseline ----------------------------------------------
    print("\n=== Step 0 — baseline ===", file=sys.stderr)
    r0 = m.read_entity(client, sA, ENT, logger, "h1c",
                        "H1c Step 0 baseline")
    try:
        entity0 = json.loads(r0.get("text", ""))
        d0 = entity0.get("d", {})
    except Exception:
        entity0 = None
        d0 = {}
    baseline_pd = d0.get("programDescription")
    save_json(f"{EVIDENCE_DIR}/baseline_application.json", entity0)
    logger.log("h1c", ENT, "NOTE", "H1c Step 0 baseline captured",
               {"status": "n/a", "text": ""},
               [f"programDescription_baseline={baseline_pd!r}",
                f"program_baseline={d0.get('program')!r}"])
    print(f"[baseline] programDescription={baseline_pd!r}", file=sys.stderr)

    verdicts = []

    try:
        # ---- Step 1: inert marker probe --------------------------------
        print("\n=== Step 1 — inert marker (writable?) ===", file=sys.stderr)
        inert_payload = "KLXSSPD_INERT_1"
        outer_1, inner_1 = batched_merge(client, sA, ENT,
                                           {"programDescription": inert_payload},
                                           logger, "H1c Step 1 inert marker")
        r1 = m.read_entity(client, sA, ENT, logger, "h1c",
                            "H1c Step 1 re-read")
        after_1 = m.json_field(r1.get("text", ""), "programDescription")
        writable = (after_1 == inert_payload)
        logger.log("h1c", ENT, "COMPARE", "H1c Step 1 verdict",
                   {"status": "n/a", "text": ""},
                   [f"outer={outer_1}", f"inner={inner_1}",
                    f"baseline={baseline_pd!r}", f"after={after_1!r}",
                    f"writable={writable}"])
        print(f"  outer={outer_1} inner={inner_1}", file=sys.stderr)
        print(f"  baseline={baseline_pd!r}", file=sys.stderr)
        print(f"  after   ={after_1!r}", file=sys.stderr)
        print(f"  writable={writable}", file=sys.stderr)
        verdicts.append(("step1_inert", inner_1, writable, after_1))

        if writable:
            # ---- Step 2a: <b> probe -----------------------------------
            print("\n=== Step 2a — <b>KLXSSPD_2</b> (non-executing HTML) ===",
                  file=sys.stderr)
            b_payload = "<b>KLXSSPD_2</b>"
            outer_2a, inner_2a = batched_merge(client, sA, ENT,
                                                 {"programDescription": b_payload},
                                                 logger, "H1c Step 2a <b>")
            r2a = m.read_entity(client, sA, ENT, logger, "h1c",
                                 "H1c Step 2a re-read")
            after_2a = m.json_field(r2a.get("text", ""), "programDescription")
            verdict_2a = classify_readback(after_2a, "KLXSSPD_2", b_payload)
            logger.log("h1c", ENT, "COMPARE", "H1c Step 2a <b> verdict",
                        {"status": "n/a", "text": ""},
                        [f"outer={outer_2a}", f"inner={inner_2a}",
                         f"payload={b_payload!r}", f"after={after_2a!r}",
                         f"classification={verdict_2a}"])
            print(f"  after={after_2a!r}", file=sys.stderr)
            print(f"  classification={verdict_2a}", file=sys.stderr)
            verdicts.append(("step2a_b_tag", inner_2a, verdict_2a, after_2a))

            # ---- Step 2b: <img src=x> probe (NO onerror) --------------
            print("\n=== Step 2b — <img src=x>KLXSSPD_3 (NO onerror) ===",
                  file=sys.stderr)
            img_payload = "<img src=x>KLXSSPD_3"
            outer_2b, inner_2b = batched_merge(client, sA, ENT,
                                                 {"programDescription": img_payload},
                                                 logger, "H1c Step 2b <img src=x> no handler")
            r2b = m.read_entity(client, sA, ENT, logger, "h1c",
                                 "H1c Step 2b re-read")
            after_2b = m.json_field(r2b.get("text", ""), "programDescription")
            verdict_2b = classify_readback(after_2b, "KLXSSPD_3", img_payload)
            logger.log("h1c", ENT, "COMPARE", "H1c Step 2b <img> verdict",
                        {"status": "n/a", "text": ""},
                        [f"outer={outer_2b}", f"inner={inner_2b}",
                         f"payload={img_payload!r}", f"after={after_2b!r}",
                         f"classification={verdict_2b}"])
            print(f"  after={after_2b!r}", file=sys.stderr)
            print(f"  classification={verdict_2b}", file=sys.stderr)
            verdicts.append(("step2b_img_tag", inner_2b, verdict_2b, after_2b))

    finally:
        # ---- Step 4: restore ------------------------------------------
        print("\n=== Step 4 — restore ===", file=sys.stderr)
        restore_value = baseline_pd if baseline_pd is not None else ""
        outer_r, inner_r = batched_merge(client, sA, ENT,
                                          {"programDescription": restore_value},
                                          logger, f"H1c Step 4 RESTORE programDescription={restore_value!r}")
        rV = m.read_entity(client, sA, ENT, logger, "h1c",
                            "H1c Step 4 verify restore")
        now = m.json_field(rV.get("text", ""), "programDescription")
        cleanup_ok = (now == baseline_pd) or (str(now) == str(baseline_pd))
        logger.log("h1c", ENT, "CLEANUP_VERIFY",
                    f"programDescription ok={cleanup_ok}",
                    {"status": "n/a", "text": ""},
                    [f"cleanup_ok={cleanup_ok}",
                     f"restore_inner={inner_r}",
                     f"expected={baseline_pd!r}", f"observed={now!r}"])
        print(f"  cleanup_ok={cleanup_ok}  observed={now!r}", file=sys.stderr)
        if not cleanup_ok:
            print("\n[⚠ HALT] cleanup FAILED — programDescription not restored to baseline",
                  file=sys.stderr)

    # ---- CREATE-path follow-up (only if requested) ---------------------
    create_verdict = None
    if args.try_create_path:
        print("\n=== FOLLOW-UP — Track B CREATE-path probe: MERGE Applications('0') ===",
              file=sys.stderr)
        # Get list of A's current Applications to know what's there before
        rb = m.read_entity(client, sA, "Applications", logger, "h1c",
                            "H1c CREATE baseline list")
        try:
            before_rows = json.loads(rb.get("text","")).get("d",{}).get("results",[])
        except Exception:
            before_rows = []
        before_ids = {str(r.get("applicationId")) for r in before_rows}
        logger.log("h1c", "Applications", "NOTE", "H1c CREATE before-list",
                    {"status": "n/a", "text": ""},
                    [f"rows_before={len(before_ids)}",
                     f"ids_before={sorted(before_ids)[:5]}"])

        create_payload = {"programDescription": "KLXSSPD_CREATE_1"}
        outer_c, inner_c = batched_merge(client, sA, "Applications('0')",
                                           create_payload, logger,
                                           "H1c CREATE-path MERGE Applications('0')")
        # Re-list
        ra = m.read_entity(client, sA, "Applications", logger, "h1c",
                            "H1c CREATE after-list")
        try:
            after_rows = json.loads(ra.get("text","")).get("d",{}).get("results",[])
        except Exception:
            after_rows = []
        after_ids = {str(r.get("applicationId")) for r in after_rows}
        new_ids = after_ids - before_ids
        created = len(new_ids) > 0
        create_verdict = "CREATE_LANDED" if created else "CREATE_REJECTED"
        logger.log("h1c", "Applications('0')", "COMPARE", "H1c CREATE-path verdict",
                    {"status": "n/a", "text": ""},
                    [f"outer={outer_c}", f"inner={inner_c}",
                     f"rows_before={len(before_ids)}",
                     f"rows_after={len(after_ids)}",
                     f"new_ids={sorted(new_ids)}",
                     f"verdict={create_verdict}"])
        print(f"  outer={outer_c} inner={inner_c}", file=sys.stderr)
        print(f"  rows before={len(before_ids)} after={len(after_ids)}", file=sys.stderr)
        print(f"  new_ids={sorted(new_ids)}", file=sys.stderr)
        print(f"  verdict={create_verdict}", file=sys.stderr)

        # If created, DELETE the new record(s)
        if created:
            for nid in sorted(new_ids):
                print(f"\n=== CREATE cleanup — DELETE Applications('{nid}') ===",
                      file=sys.stderr)
                try:
                    rd = client.request(sA, "DELETE", f"Applications('{nid}')",
                                         note=f"H1c CREATE cleanup delete {nid}")
                    logger.log("h1c", f"Applications('{nid}')", "DELETE",
                                f"cleanup delete phantom Application",
                                {"status": rd.get("status"), "text": ""},
                                [f"delete_status={rd.get('status')}"])
                    print(f"  delete status={rd.get('status')}", file=sys.stderr)
                except Exception as e:
                    print(f"  delete err: {e}", file=sys.stderr)

    # ---- Summary --------------------------------------------------------
    print("\n=== H1c SUMMARY ===", file=sys.stderr)
    for name, inner, cls, observed in verdicts:
        print(f"  {name:<18} inner={inner}  class={cls}  observed={observed!r}",
              file=sys.stderr)
    if create_verdict is not None:
        print(f"  create_path        {create_verdict}", file=sys.stderr)


if __name__ == "__main__":
    main()
