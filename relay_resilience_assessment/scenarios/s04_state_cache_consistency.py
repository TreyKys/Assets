"""
Scenario 4: State Cache Consistency After Reverts
====================================================
If the relay caches simulation/state results (e.g. to answer repeated
eth_call queries cheaply), a revert must invalidate the right cache entries.
This scenario issues a state-reading eth_call, then a call constructed to
revert, then immediately repeats the original eth_call and diffs the two
"before" and "after" responses.

Caveat: without deployed contract bytecode on the target backend we cannot
force a *guaranteed* on-chain revert; this exercises the relay's caching /
response-consistency behavior around a call sequence that a real revert
would produce, and the report notes this scenario needs to be re-run against
your actual deployed test contract for a definitive verdict.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import client

SCENARIO = "s04_state_cache_consistency"

TARGET_ADDR = "0x000000000000000000000000000000000000dE"

# `revert()` with no reason: PUSH1 0x00 PUSH1 0x00 REVERT -> 0x60006000fd
REVERT_DATA = "0x60006000fd"
# Arbitrary "read" selector - keccak4('balanceOf(address)') stand-in, any 4 bytes
READ_DATA = "0x70a08231000000000000000000000000000000000000000000000000000000000000dead"


def _eth_call(data, tag="latest"):
    return {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": TARGET_ADDR, "data": data}, tag],
        "id": "state_cache",
    }


def run():
    results = []

    before = client.send(SCENARIO, "read_before_revert", _eth_call(READ_DATA))
    results.append(before)

    reverting = client.send(SCENARIO, "call_designed_to_revert", _eth_call(REVERT_DATA))
    results.append(reverting)

    after = client.send(SCENARIO, "read_immediately_after_revert", _eth_call(READ_DATA))
    results.append(after)

    # Repeat once more after a short pause to see if a cache TTL masks the
    # inconsistency on the first re-read but not the second.
    after_2 = client.send(SCENARIO, "read_after_revert_second_pass", _eth_call(READ_DATA))
    results.append(after_2)

    before_body = before["result"].get("body_preview")
    after_body = after["result"].get("body_preview")
    if before_body is not None and before_body == after_body:
        note = {
            "case": "cache_diff_note",
            "observation": (
                "Response body after the reverting call is byte-identical to "
                "the response before it. This is EXPECTED if the read is "
                "genuinely idempotent and state didn't change - it only "
                "indicates a caching bug if you know the backend state "
                "actually differs after the revert path executed server-side."
            ),
        }
        results.append(note)

    return results


if __name__ == "__main__":
    for r in run():
        if "result" in r:
            print(r["case"], "->", r["result"].get("status_code"), r["result"].get("anomaly_reasons"))
        else:
            print(r)
