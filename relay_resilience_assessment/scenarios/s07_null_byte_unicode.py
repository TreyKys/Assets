"""
Scenario 7: Null Byte and Unicode Input Handling
====================================================
String fields pass through multiple layers (HTTP framework -> JSON decoder
-> validation -> backend serialization). Each layer may normalize, strip, or
choke on embedded NUL (\\u0000), zero-width/combining characters, RTL
override characters, astral-plane emoji requiring surrogate pairs, or
overlong/invalid UTF-8 sequences differently - producing inconsistent
behavior an attacker could exploit (e.g. a filter checks the pre-strip
string, the backend acts on the post-strip one).

Null bytes and lone surrogates are built with explicit \\uXXXX escapes
(rather than typed as literal source characters) so this file itself stays
plain ASCII and unambiguous to read/diff.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import client

SCENARIO = "s07_null_byte_unicode"

ADDR = "0x000000000000000000000000000000000000dE"

NUL = "\u0000"
SKULL_EMOJI = "\U0001F480"  # astral-plane, requires a UTF-16 surrogate pair
COLLISION_EMOJI = "\U0001F4A5"
RTL_OVERRIDE = "‮"
ZERO_WIDTH_JOINER = "‍"
COMBINING_ACUTE = "́"

CASES = [
    ("embedded_null_byte_in_id", {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": f"abc{NUL}def"}),
    ("null_byte_in_data_field", {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": ADDR, "data": f"0x00{NUL}00"}], "id": 1}),
    ("multibyte_emoji_in_id", {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": SKULL_EMOJI + COLLISION_EMOJI}),
    ("astral_surrogate_pair_raw", '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":"\\ud83d\\udc80"}'),
    ("lone_high_surrogate_invalid", '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":"\\ud800"}'),
    ("rtl_override_in_method", {"jsonrpc": "2.0", "method": "eth_chainId" + RTL_OVERRIDE, "params": [], "id": 2}),
    ("zero_width_joiner_in_method", {"jsonrpc": "2.0", "method": "eth" + ZERO_WIDTH_JOINER + "_chainId", "params": [], "id": 3}),
    ("combining_diacritics_flood", {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": "e" + COMBINING_ACUTE * 200}),
    ("overlong_utf8_raw_bytes", b'{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":"\xc0\xaf"}'),
    ("null_byte_as_literal_string_prefix", {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": " " + ADDR}], "id": 4}),
]


def run():
    results = []
    for case_name, payload in CASES:
        results.append(client.send(SCENARIO, case_name, payload))
    return results


if __name__ == "__main__":
    for r in run():
        print(r["case"], "->", r["result"].get("status_code"), r["result"].get("anomaly_reasons"))
