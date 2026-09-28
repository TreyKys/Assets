#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track H.1 RERUN — comprehensive programDescription writability test.

Improvements over the first run:
  - Session validation up front (GET Applicants('0'), confirm identity)
  - Control write: batched MERGE of a known-writable non-priv field
    (additionalremarks) to confirm the batch path actually persists data
  - Batched MERGE of programDescription (the primary test)
  - Direct (non-batched) MERGE of programDescription as brief-specified fallback
  - Both self-alias ('0') and real-key addressing
  - CREATE-path probe (MERGE Applications('0') with programDescription)
  - Full restore + verify for every field touched

Budget: ~8 non-safe requests (4 batched + 2 direct + 2 restore), ~8 safe GETs.
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m

APP_A = "000000503432"
ENT_REAL = f"Applications('{APP_A}')"
ENT_SELF = "Applications('0')"
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
    logger.log("h1r", entity_rel, "POST $batch", note, r,
               [f"outer={r.get('status')}", f"inner={inner}",
                f"payload={json.dumps(body_dict)[:120]}"])
    return r.get("status"), inner, r


def direct_merge(client, session, entity_rel, body_dict, logger, note):
    r = client.request(session, "MERGE", entity_rel, body=body_dict, note=note)
    logger.log("h1r", entity_rel, "MERGE", note, r,
               [f"status={r.get('status')}",
                f"payload={json.dumps(body_dict)[:120]}"])
    return r.get("status"), r


def read_and_extract(client, session, entity_rel, fields, logger, note):
    r = m.read_entity(client, session, entity_rel, logger, "h1r", note)
    text = r.get("text", "")
    vals = {}
    for f in fields:
        vals[f] = m.json_field(text, f)
    return r, vals


