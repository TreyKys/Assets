"""
Scenario 6: ECDSA Signature Edge Cases
=========================================
eth_sendRawTransaction signatures (v, r, s) have a well-defined valid range
(secp256k1 curve order n, EIP-2 low-s malleability rule, EIP-155 v encoding),
but a translation layer might parse them with a generic big-int library that
doesn't enforce those bounds before handing them to the backend's signer /
verifier. This scenario sends structurally-valid-looking but boundary/edge
values for v, r, s and checks whether the relay validates, rejects
gracefully, or throws an unhandled exception (crash, 500, stack trace leak).

Note: these are not necessarily *cryptographically* valid signatures for any
real message/key (that would require a matching private key) - the point is
to see how the relay's parsing/validation layer reacts to the byte patterns
before/if it ever reaches real signature recovery.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import client

SCENARIO = "s06_ecdsa_signature_edge_cases"

# secp256k1 order n
N = "fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141"
N_MINUS_1 = "fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364140"
HALF_N_PLUS_1 = "7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a1"  # > n/2, malleable high-s

RAW_TX_PREFIX = "0xf86c8085"  # arbitrary legacy-tx-shaped prefix, not a full valid RLP tx


def _tx(v, r, s):
    return {
        "jsonrpc": "2.0",
        "method": "eth_sendRawTransaction",
        "params": [RAW_TX_PREFIX + "0" * 40],  # placeholder body; real assessment
        "id": f"v={v}",
    }


def _send_raw_tx_object_form(v, r, s, case_id):
    # Some relays accept a structured object instead of/alongside raw RLP hex;
    # send both shapes since we don't know which one this translation layer expects.
    return {
        "jsonrpc": "2.0",
        "method": "eth_sendRawTransaction",
        "params": [{"v": v, "r": r, "s": s, "to": "0x000000000000000000000000000000000000dE"}],
        "id": case_id,
    }


CASES = [
    ("v_zero", "0x0", "0x" + N_MINUS_1, "0x" + N_MINUS_1),
    ("v_one", "0x1", "0x" + N_MINUS_1, "0x" + N_MINUS_1),
    ("v_legacy_27", "0x1b", "0x" + N_MINUS_1, "0x1"),
    ("v_legacy_28", "0x1c", "0x" + N_MINUS_1, "0x1"),
    ("v_eip155_huge_chainid", "0x100000000", "0x1", "0x1"),
    ("r_equals_curve_order_n_invalid", "0x1b", "0x" + N, "0x1"),
    ("r_zero_invalid", "0x1b", "0x0", "0x1"),
    ("s_zero_invalid", "0x1b", "0x1", "0x0"),
    ("s_high_malleable", "0x1b", "0x1", "0x" + HALF_N_PLUS_1),
    ("s_equals_curve_order_n_invalid", "0x1b", "0x1", "0x" + N),
    ("r_and_s_both_max_u256", "0x1b", "0x" + "f" * 64, "0x" + "f" * 64),
    ("v_negative_style", "-0x1", "0x1", "0x1"),
    ("v_non_hex_garbage", "not_a_number", "0x1", "0x1"),
]


def run():
    results = []
    for case_name, v, r, s in CASES:
        payload = _send_raw_tx_object_form(v, r, s, case_name)
        results.append(client.send(SCENARIO, case_name, payload))
    return results


if __name__ == "__main__":
    for r in run():
        print(r["case"], "->", r["result"].get("status_code"), r["result"].get("anomaly_reasons"))
