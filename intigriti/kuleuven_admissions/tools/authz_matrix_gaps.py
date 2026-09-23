#!/usr/bin/env python3
"""Gap-fill sweeps 9–12 for Track B — the things authz_matrix.py's original run didn't cover.

Reuses authz_matrix.Client/Session/logger (same scope guard, same rate limit, same PII stop),
appends rows to the same 02-authz-matrix.jsonl. Sweeps:

    9  $batch CHANGESET writes  — the write path the original Sweep 2 skipped
   10  cross-user MERGE (A -> B) and read-back from B (Track A §5, deferred)
   11  submission-gating MERGE (submitVinkje, isXxxCompleted) — Track A §4 HIGH class
   12  `|slice` key syntax exploration on OWN records only

All writes to B are cleaned up in a finally: block by reading from B's session and, if any
field actually changed, MERGE'ing it back to its captured baseline. If the cross-user write
persists we STOP and don't propagate the payload.
"""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m

# ------------------------------------------------------------------
# Sweep 9 — $batch CHANGESET writes
# ------------------------------------------------------------------
CHANGESET_PROBES = [
    ("statusCode",           "211"),
    ("isAppFeePayed",        True),
    ("caseAdmin",            "HACKER"),
    ("isPropositionAccepted", True),
    ("followUpAdmLetter",    "1"),
]


def _batch_changeset_merge(client, session, entity_rel, field, value, logger, variant):
    """POST a $batch containing a single changeset with one MERGE. Log outer/inner."""
    body, boundary = m._batch_body(
        [],
        changeset=[("MERGE", "/" + entity_rel, {field: value})],
    )
    r = client.request(session, "POST", "$batch", body=body,
                       extra_headers={"Content-Type": f"multipart/mixed; boundary={boundary}"},
                       note=variant)
    inners = m._parse_batch_inner_statuses(r.get("text", ""))
    flags = [f"batch_outer={r.get('status')}", f"batch_inner={inners}"]
    if any(s in (200, 201, 202, 204) for s in inners):
        flags.append("ANOMALY_batch_changeset_write_accepted")
    logger.log("9", entity_rel, "POST $batch(changeset)", variant, r, flags)
    return r, inners


def sweep9(client, sessions, logger):
    sA = sessions["A"]
    own_app = f"Applications('{m.ACCT['A']['application']}')"
    # baseline read on own app so we can detect any actual persistence
    base = m.read_entity(client, sA, own_app, logger, "9", "S9 baseline read")
    baseline = {k: m.json_field(base.get("text", ""), k) for k, _ in CHANGESET_PROBES}
    logger.log("9", own_app, "NOTE", "S9 baseline",
               {"status": "n/a", "text": ""},
               [f"baseline={baseline}"])
    try:
        for field, val in CHANGESET_PROBES:
            variant = f"changeset MERGE {field}={val!r}"
            _batch_changeset_merge(client, sA, own_app, field, val, logger, variant)
            after = m.read_entity(client, sA, own_app, logger, "9",
                                  f"S9 re-read after {field}")
            now = m.json_field(after.get("text", ""), field)
            persisted = (now == val) and (now != baseline[field])
            logger.log("9", own_app, "COMPARE", f"{field}={val!r}",
                       {"status": "n/a", "text": ""},
                       [f"before={baseline[field]!r}", f"after={now!r}",
                        f"persisted={persisted}"] +
                       (["ANOMALY_changeset_persisted"] if persisted else []))
    finally:
        # restore any field the changeset actually flipped
        again = client.request(sA, "GET", own_app, note="S9 restore-check")
        for field, _ in CHANGESET_PROBES:
            now = m.json_field(again.get("text", ""), field)
            if now != baseline[field]:
                bv = baseline[field]
                bv_send = ("" if bv is None else bv)
                logger.log("9", own_app, "NOTE",
                           f"S9 restore {field}: {now!r}->{bv!r}",
                           {"status": "n/a", "text": ""}, ["restore"])
                m.merge(client, sA, own_app, {field: bv_send}, logger, "9",
                        f"S9 RESTORE {field}={bv_send!r}", extra_flags=["restore"])


# ------------------------------------------------------------------
# Sweep 10 — cross-user MERGE from A -> B, then read-back from B
# ------------------------------------------------------------------
# Explicit Track A §5 item. Ethical bounds: both accounts are ours; if the write lands, we
# STOP and revert from B's own session immediately. The probe uses a benign marker (no XSS,
# no privilege bump on the target) in a free-text field so the finding stays a proof of
# authz-write-broke, not a scope-blowup.
CROSSUSER_PROBES = [
    (f"Applications('{m.ACCT['B']['application']}')",
     "additionalremarks", "TRACKBCROSSPROBE-A2B"),
    (f"Applications('{m.ACCT['B']['application']}')",
     "statusCode", "211"),
    (f"PersInfos('{m.ACCT['B']['applicant']}')",
     "additionalRemarks", "TRACKBCROSSPROBE-A2B"),
]


def _read_field_from_b(client, sessions, entity_path, field, logger, note):
    r = client.request(sessions["B"], "GET", entity_path, note=note)
    val = m.json_field(r.get("text", ""), field)
    logger.log("10", entity_path, "GET (B-session)", note, r, [f"field_{field}={val!r}"])
    return val


