#!/usr/bin/env python3
"""
Parses logs/all_requests.jsonl and logs/anomalies.jsonl and writes a
markdown report to reports/report.md summarizing, per scenario:
  - how many cases were run
  - how many were anomalous, and why
  - the exact payload for each anomaly (for reproduction)
"""
import json
import os
import time
from collections import defaultdict

import config

SCENARIO_TITLES = {
    "s01_duplicate_keys": "Duplicate JSON Keys and Parser Inconsistency",
    "s02_gas_estimation_exhaustion": "Gas Estimation Resource Exhaustion",
    "s03_hex_integer_boundaries": "Hex and Integer Boundary Handling",
    "s04_state_cache_consistency": "State Cache Consistency After Reverts",
    "s05_prototype_pollution": "Object Property Name Pollution",
    "s06_ecdsa_signature_edge_cases": "ECDSA Signature Edge Cases",
    "s07_null_byte_unicode": "Null Byte and Unicode Input Handling",
    "s08_deeply_nested_arrays": "Deeply Nested Arrays",
    "s09_method_case_normalization": "RPC Method Case Normalization",
    "s10_slow_body_transmission": "Slow HTTP Body Transmission",
}


def _load_jsonl(path):
    records = []
    if not os.path.exists(path):
        return records
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
    return records


def main():
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    all_records = _load_jsonl(config.ALL_REQUESTS_LOG)
    anomaly_records = _load_jsonl(config.ANOMALIES_LOG)

    by_scenario = defaultdict(list)
    for r in all_records:
        by_scenario[r.get("scenario", "unknown")].append(r)

    anomalies_by_scenario = defaultdict(list)
    for r in anomaly_records:
        anomalies_by_scenario[r.get("scenario", "unknown")].append(r)

    lines = []
    lines.append("# JSON-RPC Relay Resilience Assessment Report")
    lines.append("")
    lines.append(f"- **Target:** `{config.TARGET_URL}`")
    lines.append(f"- **Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    lines.append(f"- **Rate limit applied:** {config.RATE_LIMIT_RPS} req/s")
    lines.append(f"- **Anomaly latency threshold:** {config.ANOMALY_LATENCY_SECONDS}s")
    total_cases = len(all_records)
    total_anomalies = len(anomaly_records)
    lines.append(f"- **Total requests logged:** {total_cases}")
    lines.append(f"- **Total anomalies:** {total_anomalies}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| # | Scenario | Cases | Anomalies |")
    lines.append("|---|----------|-------|-----------|")
    for i, (mod_name, title) in enumerate(SCENARIO_TITLES.items(), start=1):
        n_cases = len(by_scenario.get(mod_name, []))
        n_anom = len(anomalies_by_scenario.get(mod_name, []))
        flag = " ⚠️" if n_anom else ""
        lines.append(f"| {i} | {title} | {n_cases} | {n_anom}{flag} |")
    lines.append("")

    if total_anomalies == 0 and total_cases == 0:
        lines.append(
            "> No log data found. Run `python run_all.py` (or an individual "
            "`scenarios/sNN_*.py` script) against a reachable target before "
            "generating a report."
        )

    lines.append("## Findings by Scenario")
    lines.append("")
    for mod_name, title in SCENARIO_TITLES.items():
        lines.append(f"### {title} (`{mod_name}`)")
        lines.append("")
        cases = by_scenario.get(mod_name, [])
        anomalies = anomalies_by_scenario.get(mod_name, [])
        if not cases:
            lines.append("_Not run._")
            lines.append("")
            continue

        if not anomalies:
            lines.append(f"No anomalies across {len(cases)} case(s). All responses used "
                          "standard JSON-RPC error codes / expected latency.")
            lines.append("")
            continue

        lines.append(f"**{len(anomalies)} anomaly(ies) out of {len(cases)} case(s):**")
        lines.append("")
        for a in anomalies:
            case = a.get("case", "?")
            result = a.get("result", {})
            reasons = ", ".join(result.get("anomaly_reasons", [])) or "unspecified"
            status = result.get("status_code")
            elapsed = result.get("elapsed_seconds")
            elapsed_display = f"{elapsed}s" if elapsed is not None else "n/a"
            error = result.get("error")
            payload = a.get("payload", {})
            payload_text = payload.get("raw") if isinstance(payload, dict) and not payload.get("truncated") else payload

            lines.append(f"- **Case:** `{case}`")
            lines.append(f"  - Reasons: `{reasons}`")
            lines.append(f"  - HTTP status: `{status}` | elapsed: `{elapsed_display}`" + (f" | error: `{error}`" if error else ""))
            lines.append("  - Payload:")
            lines.append("    ```json")
            snippet = str(payload_text)
            if len(snippet) > 1500:
                snippet = snippet[:1500] + f"... [truncated, {len(str(payload_text))} chars total]"
            for line in snippet.splitlines() or [snippet]:
                lines.append(f"    {line}")
            lines.append("    ```")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- \"Anomaly\" = HTTP >= 500, dropped/reset connection, response time over "
        f"{config.ANOMALY_LATENCY_SECONDS}s, or a non-JSON body where JSON was expected. "
        "A 4xx JSON-RPC error response (e.g. `-32600 Invalid Request`) is normal, "
        "expected behavior and is *not* flagged."
    )
    lines.append(
        "- Scenario 4 (state cache consistency) and Scenario 6 (ECDSA edge cases) "
        "produce structurally representative payloads but a fully conclusive verdict "
        "requires pairing them with your actual deployed test contract / a real "
        "signer, since this harness has no private key material or contract bytecode "
        "of its own."
    )
    lines.append(
        "- Re-run individual scenario scripts directly (`python scenarios/sNN_*.py`) "
        "to iterate on a single finding without re-running the whole suite."
    )
    lines.append("")

    report_path = os.path.join(config.REPORT_DIR, "report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    return report_path


if __name__ == "__main__":
    print(main())
