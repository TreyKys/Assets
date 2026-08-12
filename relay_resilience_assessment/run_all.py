#!/usr/bin/env python3
"""
Runs all 10 resilience scenarios against config.TARGET_URL, then generates
the markdown report. Scenarios run sequentially (the shared rate limiter in
harness/client.py already caps every request at RATE_LIMIT_RPS, so running
them one after another - rather than in parallel - is what keeps the whole
suite, not just each scenario individually, under that ceiling).

Usage:
    python run_all.py
    RELAY_TARGET_URL=http://127.0.0.1:7546 python run_all.py
    python run_all.py --skip slow_body   # slow_body takes minutes at the
                                          # assessment's reference 10s/byte rate
"""
import argparse
import importlib
import sys
import time

import config

SCENARIO_MODULES = [
    "s01_duplicate_keys",
    "s02_gas_estimation_exhaustion",
    "s03_hex_integer_boundaries",
    "s04_state_cache_consistency",
    "s05_prototype_pollution",
    "s06_ecdsa_signature_edge_cases",
    "s07_null_byte_unicode",
    "s08_deeply_nested_arrays",
    "s09_method_case_normalization",
    "s10_slow_body_transmission",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip", nargs="*", default=[],
        help="substrings of scenario module names to skip, e.g. --skip slow_body",
    )
    parser.add_argument(
        "--slow-body-delay", type=float, default=10.0,
        help="seconds between bytes for scenario 10 (default matches the assessment spec: 10)",
    )
    parser.add_argument(
        "--slow-body-max-wait", type=float, default=60.0,
        help="give up scenario 10 after this many seconds total",
    )
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args()

    print(f"Target: {config.TARGET_URL}")
    print(f"Rate limit: {config.RATE_LIMIT_RPS} req/s | anomaly latency threshold: {config.ANOMALY_LATENCY_SECONDS}s\n")

    sys.path.insert(0, ".")
    total_anomalies = 0

    for mod_name in SCENARIO_MODULES:
        if any(s in mod_name for s in args.skip):
            print(f"[skip] {mod_name}")
            continue

        print(f"[run ] {mod_name}")
        mod = importlib.import_module(f"scenarios.{mod_name}")
        t0 = time.monotonic()

        if mod_name == "s10_slow_body_transmission":
            results = mod.run(args.slow_body_delay, 1, args.slow_body_max_wait)
        else:
            results = mod.run()

        elapsed = time.monotonic() - t0
        anomalies = sum(1 for r in results if isinstance(r, dict) and r.get("result", {}).get("is_anomaly"))
        total_anomalies += anomalies
        print(f"       {len(results)} case(s), {anomalies} anomaly(ies), {elapsed:.1f}s")

    print(f"\nTotal anomalies recorded this run: {total_anomalies}")
    print(f"Raw logs: {config.ALL_REQUESTS_LOG}")
    print(f"Anomaly detail files: {config.ANOMALY_DIR}")

    if not args.no_report:
        import generate_report
        report_path = generate_report.main()
        print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