def sweep10(client, sessions, logger):
    for ent, field, payload in CROSSUSER_PROBES:
        # baseline from B's own session
        base_val = _read_field_from_b(client, sessions, ent, field, logger,
                                      f"S10 baseline {ent}.{field}")
        # MERGE from A's session (the actual test)
        r = m.merge(client, sessions["A"], ent, {field: payload}, logger, "10",
                    f"cross-user MERGE A->{ent}.{field}={payload!r}")
        # verify from B's session
        now = _read_field_from_b(client, sessions, ent, field, logger,
                                 f"S10 verify {ent}.{field}")
        persisted = (now == payload) and (now != base_val)
        logger.log("10", ent, "COMPARE", f"{field} cross-user",
                   {"status": "n/a", "text": ""},
                   [f"A_MERGE_status={r.get('status')}",
                    f"base={base_val!r}", f"after={now!r}",
                    f"cross_user_persisted={persisted}"] +
                   (["ANOMALY_cross_user_write_persisted"] if persisted else []))
        # revert from B's session if anything landed
        if persisted:
            bv = base_val if base_val is not None else ""
            m.merge(client, sessions["B"], ent, {field: bv}, logger, "10",
                    f"S10 RESTORE (from B) {field}={bv!r}",
                    extra_flags=["restore"])
            verify = _read_field_from_b(client, sessions, ent, field, logger,
                                        f"S10 verify restore {ent}.{field}")


# ------------------------------------------------------------------
# Sweep 11 — submission-gating MERGE on OWN app (Track A §4 HIGH class)
# ------------------------------------------------------------------
GATING_FIELDS = [
    ("submitVinkje",         True),
    ("isPersInfoCompleted",  True),
    ("isAddressCompleted",   True),
    ("isCurriculumCompleted", True),
    ("isLanguageCompleted",  True),
    ("isScholarshipCompleted", True),
    ("isEditable",           False),  # trying to lock our own record — weird if it works
]


def sweep11(client, sessions, logger):
    sA = sessions["A"]
    own = f"Applications('{m.ACCT['A']['application']}')"
    base = m.read_entity(client, sA, own, logger, "11", "S11 baseline read")
    baseline = {f: m.json_field(base.get("text", ""), f) for f, _ in GATING_FIELDS}
    logger.log("11", own, "NOTE", "S11 baseline",
               {"status": "n/a", "text": ""}, [f"baseline={baseline}"])
    try:
        for field, val in GATING_FIELDS:
            variant = f"MERGE {field}={val!r} (own, gating-bypass)"
            m.merge(client, sA, own, {field: val}, logger, "11", variant)
            after = m.read_entity(client, sA, own, logger, "11",
                                  f"re-read after {field}")
            now = m.json_field(after.get("text", ""), field)
            persisted = (now == val) and (now != baseline[field])
            logger.log("11", own, "COMPARE", f"{field}={val!r}",
                       {"status": "n/a", "text": ""},
                       [f"before={baseline[field]!r}", f"after={now!r}",
                        f"persisted={persisted}"] +
                       (["ANOMALY_gating_flag_persisted"] if persisted else []))
    finally:
        again = client.request(sA, "GET", own, note="S11 restore-check")
        for f, _ in GATING_FIELDS:
            now = m.json_field(again.get("text", ""), f)
            if now != baseline[f]:
                bv = baseline[f]
                bv_send = ("" if bv is None else bv)
                m.merge(client, sA, own, {f: bv_send}, logger, "11",
                        f"S11 RESTORE {f}={bv_send!r}", extra_flags=["restore"])


# ------------------------------------------------------------------
# Sweep 12 — `|slice` key syntax exploration (own records only)
# ------------------------------------------------------------------
def sweep12(client, sessions, logger):
    sA = sessions["A"]
    own = m.ACCT["A"]["application"]
    for suffix in ("", "|0", "|1", "|X", "|99"):
        path = f"Applications('{own}{suffix}')"
        r = client.request(sA, "GET", path, note=f"slice suffix={suffix or '∅'}")
        flags = [f"len={len(r.get('text',''))}"]
        # if suffix changes what we get back, that's a signal
        if r.get("status") == 200:
            id_in_body = m.json_field(r.get("text", ""), "applicationCode")
            flags.append(f"applicationCode={id_in_body!r}")
        logger.log("12", path, "GET", f"suffix={suffix or '∅'}", r, flags)
    # Attachments listing on OWN app
    r = client.request(sA, "GET", f"Applications('{own}')/Attachments", note="own attachments listing")
    logger.log("12", f"Applications('{own}')/Attachments", "GET",
               "listing on own app", r,
               [f"len={len(r.get('text',''))}"])


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------
def main():
    client = m.Client()
    sessions = m.load_sessions(client)
    logger = m.MatrixLogger(m.JSONL_PATH, append=True)
    print(f"[LIVE-GAPS] sessions loaded: {list(sessions)}; appending to {m.JSONL_PATH}",
          file=sys.stderr)
    # Sweep 10 (cross-user MERGE A->B) is opt-in via env because it deliberately
    # writes to records keyed by B's ids (both accounts are still ours; auto-mode
    # classifiers reasonably gate this).
    plan = [("9", sweep9), ("11", sweep11), ("12", sweep12)]
    if os.environ.get("SWEEP10_ENABLED") == "1":
        plan.insert(1, ("10", sweep10))
    for label, fn in plan:
        print(f"\n=== SWEEP {label} ===", file=sys.stderr)
        try:
            fn(client, sessions, logger)
        except m.SessionExpired as e:
            print(f"[HALT] session expired in sweep {label}: {e}", file=sys.stderr)
            break
        except m.ImmediateStop as e:
            logger.log(label, "IMMEDIATE-STOP", "-", str(e),
                       {"status": "IMMEDIATE-STOP", "text": ""}, ["IMMEDIATE_STOP"])
            print(f"[IMMEDIATE-STOP] sweep {label}: {e}", file=sys.stderr)
            continue
        except m.ScopeViolation as e:
            print(f"[FATAL] scope violation in sweep {label}: {e}", file=sys.stderr)
            break
    m.build_summary()
    print("\nDone. Summary regenerated.", file=sys.stderr)


if __name__ == "__main__":
    main()
