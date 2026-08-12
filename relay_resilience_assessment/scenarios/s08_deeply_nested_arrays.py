"""
Scenario 8: Deeply Nested Arrays
====================================
Most JSON decoders are implemented recursively (one stack frame per nesting
level). A payload nested thousands of levels deep can exhaust the parser's
call stack before any application-level size/depth limit is even checked,
crashing the worker process with an unhandled RecursionError/StackOverflow
instead of returning a clean JSON-RPC error. We test a range of depths to
find where behavior changes (clean 4xx error vs. connection drop/500).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import client

SCENARIO = "s08_deeply_nested_arrays"

DEPTHS = [10, 100, 1000, 5000, 20000]


def _nested_array_json(depth: int) -> str:
    """Build the raw JSON text directly (not via json.dumps on a Python
    object) so we aren't bottlenecked by *our own* recursion limits - this
    is pure string concatenation."""
    return "[" * depth + "]" * depth


def run():
    results = []
    for depth in DEPTHS:
        nested = _nested_array_json(depth)
        payload = (
            '{"jsonrpc":"2.0","method":"eth_call",'
            f'"params":[{{"to":"0x000000000000000000000000000000000000dE",'
            f'"data":"0x00","aux":{nested}}},"latest"],"id":"{depth}"}}'
        )
        results.append(client.send(SCENARIO, f"depth_{depth}", payload))
    return results


if __name__ == "__main__":
    for r in run():
        print(r["case"], "->", r["result"].get("status_code"), r["result"].get("anomaly_reasons"))
