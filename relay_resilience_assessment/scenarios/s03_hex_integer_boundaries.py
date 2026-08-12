"""
Scenario 3: Hex and Integer Boundary Handling
===============================================
EVM values (balances, gas, value, block numbers) are canonically 256-bit
unsigned integers. A relay translating to a non-EVM backend has to convert
hex strings to whatever native integer type the backend uses. This scenario
probes the conversion boundary: values at/over 2**256-1, negative-looking
hex, malformed hex, and non-canonical encodings (odd-length, missing
prefix, upper/lower case mixing, leading zeros).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import client

SCENARIO = "s03_hex_integer_boundaries"

MAX_U256 = "0x" + "f" * 64  # 2**256 - 1
OVER_U256 = "0x1" + "0" * 64  # 2**256
WAY_OVER_U256 = "0x" + "f" * 128  # far beyond 256 bits

ADDR = "0x000000000000000000000000000000000000dE"

CASES = [
    ("value_at_u256_max", {"to": ADDR, "value": MAX_U256}),
    ("value_over_u256_max", {"to": ADDR, "value": OVER_U256}),
    ("value_way_over_u256", {"to": ADDR, "value": WAY_OVER_U256}),
    ("gas_price_over_u256", {"to": ADDR, "gasPrice": OVER_U256}),
    ("negative_hex_style", {"to": ADDR, "value": "-0x1"}),
    ("hex_no_prefix", {"to": ADDR, "value": "ff"}),
    ("hex_odd_length", {"to": ADDR, "value": "0xfff"}),
    ("hex_invalid_chars", {"to": ADDR, "value": "0xZZZZ"}),
    ("hex_empty", {"to": ADDR, "value": "0x"}),
    ("hex_excess_leading_zeros", {"to": ADDR, "value": "0x" + "0" * 60 + "1"}),
    ("hex_mixed_case", {"to": ADDR, "value": "0xAbCdEf1234567890"}),
    ("block_number_over_u256", "0x" + "f" * 100),
    ("value_as_decimal_string_not_hex", {"to": ADDR, "value": "115792089237316195423570985008687907853269984665640564039457584007913129639935"}),
    ("value_as_json_number_not_string", {"to": ADDR, "value": 999999999999999999999999999999999999999999999}),
]


def run():
    results = []

    for case_name, extra in CASES[:11] + CASES[13:]:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [extra, "latest"],
            "id": case_name,
        }
        results.append(client.send(SCENARIO, case_name, payload))

    # block number boundary case uses eth_getBalance's block tag param directly
    case_name, block_val = CASES[11]
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [ADDR, block_val],
        "id": case_name,
    }
    results.append(client.send(SCENARIO, case_name, payload))

    return results


if __name__ == "__main__":
    for r in run():
        print(r["case"], "->", r["result"].get("status_code"), r["result"].get("anomaly_reasons"))
