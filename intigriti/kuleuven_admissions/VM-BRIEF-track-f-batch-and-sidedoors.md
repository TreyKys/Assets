# VM BRIEF — KU Leuven Admissions — Track F: the $batch frontier + the side doors

**Why this brief exists.** Two facts reframe everything we thought we knew:

1. **The `$batch` helper was malformed the entire campaign.** Every prior `$batch`
   request (Track B Sweep 2, Sweep 9.4, the Track-B-gap changeset tests) was rejected by SAP
   Gateway's parser *before the inner request dispatched*. Those "no bypass" verdicts are
   **null results, not negative results.** The fix (commit `dfb7693`) is now proven to work.
2. **Batch dispatch routes to a DIFFERENT implementation than direct requests.** Standalone
   `MERGE /HigherEducations('0')` returns **501 Not Implemented**; the *same MERGE inside a
   corrected `$batch` changeset returns 204*. The SAP data-provider class wires up
   `*_UPDATE_ENTITY` differently for the batch-changeset dispatch path than for the direct
   `UPDATE_ENTITY` runtime path.

Put those together: **the direct-request authz results we have (Sweep 1's uniform 403 on
Applications privileged fields; Sweep 9's 501 on LongTexts) characterize only the direct path.
The batch dispatch path is a separate code path with separately-implemented handlers, and it has
never been validly tested.** The entire crown-jewel surface of this program — self-admission
(`statusCode`), fee-bypass (`isAppFeePayed`), decision-tampering (`isPropositionAccepted`,
`followUpAdmLetter`) — was declared safe on the direct path alone. Track F re-tests it on the
path we now know behaves differently, and folds in four other side-door surfaces the front-door
authz rigor may not cover.

**Everything here is in-scope authorization testing on your own accounts A/B.** No credential
forgery, no IdP, no `esap/public/*`, no infrastructure attacks. The question throughout is the
legitimate one: *does the server enforce the same authorization on every path that reaches a
given action, or only on the path the developers expected to be attacked?*

## Scope + guardrails (unchanged from Track B/E)

- ONLY `https://webwsp.aps.kuleuven.be/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/*`
- ONLY accounts A (`IN01051619` / `000000503432`) and B (`IN01051651` / `000000503434`).
- Target-ID guard ON. IMMEDIATE-STOP on foreign PII. Session-death detection ON.
- **ACL discipline is now hard-won knowledge:** the SAP Web Dispatcher ACL fingerprints on
  path+method+repetition and re-trips at **~15 non-safe requests per egress**, tighter each
  round. Every write-heavy phase below is capped and tagged with its request budget. Rotate
  egress between phases; never exceed ~12 non-safe requests on one IP.
- Baseline-restore in `finally:` for every write. Cleanup verification mandatory.

## Immediate housekeeping (do first, zero network)

- **Phantom row on A:** the Sweep-10 discriminator left `HigherEducations` row
  `higherEducationId='000999'` (fields blanked, but row persists; OData DELETE is 501). This
  needs **manual UI deletion** by the researcher — flag it in the run log as an open cleanup
  item, do not attempt further OData DELETEs on it.

---

## SURFACE 1 — the `$batch` dispatch path (HIGHEST PRIORITY)

The centerpiece. Now that the batch helper emits valid multipart, re-test everything the direct
path declared safe, plus batch-native attacks that were never possible before.

### F1.1 — Re-test Sweep 1's privileged-field MERGEs through the batch path (THE crown jewel)

For each privileged field on OWN `Applications('000000503432')` that Sweep 1 saw 403 on the
direct path, issue the identical MERGE **inside a single-op changeset** with the corrected batch
format, from A's session:

- `statusCode` = `"211"`, `"210"`, `"216"` (self-admission / decision advance)
- `isAppFeePayed` = `true` (fee bypass)
- `isPropositionAccepted` = `true` (decision tampering)
- `followUpAdmLetter` = `"1"` (admission-letter forgery flag)
- `caseAdmin` = `"HACKER"` (assign own case officer)

For each: capture the INNER status (not the outer 202). Re-read `Applications('000000503432')`
directly and log `field_changed`.

**Interpretation:**
- Inner 403 → the batch path enforces the same field-authz as direct. Genuine clean-negative
  (this time with a valid batch). Report as such.
- Inner 204 + `field_changed=True` → **the batch dispatch path bypasses field-level
  authorization that the direct path enforces. This is the finding of the entire engagement.**
  STOP immediately, capture the full request/response, restore the baseline, and write it up
  before touching anything else. A self-admission or fee-bypass via batch is Critical.

Budget: ~10 non-safe (5 fields × MERGE + re-read GETs). Restore each in `finally:`.
**Run this phase FIRST, alone, on a fresh egress.** If it lands, nothing else matters tonight.

### F1.2 — Changeset atomicity abuse (batch-native, never testable before)

SAP `$batch` changesets are transactional. Test whether authz is evaluated per-operation or
per-changeset by putting a **known-authorized op and a known-forbidden op in the same
changeset**:

- Changeset op 1 (Content-ID 1): `MERGE HigherEducations('0')` body `{higherEducationId:<A's
  own row>, nameSchool:"KLTEST_F12_LEGAL"}` — the op we proved returns 204.
- Changeset op 2 (Content-ID 2): `MERGE Applications('000000503432')` body
  `{statusCode:"211"}` — the op that 403s alone.

Two outcomes worth distinguishing:
- Whole changeset rolls back (both ops fail) → transactional integrity, authz per-op. Safe.
- Op 1 commits AND op 2 commits (statusCode changed) → **authz checked only on changeset entry,
  illegal op rode the transaction.** Critical.
- Op 1 commits, op 2 fails cleanly → per-op authz, correct. Safe.

Also try the reverse order (forbidden op first) — some dispatchers short-circuit differently.
Budget: ~4 non-safe + 2 re-read GETs. Restore both in `finally:`.

### F1.3 — Re-run Sweep 2 (batch-wrap the direct-403 reads) with the valid helper

The original Sweep 2 premise, now validly testable. For each endpoint Track A saw 403 on the
direct path, wrap the identical GET in a `$batch` (reads go in the batch directly, no
changeset):

- `GET Applications('000000503434')/SubmitChecks` (B's app, from A's session)
- `GET DisciplineSet?$filter=applicationId eq '000000503434'`
- `GET TrefwoordenSet?$filter=applicationId eq '000000503434'`
- `GET Applications('000000503434|0')/Attachments('1')/$value`

Inner 200 where direct was 403 → batch read-authz bypass → cross-user read. Budget: ~5 GETs
(safe/idempotent, lighter ACL weight than writes).

### F1.4 — Batch-wrapped LongTexts MERGE re-test (does the XSS chain reopen?)

Sweep 9 found `LongTexts.UPDATE_ENTITY` = 501 on the direct path and concluded the 14 htmlText
sinks are unreachable. But HigherEducations proved batch dispatch can route to a *different,
implemented* handler where direct is 501. Re-test: batched `MERGE LongTexts('EN|50000050|2020')`
body `{infoText:"<img src=x onerror=alert(1)>KLXSSPROBE_F14"}` from A's session.

- Inner 501 → same handler dispatches both paths for LongTexts; Sweep 9's verdict holds.
- Inner 204 → **the crown-jewel stored-XSS chain reopens** (write into the shared LongTexts row
  that renders across all applicants + staff). If so, immediately follow with the cross-user
  read from B, the `submitInfo` javascript-scheme probe (9.7), and mandatory cleanup. Critical.

Budget: ~3 non-safe + re-read. **Do NOT combine with F1.1 on the same egress** — two write-heavy
phases on one IP blows the ACL budget. Separate rotation.

### F1.5 — Content-ID reference resolution across tenant (batch-native)

SAP `$batch` supports referencing an entity created earlier in the changeset via `$<Content-ID>`.
Create a row in op 1, then in op 2 reference `$1` while pointing a navigation/key at B's scope.
Does reference resolution respect tenant scope, or does the `$1` alias let you smuggle a
cross-tenant target past the per-request guard? Budget: ~3 non-safe. Restore in `finally:`.

---

## SURFACE 2 — binary upload paths (front-door authz doesn't guard these)

The authz team locked entity CRUD. Binary upload is a separate code path with client-controlled
metadata. This is the same class as your Bank Van Breda FileName win, but on a live endpoint.

### F2.1 — ApplicantPhotos Content-Type reflection → stored XSS

`POST /ApplicantPhotos` (raw XHR) takes `Content-Type: <client-controlled>` and
`slug: "ZCM_ADM027|<client-controlled-filename>"`. Read-back is `GET /ApplicantPhotos('0')/$value`.

Probes (from A's session, on own photo):
1. Upload a blob whose bytes are `<svg xmlns="http://www.w3.org/2000/svg" onload="/*KLXSS_F21*/"/>`
   with `Content-Type: image/svg+xml`. GET `/ApplicantPhotos('0')/$value`. Does the response
   echo `Content-Type: image/svg+xml`? If yes, the photo renders as script in any browser
   context that loads it (including a staff photo-review screen) → stored XSS.
2. Same with `Content-Type: text/html` and an HTML body.
3. Restore the real photo (or a blank) in `finally:`.

Budget: ~4 non-safe + GETs. **Cross-user render note:** staff review applicant photos — if the
`$value` honors the stored MIME, that's a cross-user XSS surface without needing OLBUSER routing.

### F2.2 — ApplicantPhotos slug filename injection

The `slug` is `ZCM_ADM027|<filename>`. Probes:
- Filename with HTML metacharacters (`<img src=x onerror=alert(1)>.jpg`) — does it persist and
  render in any filename-display context (staff attachment list)?
- Filename with `../` traversal — does the archive store path-normalize?
- Manipulate the doc-type code before the `|` (`ZCM_ADM028|x.jpg`, `ZCM_OTHER|x.jpg`) — does the
  server accept a different archive document type than the UI ever sends? Storing under an
  unexpected doc-type could land the blob in a different review queue.

Budget: ~4 non-safe.

### F2.3 — Cross-tenant photo read

`GET /ApplicantPhotos('0')/$value` resolves `'0'` to the caller. Try `GET
/ApplicantPhotos('<B-account-id>')/$value` from A's session (parallel to the Addresses
`inAccountId` self-substitution test). Does it 403, self-substitute to A's, or leak B's photo?
Budget: ~2 GETs.

### F2.4 — ApplicationAttachments lazy-loaded flow (Sweep 14.1 folded in)

Fetch (GET, in-scope static assets):
- `/sap/bc/ui5_ui5/sap/zc_ad_appl/view/ApplicationAttachments.view.xml`
- `/sap/bc/ui5_ui5/sap/zc_ad_appl/controller/ApplicationAttachments.controller.js`

If they exist (referenced in manifest, not in preload), analyze the attachment upload flow — it
likely mirrors the ApplicantPhotos raw-XHR pattern (client filename + Content-Type) but the
attachment is shown to staff reviewers (stronger cross-user render than a photo). If reachable
and it uses the same slug/Content-Type pattern, run F2.1/F2.2 against it too. Budget: ~2 GETs +
(conditional) uploads.

---

## SURFACE 3 — the payment verifier (financial crown jewel)

`isAppFeePayed` MERGE is 403 (Sweep 1) and will be re-tested via batch in F1.1. But the *server*
sets that flag via the `isPaymentDone(admCode, paymentId)` FunctionImport after a real payment.
If that verifier can be tricked, the applicant marks their own fee paid without paying — a direct
financial bypass on their own account (legitimate self-benefit-fraud finding).

### F3.1 — isPaymentDone ownership binding

Sweep 5 fired 30 numeric `paymentId` guesses → all 400. The creative question Sweep 5 didn't
ask: **does isPaymentDone bind the paymentId to the caller's admCode, or does it check "is this
paymentId a completed payment" independent of who owns it?** Test using ONLY your own two
accounts' admCodes (do NOT enumerate real strangers' payment IDs):

