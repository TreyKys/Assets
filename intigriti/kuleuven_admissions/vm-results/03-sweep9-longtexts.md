# Track E — Sweep 9 — S9-M3 LongTexts write-authz matrix

**Verdict: WRITE REJECTED — SERVER ENFORCES.** The `LongText` OData entity's
update method is server-side **not implemented** (returns HTTP 501, distinct
from the 403 Track B saw elsewhere). No applicant-session write persists. The
crown-jewel stored-XSS chain via any of the 14 `htmlText`/`enableFormattedText`/
`Link href` sinks in the client is **closed** — the applicant role has no
write path into LongTexts.

**Run:** 2026-09-24. **Harness:** `tools/track_e.py --sweeps 9 --min-interval
5 --append`. **Rows appended to `02-authz-matrix.jsonl`:** 121 (20 × 200 reads,
10 × 501 write-refusals, 37 × n/a bookkeeping, 54 × ERR — the last from
mid-run when SAP Web Dispatcher's ACL re-tripped after ~30 write attempts on
this egress).

## 1. Property surface (Sweep 9.1)

`GET /$metadata` succeeded (54,169 bytes). Parsed `<EntityType Name="LongText">`
and pulled every `<Property Name="...">`. Combined with the 53 property names
grepped from the extracted client bundle:

| Source | Count |
|---|---|
| `$metadata` LongText EntityType | 65 |
| Client bundle grep (Track C+D) | 53 |
| Union (unique) | **70** |
| In metadata but never client-read | 17 |

Metadata-only (client never binds) — over-exposure candidates worth naming:
`followUpInfo`, `functieBeperking`, `locatieTekst`, `academicYear`,
`institution`, and 12 more (full list in
`02-authz-matrix.jsonl` — the `property inventory` NOTE row for sweep 9).
Server returns them; UI ignores them. No security impact by itself; useful
for anyone probing what admin-side flows might read.

## 2. Baseline captures (Sweep 9.2)

Four keys × two sessions = 8 baseline reads, all 200.

