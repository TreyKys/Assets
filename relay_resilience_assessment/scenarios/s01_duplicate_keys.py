"""
Scenario 1: Duplicate JSON Keys and Parser Inconsistency
==========================================================
RFC 8259 does not define behavior for duplicate object keys, so different
JSON parsers (the HTTP framework's body parser, a validation middleware, the
backend translation layer) can legally disagree about which occurrence
"wins". If the relay validates one occurrence but a downstream layer acts on
another, an attacker can smuggle a request past a method allow-list.

We send raw JSON text (not a Python dict - dicts can't hold duplicate keys)
with the target key duplicated in several positions, and inspect which
method the relay actually executed by comparing the response shape to what
each candidate method should return.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import client

SCENARIO = "s01_duplicate_keys"

CASES = [
    (
        "method_dup_last_wins_candidate",
        '{"jsonrpc":"2.0","method":"eth_chainId","method":"eth_sendRawTransaction","params":[],"id":1}',
    ),
    (
        "method_dup_first_wins_candidate",
        '{"jsonrpc":"2.0","method":"eth_sendRawTransaction","method":"eth_chainId","params":[],"id":2}',
    ),
    (
        "id_duplicated",
        '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1,"id":999}',
    ),
    (
        "params_duplicated_conflicting",
        '{"jsonrpc":"2.0","method":"eth_getBalance","params":["0x0000000000000000000000000000000000dEaD","latest"],"params":["0xffffffffffffffffffffffffffffffffffffffff","latest"],"id":3}',
    ),
    (
        "jsonrpc_version_duplicated",
        '{"jsonrpc":"2.0","jsonrpc":"1.0","method":"eth_chainId","params":[],"id":4}',
    ),
    (
        "nested_params_object_dup_keys",
        '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0x0000000000000000000000000000000000dEaD","to":"0x000000000000000000000000000000000000FF"},"latest"],"id":5}',
    ),
    (
        "three_way_method_duplication",
        '{"jsonrpc":"2.0","method":"eth_chainId","method":"eth_blockNumber","method":"eth_sendRawTransaction","params":[],"id":6}',
    ),
]


def run():
    results = []
    for case_name, raw_json in CASES:
        record = client.send(SCENARIO, case_name, raw_json)
        results.append(record)
    return results


if __name__ == "__main__":
    for r in run():
        print(r["case"], "->", r["result"].get("status_code"), r["result"].get("anomaly_reasons"))