def save_json(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-interval", type=float, default=8.0)
    args = ap.parse_args()
    m.MIN_INTERVAL = args.min_interval
    print(f"[cadence] MIN_INTERVAL={m.MIN_INTERVAL}", file=sys.stderr)

    client = m.Client()
    logger = m.MatrixLogger(m.JSONL_PATH, append=True)
    sA = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))

    # ---- Step 0a: CSRF + session validation --------------------------------
    print("\n=== Step 0a — session validation ===", file=sys.stderr)
    client.fetch_csrf(sA)
    print(f"  CSRF obtained: {sA.csrf[:12]}...", file=sys.stderr)

    r_id = m.read_entity(client, sA, "Applicants('0')", logger, "h1r",
                          "H1r session identity check")
    id_text = r_id.get("text", "")
    applicant_id = m.json_field(id_text, "inAccountId")
    if not applicant_id:
        applicant_id = m.json_field(id_text, "applicantId")
    print(f"  Identity: inAccountId={applicant_id!r}", file=sys.stderr)
    if applicant_id != "IN01051619":
        print(f"  [HALT] Wrong identity or dead session. Expected IN01051619, got {applicant_id}",
              file=sys.stderr)
        return 1

    # ---- Step 0b: baseline capture -----------------------------------------
    print("\n=== Step 0b — baseline capture (real key + self-alias) ===", file=sys.stderr)
    FIELDS = ["applicationId", "programDescription", "additionalremarks",
              "program", "institution", "statusCode"]

    r_real, vals_real = read_and_extract(client, sA, ENT_REAL, FIELDS, logger,
                                          "H1r baseline real-key")
    r_self, vals_self = read_and_extract(client, sA, ENT_SELF, FIELDS, logger,
                                          "H1r baseline self-alias")

    print(f"  Real-key  applicationId={vals_real['applicationId']!r}  "
          f"programDescription={vals_real['programDescription']!r}", file=sys.stderr)
    print(f"  Self-alias applicationId={vals_self['applicationId']!r}  "
          f"programDescription={vals_self['programDescription']!r}", file=sys.stderr)

    save_json(f"{EVIDENCE_DIR}/rerun_baseline_real.json",
              {"entity": ENT_REAL, "fields": vals_real})
    save_json(f"{EVIDENCE_DIR}/rerun_baseline_self.json",
              {"entity": ENT_SELF, "fields": vals_self})

    baseline_pd = vals_real.get("programDescription") or ""
    baseline_remarks = vals_real.get("additionalremarks") or ""

    results = {}

    try:
        # ---- Step 1: CONTROL — batched MERGE of additionalremarks ----------
        print("\n=== Step 1 — CONTROL: batched MERGE additionalremarks ===",
              file=sys.stderr)
        control_marker = "KLXSSPD_CTRL_RMK"
        outer_c, inner_c, _ = batched_merge(
            client, sA, ENT_REAL,
            {"additionalremarks": control_marker},
            logger, "H1r CONTROL batched MERGE additionalremarks")
        _, vals_c = read_and_extract(client, sA, ENT_REAL,
                                      ["additionalremarks"], logger,
                                      "H1r CONTROL readback")
        ctrl_written = (vals_c["additionalremarks"] == control_marker)
        print(f"  outer={outer_c} inner={inner_c}", file=sys.stderr)
        print(f"  readback={vals_c['additionalremarks']!r}  written={ctrl_written}",
              file=sys.stderr)
        results["control_batched"] = {
            "field": "additionalremarks",
            "outer": outer_c, "inner": inner_c,
            "readback": vals_c["additionalremarks"],
            "written": ctrl_written,
        }

        # ---- Step 1b: CONTROL — direct MERGE of additionalremarks ----------
        print("\n=== Step 1b — CONTROL: direct MERGE additionalremarks ===",
              file=sys.stderr)
        control_marker2 = "KLXSSPD_CTRL_DIR"
        st_cd, _ = direct_merge(
            client, sA, ENT_REAL,
            {"additionalremarks": control_marker2},
            logger, "H1r CONTROL direct MERGE additionalremarks")
        _, vals_cd = read_and_extract(client, sA, ENT_REAL,
                                       ["additionalremarks"], logger,
                                       "H1r CONTROL direct readback")
        ctrl_dir_written = (vals_cd["additionalremarks"] == control_marker2)
        print(f"  status={st_cd}  readback={vals_cd['additionalremarks']!r}  "
              f"written={ctrl_dir_written}", file=sys.stderr)
        results["control_direct"] = {
            "field": "additionalremarks",
            "status": st_cd,
            "readback": vals_cd["additionalremarks"],
            "written": ctrl_dir_written,
        }

        # ---- Step 2: PRIMARY — batched MERGE programDescription (real key) -
        print("\n=== Step 2 — batched MERGE programDescription (real key) ===",
              file=sys.stderr)
        inert = "KLXSSPD_INERT_2"
        outer_2, inner_2, _ = batched_merge(
            client, sA, ENT_REAL,
            {"programDescription": inert},
            logger, "H1r batched MERGE programDescription real-key")
        _, vals_2 = read_and_extract(client, sA, ENT_REAL,
                                      ["programDescription"], logger,
                                      "H1r batched readback real-key")
        bat_written = (vals_2["programDescription"] == inert)
        print(f"  outer={outer_2} inner={inner_2}", file=sys.stderr)
        print(f"  readback={vals_2['programDescription']!r}  written={bat_written}",
              file=sys.stderr)
        results["batched_merge_realkey"] = {
            "outer": outer_2, "inner": inner_2,
            "readback": vals_2["programDescription"],
            "written": bat_written,
        }

        # ---- Step 2b: batched MERGE programDescription (self-alias) --------
        print("\n=== Step 2b — batched MERGE programDescription (self-alias) ===",
              file=sys.stderr)
        inert_s = "KLXSSPD_INERT_2S"
        outer_2s, inner_2s, _ = batched_merge(
            client, sA, ENT_SELF,
            {"programDescription": inert_s},
            logger, "H1r batched MERGE programDescription self-alias")
        _, vals_2s = read_and_extract(client, sA, ENT_REAL,
                                       ["programDescription"], logger,
                                       "H1r batched readback self-alias")
        bat_s_written = (vals_2s["programDescription"] == inert_s)
        print(f"  outer={outer_2s} inner={inner_2s}", file=sys.stderr)
        print(f"  readback={vals_2s['programDescription']!r}  written={bat_s_written}",
              file=sys.stderr)
        results["batched_merge_selfalias"] = {
            "outer": outer_2s, "inner": inner_2s,
            "readback": vals_2s["programDescription"],
            "written": bat_s_written,
        }

        # ---- Step 3: FALLBACK — direct MERGE programDescription ------------
        print("\n=== Step 3 — direct MERGE programDescription ===",
              file=sys.stderr)
        inert_d = "KLXSSPD_INERT_3D"
        st_3, _ = direct_merge(
            client, sA, ENT_REAL,
            {"programDescription": inert_d},
            logger, "H1r direct MERGE programDescription")
        _, vals_3 = read_and_extract(client, sA, ENT_REAL,
                                      ["programDescription"], logger,
                                      "H1r direct readback")
        dir_written = (vals_3["programDescription"] == inert_d)
        print(f"  status={st_3}  readback={vals_3['programDescription']!r}  "
              f"written={dir_written}", file=sys.stderr)
        results["direct_merge"] = {
            "status": st_3,
            "readback": vals_3["programDescription"],
            "written": dir_written,
        }

        # ---- Step 3b: HTML probe (only if ANY write path succeeded) --------
        any_written = bat_written or bat_s_written or dir_written
        if any_written:
            print("\n=== Step 3b — non-executing HTML probes ===", file=sys.stderr)

            # <b> tag
            b_payload = "<b>KLXSSPD_B1</b>"
            st_b, _ = direct_merge(
                client, sA, ENT_REAL,
                {"programDescription": b_payload},
                logger, "H1r HTML probe <b>")
            _, vals_b = read_and_extract(client, sA, ENT_REAL,
                                          ["programDescription"], logger,
                                          "H1r HTML probe <b> readback")
            b_class = classify_readback(vals_b["programDescription"], "KLXSSPD_B1", b_payload)
            print(f"  <b>: status={st_b}  readback={vals_b['programDescription']!r}  "
                  f"class={b_class}", file=sys.stderr)
            results["html_b_tag"] = {
                "status": st_b,
                "readback": vals_b["programDescription"],
                "classification": b_class,
            }

            # <img src=x> (NO onerror)
            img_payload = "<img src=x>KLXSSPD_I1"
            st_i, _ = direct_merge(
                client, sA, ENT_REAL,
                {"programDescription": img_payload},
                logger, "H1r HTML probe <img> no handler")
            _, vals_i = read_and_extract(client, sA, ENT_REAL,
                                          ["programDescription"], logger,
                                          "H1r HTML probe <img> readback")
            i_class = classify_readback(vals_i["programDescription"], "KLXSSPD_I1", img_payload)
            print(f"  <img>: status={st_i}  readback={vals_i['programDescription']!r}  "
                  f"class={i_class}", file=sys.stderr)
            results["html_img_tag"] = {
                "status": st_i,
                "readback": vals_i["programDescription"],
                "classification": i_class,
            }
        else:
            print("\n=== Step 3b — SKIPPED (no write path succeeded) ===",
                  file=sys.stderr)
            results["html_probes"] = "skipped_not_writable"

        # ---- Step 4: CREATE-path -------------------------------------------
        print("\n=== Step 4 — CREATE-path: MERGE Applications('0') ===",
              file=sys.stderr)
        # List current applications
        r_list_b = m.read_entity(client, sA, "Applications", logger, "h1r",
                                  "H1r CREATE list-before")
        try:
            before_rows = json.loads(r_list_b.get("text","")).get("d",{}).get("results",[])
        except Exception:
            before_rows = []
        before_ids = {str(r.get("applicationId","")).strip() for r in before_rows}
        before_ids.discard("")
        print(f"  rows_before={len(before_ids)} ids={sorted(before_ids)[:5]}",
              file=sys.stderr)

        create_payload = {"programDescription": "KLXSSPD_CREATE_2"}
        outer_cr, inner_cr, raw_cr = batched_merge(
            client, sA, ENT_SELF,
            create_payload, logger,
            "H1r CREATE-path MERGE Applications('0')")

        r_list_a = m.read_entity(client, sA, "Applications", logger, "h1r",
                                  "H1r CREATE list-after")
        try:
            after_rows = json.loads(r_list_a.get("text","")).get("d",{}).get("results",[])
        except Exception:
            after_rows = []
        after_ids = {str(r.get("applicationId","")).strip() for r in after_rows}
        after_ids.discard("")
        new_ids = after_ids - before_ids
        create_verdict = "CREATE_LANDED" if new_ids else "CREATE_REJECTED"
        print(f"  outer={outer_cr} inner={inner_cr}", file=sys.stderr)
        print(f"  rows_after={len(after_ids)} new_ids={sorted(new_ids)}",
              file=sys.stderr)
        print(f"  verdict={create_verdict}", file=sys.stderr)
        results["create_path"] = {
            "outer": outer_cr, "inner": inner_cr,
            "rows_before": len(before_ids),
            "rows_after": len(after_ids),
            "new_ids": sorted(new_ids),
            "verdict": create_verdict,
        }

        # If created, check programDescription on the new record + delete
        if new_ids:
            for nid in sorted(new_ids):
                print(f"\n  CREATE inspect+cleanup: Applications('{nid}')",
                      file=sys.stderr)
                _, vals_new = read_and_extract(
                    client, sA, f"Applications('{nid}')",
                    ["programDescription", "applicationId"], logger,
                    f"H1r CREATE inspect {nid}")
                print(f"    programDescription={vals_new['programDescription']!r}",
                      file=sys.stderr)
                results["create_path"]["new_programDescription"] = vals_new["programDescription"]
                try:
                    rd = client.request(sA, "DELETE", f"Applications('{nid}')",
                                         note=f"H1r CREATE cleanup delete {nid}")
                    logger.log("h1r", f"Applications('{nid}')", "DELETE",
                                f"cleanup delete", rd,
                                [f"delete_status={rd.get('status')}"])
                    print(f"    delete status={rd.get('status')}", file=sys.stderr)
                except Exception as e:
                    print(f"    delete err: {e}", file=sys.stderr)

    finally:
        # ---- Step 5: RESTORE -----------------------------------------------
        print("\n=== Step 5 — restore ===", file=sys.stderr)
        restore_body = {
            "programDescription": baseline_pd,
            "additionalremarks": baseline_remarks,
        }
        # Restore via direct MERGE (most reliable path)
        try:
            st_r, _ = direct_merge(client, sA, ENT_REAL, restore_body,
                                    logger, f"H1r RESTORE (direct)")
            print(f"  restore status={st_r}", file=sys.stderr)
        except Exception as e:
            print(f"  restore direct err: {e} — trying batched", file=sys.stderr)
            batched_merge(client, sA, ENT_REAL, restore_body, logger,
                          "H1r RESTORE (batched fallback)")

        # Verify
        _, vals_v = read_and_extract(client, sA, ENT_REAL,
                                      ["programDescription", "additionalremarks"],
                                      logger, "H1r RESTORE verify")
        pd_ok = (str(vals_v.get("programDescription") or "") == str(baseline_pd))
        rm_ok = (str(vals_v.get("additionalremarks") or "") == str(baseline_remarks))
        print(f"  programDescription restored: {pd_ok}  "
              f"(expected={baseline_pd!r}, got={vals_v['programDescription']!r})",
              file=sys.stderr)
        print(f"  additionalremarks restored:  {rm_ok}  "
              f"(expected={baseline_remarks!r}, got={vals_v['additionalremarks']!r})",
              file=sys.stderr)
        results["restore"] = {
            "programDescription_ok": pd_ok,
            "additionalremarks_ok": rm_ok,
            "programDescription_observed": vals_v.get("programDescription"),
            "additionalremarks_observed": vals_v.get("additionalremarks"),
        }
        if not (pd_ok and rm_ok):
            print("\n  [WARN] cleanup incomplete — check manually", file=sys.stderr)

    # ---- Summary -----------------------------------------------------------
    print("\n=== H1r RERUN SUMMARY ===", file=sys.stderr)
    save_json(f"{EVIDENCE_DIR}/rerun_results.json", results)

    any_pd_written = any(
        results.get(k, {}).get("written", False)
        for k in ["batched_merge_realkey", "batched_merge_selfalias", "direct_merge"]
    )
    create_landed = results.get("create_path", {}).get("verdict") == "CREATE_LANDED"

    print(f"\n  Control (additionalremarks):", file=sys.stderr)
    print(f"    batched: written={results.get('control_batched',{}).get('written')}",
          file=sys.stderr)
    print(f"    direct:  written={results.get('control_direct',{}).get('written')}",
          file=sys.stderr)

    print(f"\n  programDescription:", file=sys.stderr)
    print(f"    batched real-key:   written={results.get('batched_merge_realkey',{}).get('written')}",
          file=sys.stderr)
    print(f"    batched self-alias: written={results.get('batched_merge_selfalias',{}).get('written')}",
          file=sys.stderr)
    print(f"    direct MERGE:       written={results.get('direct_merge',{}).get('written')}",
          file=sys.stderr)

    print(f"\n  CREATE-path: {results.get('create_path',{}).get('verdict')}", file=sys.stderr)

    if any_pd_written:
        if results.get("html_b_tag", {}).get("classification") == "stored_RAW":
            print("\n  *** STORED RAW HTML *** — XSS via innerHTML sink confirmed",
                  file=sys.stderr)
        elif results.get("html_img_tag", {}).get("classification") == "stored_RAW":
            print("\n  *** STORED RAW HTML *** — XSS via innerHTML sink confirmed",
                  file=sys.stderr)
        else:
            cls = results.get("html_b_tag", {}).get("classification", "?")
            print(f"\n  Writable but HTML classification: {cls}", file=sys.stderr)
    else:
        print("\n  VERDICT: NOT WRITABLE — programDescription silent-drop "
              "on all paths tested", file=sys.stderr)

    if create_landed:
        pd_val = results.get("create_path", {}).get("new_programDescription")
        print(f"\n  CREATE-path: programDescription={pd_val!r}", file=sys.stderr)

    print(f"\n  Restore: pd_ok={results['restore']['programDescription_ok']}  "
          f"remarks_ok={results['restore']['additionalremarks_ok']}", file=sys.stderr)

    return 0


def classify_readback(observed, marker, payload):
    if observed is None:
        return "readback_none"
    s = str(observed)
    if s == payload:
        return "stored_RAW"
    if ("&lt;" in s or "&gt;" in s or "&amp;" in s) and marker in s:
        return "stored_encoded"
    if marker in s and "<" not in s and ">" not in s:
        return "stored_stripped_marker_kept"
    if marker in s and "<" in s:
        return "stored_partial"
    return "unchanged_or_other"


if __name__ == "__main__":
    sys.exit(main())
