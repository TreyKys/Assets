#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sweep 10 batched-write probe v2 — single-MERGE changeset.

v1 sent a 2-MERGE changeset (Curriculums('0') + HigherEducations('0')) and
got outer 400 'malformed syntax'. The empty {} body on Curriculums may have
been the parser hazard. This variant tries the simpler single-MERGE-in-
changeset shape:

  POST /$batch
  --batch
    --changeset
      MERGE HigherEducations('0')
      body: {higherEducationId:"000001", nameSchool:"KLTEST_S10_TEST"}
    --changeset--
  --batch--

Discrimination — since A's and B's rows both have `higherEducationId='000001'`,
this ONE probe collapses phase 10.2 (control) and 10.4 (cross-user):
  A's row updated but B's unchanged → tenant-scoped (safe).
  B's row updated                   → unscoped table write (crown jewel).
  Both unchanged, inner 501/403     → batch wrap doesn't unlock writes.
  Both unchanged, inner 204         → write succeeded but landed nowhere we see
                                      (server-side self-substitution, effectively
                                      URL-key-routed with no visible effect).
  Outer 400 again                   → batch format is still off; different fix.

Budget: 1 non-safe request + up to 1 cleanup non-safe = 2/8.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m  # noqa: E402


def rows_from(text):
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


def find_row_by_seed(rows, seed_prefix):
    for r in rows:
        ns = str(r.get("nameSchool") or "")
        if ns.startswith(seed_prefix):
            return r
    return None


