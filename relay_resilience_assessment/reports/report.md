# JSON-RPC Relay Resilience Assessment Report

- **Target:** `http://127.0.0.1:7546`
- **Generated:** 2026-08-12 23:11:48 UTC
- **Rate limit applied:** 10.0 req/s
- **Anomaly latency threshold:** 10.0s
- **Total requests logged:** 84
- **Total anomalies:** 10

## Summary

| # | Scenario | Cases | Anomalies |
|---|----------|-------|-----------|
| 1 | Duplicate JSON Keys and Parser Inconsistency | 7 | 0 |
| 2 | Gas Estimation Resource Exhaustion | 8 | 0 |
| 3 | Hex and Integer Boundary Handling | 13 | 0 |
| 4 | State Cache Consistency After Reverts | 4 | 0 |
| 5 | Object Property Name Pollution | 6 | 0 |
| 6 | ECDSA Signature Edge Cases | 13 | 0 |
| 7 | Null Byte and Unicode Input Handling | 10 | 0 |
| 8 | Deeply Nested Arrays | 5 | 2 ⚠️ |
| 9 | RPC Method Case Normalization | 18 | 8 ⚠️ |
| 10 | Slow HTTP Body Transmission | 0 | 0 |

## Findings by Scenario

### Duplicate JSON Keys and Parser Inconsistency (`s01_duplicate_keys`)

No anomalies across 7 case(s). All responses used standard JSON-RPC error codes / expected latency.

### Gas Estimation Resource Exhaustion (`s02_gas_estimation_exhaustion`)

No anomalies across 8 case(s). All responses used standard JSON-RPC error codes / expected latency.

### Hex and Integer Boundary Handling (`s03_hex_integer_boundaries`)

No anomalies across 13 case(s). All responses used standard JSON-RPC error codes / expected latency.

### State Cache Consistency After Reverts (`s04_state_cache_consistency`)

No anomalies across 4 case(s). All responses used standard JSON-RPC error codes / expected latency.

### Object Property Name Pollution (`s05_prototype_pollution`)

No anomalies across 6 case(s). All responses used standard JSON-RPC error codes / expected latency.

### ECDSA Signature Edge Cases (`s06_ecdsa_signature_edge_cases`)

No anomalies across 13 case(s). All responses used standard JSON-RPC error codes / expected latency.

### Null Byte and Unicode Input Handling (`s07_null_byte_unicode`)

No anomalies across 10 case(s). All responses used standard JSON-RPC error codes / expected latency.

### Deeply Nested Arrays (`s08_deeply_nested_arrays`)

**2 anomaly(ies) out of 5 case(s):**

- **Case:** `depth_5000`
  - Reasons: `http_500`
  - HTTP status: `500` | elapsed: `0.017s`
  - Payload:
    ```json
    {"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0x000000000000000000000000000000000000dE","data":"0x00","aux":[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[... [truncated, 10140 chars total]
    ```
- **Case:** `depth_20000`
  - Reasons: `http_500`
  - HTTP status: `500` | elapsed: `0.029s`
  - Payload:
    ```json
    {'truncated': True, 'original_length': 40141, 'preview': '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0x000000000000000000000000000000000000dE","data":"0x00","aux":[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[... [truncated, 2060 chars total]
    ```

### RPC Method Case Normalization (`s09_method_case_normalization`)

**8 anomaly(ies) out of 18 case(s):**

- **Case:** `DIFFERENTIAL__eth_chainId__as__ETH_chainId`
  - Reasons: `case_variant_status_400_differs_from_canonical_200`
  - HTTP status: `400` | elapsed: `n/a`
  - Payload:
    ```json
    eth_chainId__as__ETH_chainId
    ```
- **Case:** `DIFFERENTIAL__eth_chainId__as__eth_CHAINID`
  - Reasons: `case_variant_status_400_differs_from_canonical_200`
  - HTTP status: `400` | elapsed: `n/a`
  - Payload:
    ```json
    eth_chainId__as__eth_CHAINID
    ```
- **Case:** `DIFFERENTIAL__eth_chainId__as__ETH_CHAINID`
  - Reasons: `case_variant_status_400_differs_from_canonical_200`
  - HTTP status: `400` | elapsed: `n/a`
  - Payload:
    ```json
    eth_chainId__as__ETH_CHAINID
    ```
- **Case:** `DIFFERENTIAL__eth_chainId__as__Eth_ChainId`
  - Reasons: `case_variant_status_400_differs_from_canonical_200`
  - HTTP status: `400` | elapsed: `n/a`
  - Payload:
    ```json
    eth_chainId__as__Eth_ChainId
    ```
- **Case:** `DIFFERENTIAL__eth_chainId__as__eth_chainid`
  - Reasons: `case_variant_status_400_differs_from_canonical_200`
  - HTTP status: `400` | elapsed: `n/a`
  - Payload:
    ```json
    eth_chainId__as__eth_chainid
    ```
- **Case:** `DIFFERENTIAL__eth_blockNumber__as__ETH_BLOCKNUMBER`
  - Reasons: `case_variant_status_400_differs_from_canonical_200`
  - HTTP status: `400` | elapsed: `n/a`
  - Payload:
    ```json
    eth_blockNumber__as__ETH_BLOCKNUMBER
    ```
- **Case:** `DIFFERENTIAL__eth_blockNumber__as__eth_blocknumber`
  - Reasons: `case_variant_status_400_differs_from_canonical_200`
  - HTTP status: `400` | elapsed: `n/a`
  - Payload:
    ```json
    eth_blockNumber__as__eth_blocknumber
    ```
- **Case:** `DIFFERENTIAL__eth_blockNumber__as__Eth_BlockNumber`
  - Reasons: `case_variant_status_400_differs_from_canonical_200`
  - HTTP status: `400` | elapsed: `n/a`
  - Payload:
    ```json
    eth_blockNumber__as__Eth_BlockNumber
    ```

### Slow HTTP Body Transmission (`s10_slow_body_transmission`)

_Not run._

## Notes

- "Anomaly" = HTTP >= 500, dropped/reset connection, response time over 10.0s, or a non-JSON body where JSON was expected. A 4xx JSON-RPC error response (e.g. `-32600 Invalid Request`) is normal, expected behavior and is *not* flagged.
- Scenario 4 (state cache consistency) and Scenario 6 (ECDSA edge cases) produce structurally representative payloads but a fully conclusive verdict requires pairing them with your actual deployed test contract / a real signer, since this harness has no private key material or contract bytecode of its own.
- Re-run individual scenario scripts directly (`python scenarios/sNN_*.py`) to iterate on a single finding without re-running the whole suite.