- Call `isPaymentDone(admCode=<A's admCode>, paymentId=<various malformed-but-parseable>)` and
  study the *error-message differential* — does a well-formed-but-nonexistent id give a
  different error than a malformed one? Error differentials reveal the id format and the
  validation order (format check before / after ownership check).
- If A ever completes a real payment in a sandbox, call `isPaymentDone(admCode=<B's admCode>,
  paymentId=<A's real payId>)` — does B's app get marked paid off A's payment? (Only feasible
  with a real payId; note as a follow-up if none available.)

Budget: ~6 GETs (FunctionImports are GET, lighter ACL weight). No writes.

### F3.2 — appFeePayURL (Sweep 11 — check if it already ran)

Sweep 11 was queued (`appFeePayURL` + Sweep-1 gaps). **Check `02-authz-matrix.jsonl` for
`"sweep": "11"` rows first** — it may already be done. If `appFeePayURL` MERGE landed 204 on the
direct path, that's a stored open-redirect (the payment flow does `window.location.replace(
appFeePayURL)`); if it 403'd direct, re-test it via batch in F1.1's field list.

---

## SURFACE 4 — identity / context confusion (legitimate auth-logic testing)

Not credential forgery — testing whether the app trusts client-supplied *context* it shouldn't.

### F4.1 — sap-client swap

Your `sap-usercontext` cookie carries `sap-client=200`. SAP systems host multiple clients. Try a
handful of reads with `sap-client` set to `000`, `100`, `300` (via the cookie and the inner-URL
param). Does any route to a different client with different data isolation or a test dataset?
Budget: ~4 GETs. **If a different client returns data, STOP and report — do not write there.**

### F4.2 — trust-header injection

Does the SAP Web Dispatcher pass client-supplied headers through to the app server that the app
trusts for identity/routing? On a read to own data, inject (one at a time):
- `sap-user: IN01051651` (spoof the other account's user id)
- `X-Forwarded-For` / `X-Forwarded-User` variants
- `sap-trusted-system` style headers

If any changes the identity the server acts as (e.g., returns B's data to A's session), that's an
auth-confusion bug in the proxy/app config. Budget: ~5 GETs. Read-only.

---

## SURFACE 5 — create-on-demand key-collision (from today's discovery)

We learned MERGE-with-nonexistent-body-id CREATES a row in the caller's own tenant (HigherEducations,
server-normalized id). HigherEducations was per-tenant-scoped. But **DisciplineSet** and
**TrefwoordenSet** use *composite URL keys* `(applicationId='<x>',key='<y>')` — a different shape
where the applicationId is explicit in the key, not aliased to `'0'`.

### F5.1 — DisciplineSet / TrefwoordenSet composite-key create-on-demand cross-tenant

From A's session, batched `MERGE DisciplineSet(applicationId='000000503432',key='1')` (own,
control) → expect 204. Then batched `MERGE DisciplineSet(applicationId='000000503434',key='1')`
(B's applicationId in the URL key) body `{applicationId:'000000503434',key:'1',
disciplineCode:'KLTEST_F51'}`. Does the server:
- 403 / tenant-reject → safe (URL-key authz enforced).
- 204 + creates/updates under B's applicationId → **cross-tenant write via composite key +
  create-on-demand.** Critical. Read B's DisciplineSet to confirm, then restore.

Same probe for TrefwoordenSet. Budget: ~6 non-safe + re-reads. Separate egress from F1.1/F1.4.

---

## Priority order (single-lane, ACL-disciplined)

Each numbered block is one egress rotation (≤12 non-safe requests), with a gap between.

1. **F1.1** — Applications priv-fields via batch. *The crown jewel.* If any inner 204, halt +
   write up.
2. **F1.4** — LongTexts via batch (XSS chain reopen check).
3. **F5.1** — DisciplineSet/TrefwoordenSet composite-key cross-tenant.
4. **F1.2 + F1.5** — changeset atomicity + Content-ID reference (batch-native authz).
5. **F1.3** — Sweep 2 re-run (cross-user reads; GET-only, lighter).
6. **F2.1 + F2.2 + F2.3** — ApplicantPhotos upload surface.
7. **F3.1 + F3.2** — payment verifier (GET-heavy, lighter).
8. **F4.1 + F4.2** — identity/context confusion (GET-only).
9. **F2.4** — ApplicationAttachments lazy-load (GET + conditional).

## Deliverables

Under `vm-results/`:
- `05-track-f-batch.md` — F1.* results (headline: does batch dispatch bypass field authz?)
- `05-track-f-uploads.md` — F2.* + F2.4
- `05-track-f-payment-identity.md` — F3.* + F4.*
- `05-track-f-composite-keys.md` — F5.*
- Append all request rows to `02-authz-matrix.jsonl` with `"sweep": "f1.1"` etc.

Commit each as produced. **If F1.1 or F1.4 or F5.1 lands an inner 204 on a privileged/cross-tenant
write, commit + push + HALT** — that's a reportable Critical and the researcher writes it up
before any further scope.

## Verdict framing (top of each file)

- **BATCH-PATH AUTHZ BYPASS CONFIRMED** — a write the direct path 403s lands 204 via batch.
- **CROSS-TENANT WRITE CONFIRMED** — composite-key or Content-ID smuggling reaches another tenant.
- **STORED XSS REOPENED** — LongTexts writable via batch, or ApplicantPhotos MIME reflected.
- **CLEAN NEGATIVE (now validly tested)** — batch path enforces the same authz as direct; prior
  null results upgraded to real negatives.

## Non-goals (unchanged)

No IdP, no `esap/public/*`, no `webwsd`/`webwsq`, no `zc_ad_appl_chat` (scope-pending), no
credential forgery, no enumeration of real strangers' payment IDs or applicant IDs. Own accounts
A/B only; the target-ID guard stays on.
