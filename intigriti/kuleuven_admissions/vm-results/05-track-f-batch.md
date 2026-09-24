# Track F — F1.* — the `$batch` frontier

## F1.1 — Batch-path re-test of Sweep 1 privileged fields

**Verdict: CLEAN NEGATIVE (validly tested this time) — batch dispatch enforces
the same field-level authorization on `Applications` that the direct path
does.** No self-admission, no fee-bypass, no decision-tampering, no
admission-letter-forgery flag, no case-admin reassignment reachable via the
batch path.

**Distinct behavioural finding worth documenting:** the batch path returns
**inner 204 "No Content"** for the same privileged-field MERGEs that the
direct path correctly returns 403 for. The write authorization filter is
identical, but the batch handler **silently drops** the privileged field's
value while still signalling "success" to the caller. This is
inconsistent-error-signaling — a defensive design gotcha but not a security
hole in itself.

**Run:** 2026-09-24. **Harness:** `tools/f1_1_batch_privfields.py`
(uses patched `_batch_body` from commit `dfb7693`). **Rows appended:** 17.
**Non-safe requests used:** 5 (batched MERGE per field; no restore branch
needed — nothing persisted).

### Method

For each of the 5 privileged fields Sweep 1 direct-tested and saw uniform
403 on, issued the identical MERGE **inside a single-op changeset**:

```
POST /sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/$batch?sap-client=200
Content-Type: multipart/mixed; boundary=batch_klxb
x-csrf-token: <valid>

--batch_klxb
Content-Type: multipart/mixed; boundary=changeset_klxc

--changeset_klxc
Content-Type: application/http
Content-Transfer-Encoding: binary
Content-ID: 1

MERGE Applications('000000503432')?sap-client=200 HTTP/1.1
Content-Type: application/json
Content-Length: <N>

{"<field>": <value>}

--changeset_klxc--

--batch_klxb--
```

Followed by a **direct** GET on `Applications('000000503432')` to observe
whether the field's value actually changed.

### Results

| # | Field | Direct-path result (Sweep 1) | Batch outer | Batch inner | Baseline value | Value after | `field_changed` |
|---|---|---|---|---|---|---|---|
| 1 | `statusCode` = `"211"` | 403 | 202 | **204** | `'000'` | `'000'` | **False** |
| 2 | `isAppFeePayed` = `true` | 403 | 202 | **204** | `False` | `False` | **False** |
| 3 | `isPropositionAccepted` = `true` | 403 | 202 | **204** | `False` | `False` | **False** |
| 4 | `followUpAdmLetter` = `"1"` | 403 | 202 | **400** | `None` | `None` | False |
| 5 | `caseAdmin` = `"HACKER"` | 403 | 202 | **204** | `''` | `''` | **False** |

### Interpretation

**All five fields are actually rejected.** No write persisted. The
crown-jewel batch-path bypass hypothesis — that Track E's HigherEducations
finding (501 direct → 204 batched, write landing) would generalize to
Applications' authz-guarded fields — **is false for these fields**. The
SAP OData handler class for `Applications` correctly filters privileged
fields on both paths.

**Response-code divergence (documented, not a bypass):**

- **Direct path**: the OData `UPDATE_ENTITY` runtime method receives the
  MERGE, sees a filtered privileged field in the body, and rejects the
  entire request with **403 Forbidden + explicit error message**. The
  client learns the write failed.
- **Batch path**: the changeset dispatch receives the same MERGE, applies
  the same field filter, but instead of failing the operation, it emits
  **204 No Content** — the OData "write succeeded, nothing to return"
  code. The privileged field is silently dropped. The client sees 204 and
  believes the write took effect until (and unless) it re-reads.

For applications where multiple fields are MERGEd at once, this becomes a
partial-write hazard: the server accepts the batch (204), silently drops
only the privileged fields, and applies the rest. The client's model gets
out of sync with server state. This is an **application-integrity concern**
(client trust of 204), not a security bypass.

The one exception, `followUpAdmLetter`, returned inner **400** — likely a
type-coercion mismatch (the field probably expects a specific enum/int
type, and `"1"` as a string didn't parse in the batch validator). Direct
path returned 403 uniformly for the same value because the direct handler
runs authz FIRST and rejects before the type coercion step; the batch
handler runs type coercion FIRST and rejects before authz. Different order,
same net effect (no write persisted).

### Safety accounting

- Writes accepted (inner 204 + `field_changed=True`): **0**
- Restores needed: **0** (nothing persisted)
- IMMEDIATE-STOP triggers: **0**
- Session expiry: none
- ACL re-trip during F1.1: none observed at end-of-run (13 total requests
  including 5 non-safe, at 8 s/req)

### Follow-up

- F1.2 (changeset atomicity: known-legal + known-forbidden ops in the same
  changeset) — worth running on a fresh egress. If a `HigherEducations`
  MERGE and an `Applications.statusCode` MERGE are in the same changeset,
  does the illegal op ride the transaction? Track E's HigherEducations
  probe would supply the "known-legal" op.
- F1.4 (LongTexts batch MERGE) — separate egress per brief. The response-
  code-divergence finding in F1.1 raises the question: might batched
  LongTexts also return 204 with silent-drop? Or actually persist? Track F
  brief says: don't combine with F1.1.
- The 400 on `followUpAdmLetter` invites a type-probe: try `1` (int),
  `true` (bool), `"01"` (padded string) — one more round on a fresh
  egress could nail down the correct type and re-test authz on the type
  that parses.

## F1.2, F1.3, F1.4, F1.5

Deferred to future egresses per ACL discipline. Each block below is one
rotation ≤ 12 non-safe requests, per Track F brief.

- **F1.2 (changeset atomicity abuse)** — HigherEducations legal + Applications
  forbidden in same changeset. Runs after next IP rotation.
- **F1.3 (batch-wrap Sweep-2 reads)** — GET-only, safe to combine with a
  read-heavy phase like F3.1 or F4.1.
- **F1.4 (LongTexts batched MERGE)** — separate egress from all other
  write-heavy phases.
- **F1.5 (Content-ID `$1` reference smuggling)** — batch-native
  cross-tenant test; deferred.

## Rows in `02-authz-matrix.jsonl`

Grep `"sweep": "f1.1"` for the 17 rows from this run.
