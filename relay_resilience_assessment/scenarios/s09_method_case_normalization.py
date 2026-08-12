"""
Scenario 9: RPC Method Case Normalization
=============================================
JSON-RPC method names are case-sensitive by spec, but a permissive relay
might lowercase (or uppercase) the method before matching it against its
routing table, while the non-EVM backend it forwards to might do its own
*different* normalization (or none at all). We send the same logical method
in several capitalizations and diff the responses - if any variant returns a
different result, error, or is routed to a different handler than the
canonical name, that's a routing/normalization inconsistency worth flagging.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import client
from harness.logger import ResultLogger

SCENARIO = "s09_method_case_normalization"

METHOD_VARIANTS = {
    "eth_chainId": [
        "eth_chainId",
        "ETH_chainId",
        "eth_CHAINID",
        "ETH_CHAINID",
        "Eth_ChainId",
        "eth_chainid",
    ],
    "eth_blockNumber": [
        "eth_blockNumber",
        "ETH_BLOCKNUMBER",
        "eth_blocknumber",
        "Eth_BlockNumber",
    ],
}


def run():
    results = []
    logger = ResultLogger()

    for canonical, variants in METHOD_VARIANTS.items():
        for variant in variants:
            payload = {"jsonrpc": "2.0", "method": variant, "params": [], "id": variant}
            record = client.send(SCENARIO, f"{canonical}__as__{variant}", payload)
            results.append(record)

    # Cross-check: flag any variant whose HTTP status differs from the
    # canonical-cased call for the same logical method - that's the clearest
    # signal of a routing/normalization inconsistency (e.g. canonical
    # succeeds but an alternate capitalization 404s/400s, or vice versa).
    # This is logged as its own derived record (rather than mutating the
    # already-persisted per-request records above) so the anomaly log
    # always reflects exactly what was written at request time.
    for canonical, variants in METHOD_VARIANTS.items():
        canonical_status = next(
            (r["result"].get("status_code") for r in results if r["case"] == f"{canonical}__as__{canonical}"),
            None,
        )
        for r in results:
            if not r["case"].startswith(f"{canonical}__as__") or r["case"] == f"{canonical}__as__{canonical}":
                continue
            variant_status = r["result"].get("status_code")
            if canonical_status is not None and variant_status != canonical_status:
                diff_result = {
                    "status_code": variant_status,
                    "is_anomaly": True,
                    "anomaly_reasons": [
                        f"case_variant_status_{variant_status}_differs_from_canonical_{canonical_status}"
                    ],
                    "canonical_method": canonical,
                    "variant_case": r["case"],
                }
                results.append(
                    logger.record(SCENARIO, f"DIFFERENTIAL__{r['case']}", payload=r["case"], result=diff_result)
                )

    return results


if __name__ == "__main__":
    for r in run():
        print(r["case"], "->", r["result"].get("status_code"), r["result"].get("body_preview"))