def batch_single_merge(client, session, entity_rel, body_dict, logger, note):
    """Send $batch with ONE changeset containing ONE MERGE."""
    body, boundary = m._batch_body(
        [], changeset=[("MERGE", "/" + entity_rel, body_dict)])
    r = client.request(session, "POST", "$batch", body=body,
                       extra_headers={"Content-Type":
                                      f"multipart/mixed; boundary={boundary}"},
                       note=note)
    inners = m._parse_batch_inner_statuses(r.get("text", ""))
    logger.log("10c", "$batch", "POST", note, r,
               [f"outer={r.get('status')}", f"inner_statuses={inners}",
                f"changeset_body={json.dumps(body_dict)}"])
    return r.get("status"), inners, r.get("text", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-interval", type=float, default=None)
    ap.add_argument("--seed-prefix-a", default="KLTEST_S10_SEED_A")
    ap.add_argument("--seed-prefix-b", default="KLTEST_S10_SEED_B")
    args = ap.parse_args()

    if args.min_interval is not None:
        m.MIN_INTERVAL = args.min_interval
    print(f"[cadence] MIN_INTERVAL={m.MIN_INTERVAL}", file=sys.stderr)

    client = m.Client(dry_run=args.dry_run)
    logger = m.MatrixLogger(m.JSONL_PATH, dry_run=args.dry_run, append=True)
    sessions = (m.load_sessions(client) if not args.dry_run else
                {"A": m.Session("A", "dry"), "B": m.Session("B", "dry")})
    for s in sessions.values():
        if not s.csrf:
            s.csrf = "<dry-run>"
    sA, sB = sessions["A"], sessions["B"]

    # ------ 1. Baselines ---------------------------------------------------
    rA = m.read_entity(client, sA, "Curriculums('0')/HigherEducations",
                       logger, "10c", "S10c baseline A")
    rB = m.read_entity(client, sB, "Curriculums('0')/HigherEducations",
                       logger, "10c", "S10c baseline B")
    rowsA = rows_from(rA.get("text", ""))
    rowsB = rows_from(rB.get("text", ""))
    a_seed = find_row_by_seed(rowsA, args.seed_prefix_a)
    b_seed = find_row_by_seed(rowsB, args.seed_prefix_b)
    if not a_seed or not b_seed:
        logger.log("10c", "HigherEducations", "NOTE",
                   "MISSING SEED ROW — cannot proceed",
                   {"status": "n/a", "text": ""},
                   [f"a_seed={a_seed}", f"b_seed={b_seed}"])
        return 2
    a_id = str(a_seed["higherEducationId"])
    b_id = str(b_seed["higherEducationId"])
    a_base_ns = a_seed.get("nameSchool", "")
    b_base_ns = b_seed.get("nameSchool", "")
    logger.log("10c", "HigherEducations", "NOTE",
               "S10c seed enum",
               {"status": "n/a", "text": ""},
               [f"a_id={a_id!r}", f"b_id={b_id!r}",
                f"same_id={a_id == b_id}",
                f"a_ns={a_base_ns!r}", f"b_ns={b_base_ns!r}"])

    # In the seeded case both accounts have '000001' so a_id == b_id — the
    # single MERGE with body id='000001' from A's session is the crown probe.
    probe_body = {"higherEducationId": a_id,
                  "nameSchool": "KLTEST_S10_TEST_PROBE"}

    a_write_landed = False
    b_write_landed = False
    try:
        # ------ 2. Single-MERGE-in-changeset batch --------------------------
        outer, inners, _ = batch_single_merge(
            client, sA, "HigherEducations('0')", probe_body, logger,
            "S10c single-MERGE-in-changeset probe")
        inner_higher = inners[0] if inners else None

        # ------ 3. Read both to discriminate --------------------------------
        rAf = m.read_entity(client, sA, "Curriculums('0')/HigherEducations",
                            logger, "10c", "S10c re-read A")
        rBf = m.read_entity(client, sB, "Curriculums('0')/HigherEducations",
                            logger, "10c", "S10c re-read B")
        a_row_after = find_row_by_seed(rows_from(rAf.get("text", "")),
                                       "")  # any row with matching id
        # find row by id, not by prefix, since nameSchool may have changed
        a_row_after = None
        for r in rows_from(rAf.get("text", "")):
            if str(r.get("higherEducationId")) == a_id:
                a_row_after = r
                break
        b_row_after = None
        for r in rows_from(rBf.get("text", "")):
            if str(r.get("higherEducationId")) == b_id:
                b_row_after = r
                break

        a_ns_after = a_row_after.get("nameSchool") if a_row_after else None
        b_ns_after = b_row_after.get("nameSchool") if b_row_after else None
        a_write_landed = (a_ns_after == "KLTEST_S10_TEST_PROBE")
        b_write_landed = (b_ns_after == "KLTEST_S10_TEST_PROBE")

        if b_write_landed:
            verdict = "CROSS_TENANT_WRITE_CROWN_JEWEL"
        elif a_write_landed:
            verdict = "OWN_TENANT_WRITE_SAFE"  # tenant-scoped, no cross-user
        elif inner_higher in (200, 202, 204):
            verdict = "WRITE_ACCEPTED_BUT_NO_ROW_CHANGE_UNEXPECTED"
        elif inner_higher in (403,):
            verdict = "WRITE_REJECTED_403"
        elif inner_higher == 501 or inner_higher is None and outer == 400:
            verdict = "WRITE_REJECTED_501_OR_MALFORMED"
        else:
            verdict = f"UNEXPECTED_inner={inner_higher}_outer={outer}"

        flags = [f"outer={outer}", f"inner_higher={inner_higher}",
                 f"a_ns_after={a_ns_after!r}", f"b_ns_after={b_ns_after!r}",
                 f"a_write_landed={a_write_landed}",
                 f"b_write_landed={b_write_landed}",
                 f"VERDICT={verdict}"]
        if verdict == "CROSS_TENANT_WRITE_CROWN_JEWEL":
            flags.append("ANOMALY_cross_tenant_write_persisted")
        logger.log("10c", "HigherEducations", "COMPARE",
                   "S10c discriminator", {"status": "n/a", "text": ""}, flags)
    finally:
        # ------ 4. Cleanup — mandatory --------------------------------------
        if a_write_landed:
            batch_single_merge(
                client, sA, "HigherEducations('0')",
                {"higherEducationId": a_id, "nameSchool": a_base_ns},
                logger, "S10c CLEANUP A revert own row")
        if b_write_landed:
            batch_single_merge(
                client, sB, "HigherEducations('0')",
                {"higherEducationId": b_id, "nameSchool": b_base_ns},
                logger, "S10c CLEANUP B revert own row (from B's session)")
        # verify
        rAv = m.read_entity(client, sA, "Curriculums('0')/HigherEducations",
                            logger, "10c", "S10c cleanup verify A")
        rBv = m.read_entity(client, sB, "Curriculums('0')/HigherEducations",
                            logger, "10c", "S10c cleanup verify B")
        for label, rr, base_id, base_ns in (("A", rAv, a_id, a_base_ns),
                                            ("B", rBv, b_id, b_base_ns)):
            row = None
            for r in rows_from(rr.get("text", "")):
                if str(r.get("higherEducationId")) == base_id:
                    row = r
                    break
            now = row.get("nameSchool") if row else None
            ok = (str(now) == str(base_ns))
            logger.log("10c", "HigherEducations", "CLEANUP_VERIFY",
                       f"{label} ok={ok}",
                       {"status": "n/a", "text": ""},
                       [f"cleanup_ok={ok}", f"expected={base_ns!r}",
                        f"observed={now!r}"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
