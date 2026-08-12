"""
Scenario 5: Object Property Name Pollution
=============================================
If the relay is implemented in (or has middleware written in) JavaScript /
Node.js, naive object merging (`Object.assign`, spread, deep-merge libraries,
or manual `for..in` copy loops) can be tricked into writing to
`Object.prototype` via `__proto__`, `constructor`, or `constructor.prototype`
keys, corrupting global object behavior for the whole process - not just the
one request. Even non-JS backends sometimes reflect these keys back
verbatim, or crash on reserved attribute names, which is itself worth
recording.

We inject these keys at multiple nesting depths inside JSON-RPC params and
watch for: reflected pollution in the response, behavioral change in a
follow-up "control" request, or an outright error.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import client

SCENARIO = "s05_prototype_pollution"

ADDR = "0x000000000000000000000000000000000000dE"

CASES = [
    (
        "proto_top_level_params_object",
        {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": ADDR, "__proto__": {"polluted": True}}, "latest"],
            "id": 1,
        },
    ),
    (
        "constructor_prototype_chain",
        {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [
                {"to": ADDR, "constructor": {"prototype": {"polluted": True}}},
                "latest",
            ],
            "id": 2,
        },
    ),
    (
        "proto_at_request_root",
        {
            "jsonrpc": "2.0",
            "method": "eth_chainId",
            "params": [],
            "id": 3,
            "__proto__": {"jsonrpc": "9.9"},
        },
    ),
    (
        "deeply_nested_proto",
        {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [
                {"to": ADDR, "nested": {"level2": {"level3": {"__proto__": {"toString": "polluted"}}}}},
                "latest",
            ],
            "id": 4,
        },
    ),
    (
        "proto_as_string_literal_key_via_raw_json",
        '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"' + ADDR + '","__proto__":"literal_string_not_object"}],"id":5}',
    ),
]


def run():
    results = []
    for case_name, payload in CASES:
        results.append(client.send(SCENARIO, case_name, payload))

    # Control request sent AFTER the pollution attempts: if the relay process
    # is long-lived and shares JS object prototypes across requests, a
    # completely unrelated call might now behave differently (e.g. return an
    # unexpected extra field, or error where it previously succeeded).
    control = client.send(
        SCENARIO,
        "control_request_after_pollution_attempts",
        {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": "control"},
    )
    results.append(control)
    return results


if __name__ == "__main__":
    for r in run():
        print(r["case"], "->", r["result"].get("status_code"), r["result"].get("anomaly_reasons"))
