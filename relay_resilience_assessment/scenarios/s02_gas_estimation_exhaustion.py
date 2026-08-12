"""
Scenario 2: Gas Estimation Resource Exhaustion
================================================
eth_estimateGas typically requires the backend to *simulate* execution to
find a gas ceiling. If the relay's translation layer forwards the call data
verbatim into a non-EVM simulator without an internal step/time bound, a
call that encodes an unbounded loop (or a deeply recursive call chain) can
hang the simulation thread. If that thread is not isolated per-request, it
can stall the whole relay process for unrelated requests too.

Each case is sent with a bounded client-side timeout (config.REQUEST_TIMEOUT_SECONDS)
so a hang here can't stall the rest of the suite, and is immediately
followed by a liveness probe (plain eth_chainId) to check whether the relay
recovered or stayed wedged.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import client

SCENARIO = "s02_gas_estimation_exhaustion"

DEAD = "0x000000000000000000000000000000000000dE"

# EVM bytecode fragment: JUMPDEST(0x5B) PUSH1 0x00(0x6000) JUMP(0x56) -> `0x5b6000565b`
# 0x5B 0x60 0x00 0x56  is a tight `jumpdest; push1 0; jump` infinite loop.
INFINITE_LOOP_BYTECODE = "0x" + ("5b600056" * 64)

# A call `data` blob built from thousands of nested/repeated pushes to
# approximate unbounded recursive-decode cost on the relay's own parser,
# independent of whatever the backend simulator does with it.
DEEP_CALL_DATA = "0x" + "60016001" * 5000

CASES = [
    (
        "infinite_loop_bytecode_in_data",
        {
            "jsonrpc": "2.0",
            "method": "eth_estimateGas",
            "params": [{"to": DEAD, "data": INFINITE_LOOP_BYTECODE}],
            "id": 1,
        },
    ),
    (
        "no_to_contract_creation_infinite_loop",
        {
            "jsonrpc": "2.0",
            "method": "eth_estimateGas",
            "params": [{"data": INFINITE_LOOP_BYTECODE}],
            "id": 2,
        },
    ),
    (
        "deep_recursive_call_data",
        {
            "jsonrpc": "2.0",
            "method": "eth_estimateGas",
            "params": [{"to": DEAD, "data": DEEP_CALL_DATA}],
            "id": 3,
        },
    ),
    (
        "max_gas_with_loop",
        {
            "jsonrpc": "2.0",
            "method": "eth_estimateGas",
            "params": [
                {
                    "to": DEAD,
                    "data": INFINITE_LOOP_BYTECODE,
                    "gas": "0xffffffffffffffff",
                }
            ],
            "id": 4,
        },
    ),
]


def run():
    results = []
    for case_name, payload in CASES:
        record = client.send(SCENARIO, case_name, payload)
        results.append(record)
        # Immediately check whether the relay is still responsive.
        probe = client.liveness_probe(SCENARIO, case=f"{case_name}__post_probe")
        results.append(probe)
        if probe["result"].get("is_anomaly"):
            probe["result"]["note"] = (
                "Relay failed/hung on liveness probe immediately after "
                f"case '{case_name}' - possible resource exhaustion carryover."
            )
    return results


if __name__ == "__main__":
    for r in run():
        print(r["case"], "->", r["result"].get("status_code"), r["result"].get("anomaly_reasons"))