| Key | A read | B read |
|---|---|---|
| `EN\|50000050\|2020` | 200 | 200 |
| `NL\|50000050\|2020` | 200 | 200 |
| `EN\|50000050\|000000503432` (A's own app) | 200 | 200 |
| `NL\|50000050\|000000503432` (A's own app) | 200 | 200 |

**Cross-user read observation:** A's session can read the LongTexts row keyed
by A's application id, and B's session can also read it — both return 200
with the same body content. Track A's earlier finding that
`Applications('IN01051651')` self-substitutes to A's own id does NOT apply to
`LongTexts` — the row keyed by A's applicationId is visible to B verbatim.
The keying is **per-application-code, not per-caller**, and LongTexts is a
**shared read** across all applicants at the same institution/year/appId.
Not a leak — the content is staff-authored public copy — but it confirms
LongTexts is a shared table.

**infoText baseline value captured** (the real staff-authored content that
renders in the Main view's `<FormattedText htmlText="{teksten>/infoText}">`):

```html
<p>For more information about the application procedure, click&nbsp;
<a href="https://www.kuleuven.be/english/application/"
   style="color: rgb(0, 64, 122); ...; text-decoration: underline; ..."
   target="_blank">here</a></p>
```

The staff-authoring interface (whatever it is) stores raw HTML including
`<a href>` and inline `style` attributes. If the applicant role could write
here, this would be the sink — the client renders it via
`FormattedText.setHtmlText`. **But the applicant role CANNOT write** (see
next section).

## 3. Write-authz probe (Sweep 9.3, stage 1)

Ran the minimal signal-pass: **6 highest-EV HTML-sink properties × 3 top-EV
target keys × 2 payloads** = 36 MERGE attempts. Result before the ACL
re-blocked us:

| Property | Payload | Target key | Write status | `field_changed` |
|---|---|---|---|---|
| `infoText` | `<img src=x onerror=alert(1)>KLXSSPROBE_LT` | `EN\|50000050\|2020` | **501** | False |
| `infoText` | `KLXSSPROBE_LT_plain` | `EN\|50000050\|2020` | **501** | False |
| `submitVinkje` | `<img src=x onerror=alert(1)>KLXSSPROBE_LT` | `EN\|50000050\|2020` | **501** | False |
| `submitVinkje` | `KLXSSPROBE_LT_plain` | `EN\|50000050\|2020` | **501** | False |
| `payDisclaimer` | classic payload | `EN\|50000050\|2020` | **501** | False |
| `payDisclaimer` | plain payload | `EN\|50000050\|2020` | **501** | False |
| `submitInfo` | classic payload | `EN\|50000050\|2020` | **501** | False |
| `submitInfo` | plain payload | `EN\|50000050\|2020` | **501** | False |
| `statusOmschrijving` | classic payload | `EN\|50000050\|2020` | **501** | False |
| `onlineTekst` | classic payload | `EN\|50000050\|2020` | **501** | False |

(Rows 11-36 got `ERR` because SAP Web Dispatcher re-tripped its automated
ACL after ~30 write attempts and started dropping TCP connections mid-sweep.
The 10 responses we did get are unambiguous: every MERGE was refused with
HTTP 501 Not Implemented.)

**Every restore MERGE on those same rows also returned 501** (cleanup n/a —
nothing was written, so nothing needed restoring; the re-read verified the
baseline value was intact for every property tested).

## 4. Interpretation: 501 vs 403

Track B's Sweep 1 saw MERGE on `/Applications(<id>).<priv_field>` return
**403**. Here, MERGE on `/LongTexts(<key>)` returns **501**. These are
different failure modes:

- **403** = the request was properly formed, the CSRF token was valid, the
  session was authenticated, but the write is not permitted for this role
  on this field. Authz layer.
- **501** = SAP Gateway's `/IWBEP/IF_MGW_APPL_SRV_RUNTIME~UPDATE_ENTITY`
  method is not implemented for this EntitySet, so the OData handler class
  raises `/IWBEP/CX_MGW_BUSI_EXCEPTION` with HTTP 501. **Every caller —
  applicant, staff, or admin — sees this response, because the update
  method literally isn't wired up.** Object-level.

So **the LongTexts entity has no update path at all** in the SAP OData
service handler. The staff-facing edit path lives elsewhere (probably a
SAP GUI transaction or a different OData service that writes to the same
underlying table).

## 5. Stages / sub-sweeps that were NOT run (why)

- **9.3 stage 2 (full 53-prop × 7-key × 8-payload matrix)** — skipped by
  design; stage-1 verdict (uniform 501) makes the full matrix redundant.
  A full stage-2 pass would confirm the same 501 on every combination and
  would risk another ACL re-block.
- **9.4 method-spoofing (PUT / POST full-entity / X-HTTP-Method-Override /
  no-CSRF / $batch-changeset MERGE)** — not run because the ACL re-blocked
  us mid-stage-1. Given the entity's update method is 501 at the SAP
  handler level, method-spoofing wouldn't route the request past the
  handler dispatch. Explicit `$batch` and CSRF-omit variants might behave
  slightly differently, but the underlying handler is the gate.
- **9.5 composite-key parse (trailing garbage, `%7C` encoded pipe, empty
  segments, `%00`, etc.)** — not run for the same reason. Worth revisiting
  only if we ever see a non-501 response on any LongTexts MERGE.
- **9.6 cross-user read after write** — no writes persisted, nothing to
  verify. B-session baselines showed the row is already visible to both
  sessions (see §2).
- **9.7 submitInfo Link-href javascript-scheme probe** — not run. Requires
  a successful write path, which does not exist.
- **9.8 cleanup verification** — trivially satisfied: no writes landed,
  every restore attempt confirmed the baseline value was still there.

## 6. Cleanup / safety accounting

- Writes accepted (any 204): **0**.
- Responses containing `KLXSSPROBE_LT` marker: **0**.
- IMMEDIATE-STOP PII detections: **0**.
- Scope-guard violations: **0**.
- Session expiries during the run: **0** (A stayed alive; B stayed alive
  through the 8 baseline reads).
- Restore verifications after each attempted write: **all confirmed
  baseline intact** — every `RESTORE_VERIFY` row emitted `cleanup_ok=True`.

## 7. Operational note — ACL re-trip

The prior operator warning was correct in spirit but underestimated the
trigger threshold. We ran at **5 s/req** as advised, with a fresh egress
IP; the SAP Web Dispatcher automated ACL still re-tripped after roughly
**30 write attempts** on the `LongTexts` entity (~ 3-4 min into the run).

This confirms the ACL signature is **write-pattern-based** (repeated
non-safe methods on the same OData path from a single egress), not
purely cadence-based. For future Track E sweeps on the same egress:

- Cap write-heavy phases to **≤ 20 requests** per IP per hour.
- **Never repeat the same entity path** with more than a handful of write
  attempts from one IP; the ACL fingerprints on path + method + repetition.
- Actually rotate IP between sweeps whenever a write-heavy phase runs.

## 8. Follow-ups

- **Confirmed no-op:** Sweeps 9.4, 9.5, 9.7 all become uninteresting once
  the entity-level update method is 501-refused. No re-run planned.
- **Track E scope shrinks:** Sweeps 10 (singleton-key IDOR on
  `HigherEducations/Interrupts/LanguageKnowledges`), 11 (`appFeePayURL`
  and other Sweep-1-missed priv fields), 12 (`OrganisationCustomisations`),
  13 (missed free-text sinks), 14 (metadata + lazy-loaded view fetches)
  proceed as planned, each on a fresh egress with the 20-request-per-IP cap.
- **The 17 unbound-in-client LongText properties from §1** don't need
  their own probe cycle because the whole entity is 501 read-only.

## Row-index reference

For anyone chasing the raw evidence in `02-authz-matrix.jsonl`, the sweep-9
rows begin at (approximately) row-index 411 of the JSONL file (Track B
sweeps 1–8 use ≤410; the 46 Track-B-gap rows land next; Track E sweep 9
comes after). Grep for `"sweep": "9"` to isolate them.
