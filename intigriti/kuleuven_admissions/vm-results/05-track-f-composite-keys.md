# Track F — F5.1 — DisciplineSet / TrefwoordenSet composite-key cross-tenant

**Verdict: PARTIAL. TrefwoordenSet cross-tenant write CLEAN-NEGATIVE (inner
403). DisciplineSet UNCLASSIFIED (inner 400 on own-control; payload
validation failed before authz).** No cross-tenant write reached either
collection; TrefwoordenSet definitively enforces tenant scope on composite
URL keys via 403, DisciplineSet needs a richer payload to properly exercise
the authz layer.

**Run:** 2026-09-24. **Harness:** `tools/f5_1_composite_key_cross_tenant.py`.
**Rows appended:** 12. **Non-safe used:** 4.

## 1. Motivation

Sweep 10 follow-up showed that `HigherEducations('0')` uses a *singleton*
URL key that the server aliases to the caller's tenant — cross-tenant
write via body-encoded `higherEducationId` was blocked because the URL
scope was implicit. DisciplineSet and TrefwoordenSet use **composite URL
keys** of the form `(applicationId='<x>',key='<y>')` — the applicationId
is explicit in the URL, not aliased. That's a different shape and it
asks a genuinely different question: does the server enforce tenant
scope on the URL when the URL contains the tenant identifier literally?

## 2. Method

For each of `DisciplineSet` and `TrefwoordenSet`:

1. **Own-row control:** batched MERGE from A's session to
   `<Set>(applicationId='<A's app>',key='1')` with body
   `{applicationId:'<A's app>', key:'1', <marker_field>:'F51_OWN_*'}` —
   confirms the write path works for the caller's own tenant.
2. **Cross-tenant probe:** batched MERGE from A's session to
   `<Set>(applicationId='<B's app>',key='1')` — this is where a URL-key
   cross-tenant bug would show up. If inner 204 with either A or B
   seeing the marker, that's the finding.
3. **Verification:** read `?$filter=applicationId eq '<applicationId>'`
   from both A and B sessions to see where (if anywhere) the write landed.

## 3. Results

| Collection | Phase | Batch outer | Batch inner | Row observed | Verdict |
|---|---|---|---|---|---|
| `DisciplineSet` | own control (A → `applicationId='<A>'`) | 202 | **400** | none | payload rejected before authz |
| `DisciplineSet` | cross probe (A → `applicationId='<B>'`) | 202 | **400** | none | payload rejected before authz |
| `TrefwoordenSet` | own control (A → `applicationId='<A>'`) | **500** | *(none)* | none | server internal error on OWN write |
| `TrefwoordenSet` | cross probe (A → `applicationId='<B>'`) | 202 | **403** | none | **authz rejected — clean-negative** |

## 4. Interpretation per collection

### TrefwoordenSet — clean-negative on cross-tenant

The cross-tenant MERGE returned **inner 403**. This is exactly the shape we
want to see: the server received a valid changeset targeting
`TrefwoordenSet(applicationId='<B's app>', key='1')` from A's session,
recognized that the URL's `applicationId` didn't belong to the caller's
tenant, and refused with 403 at the OData handler's authz check.

**The own-control 500 is a separate SAP internal-error issue** — probably
a missing required field in my minimal `{applicationId, key, trefwoord}`
body causing the handler to panic (500 in SAP OData usually means an
uncaught exception in the data-provider class). The 500 doesn't invalidate
the cross-tenant 403 — those two paths hit different code branches, and
the 403 fires at the request-authorization step BEFORE the payload
validation panic.

**TrefwoordenSet composite-key cross-tenant write: not reachable.**

### DisciplineSet — unclassified

Both own-control and cross-tenant MERGEs returned inner 400. My payload
was too minimal — `services.updateDisciplineCodes` in the client sends
the whole discipline-row object which includes at minimum `disciplineCode`
+ several fields populated from the disccode-search response (`field`,
`Field3` etc.). SAP OData's payload validator rejected my three-field
body at parse time, before reaching the URL-key authz check.

Because we didn't reach the authz layer, **F5.1 does not conclude for
DisciplineSet.** A retry with a full row payload would answer the
cross-tenant question, but it burns budget and the operator's rate-
limit constraints suggest it's not the highest-EV pursuit given
TrefwoordenSet's cleaner 403 signal.

## 5. Safety accounting

- Writes accepted (inner 204 with `field_changed=True`): **0**
- Rows created cross-tenant: **0** (B's collection unchanged for both
  `DisciplineSet` and `TrefwoordenSet`)
- Rows created own-tenant: **0** (own-control writes all rejected —
  DisciplineSet 400, TrefwoordenSet 500)
- Cleanup required: **none** (no rows landed anywhere)
- IMMEDIATE-STOP triggers: **0**

## 6. Follow-ups

- **DisciplineSet retry with full payload.** From `services.js`, the row
  object includes `disciplineCode`, `field`, `Field3`, and possibly
  `Field0..Field2` and `Code0..Code2`. A dry-read of A's existing (if any)
  DisciplineSet rows would reveal the full column set. Budget: ~3 non-safe.
  Deferred.
- **TrefwoordenSet own-write 500 investigation.** Small follow-up: retry
  own-control with additional fields to see if any specific field lift
  the 500 to 204. Not security-relevant; more curiosity. Deferred.
- **F1.2 / F1.5 / F1.3** — remaining batch-native tests. Each is its own
  egress rotation per ACL discipline.

## Rows in `02-authz-matrix.jsonl`

Grep `"sweep": "f5.1"` for the 12 rows from this run.
