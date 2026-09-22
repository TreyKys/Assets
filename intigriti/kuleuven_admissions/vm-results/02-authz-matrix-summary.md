# Track B — authz-matrix — execution status

**Status: BUILT & VALIDATED — NOT YET RUN LIVE (blocked on session credentials).**
Date: 2026-09-22.

This file is a placeholder status record. It is **regenerated automatically** with the real
sweep×status table and anomaly expansions the moment the harness runs against live sessions
(`python3 tools/authz_matrix.py` → `build_summary()` overwrites this file from
`02-authz-matrix.jsonl`). **No results below are fabricated** — the matrix has not been run, because
the required authenticated sessions are not present in the VM.

## Why it hasn't run
The brief (§Setup) requires the **human** to provide fresh SAP session cookies, captured from the
already-authenticated Admissions app (the `idp.kuleuven.be` login is out of scope and never touched
by the harness):

- `~/kuleuven_creds/A.cookies`  ← account A (`IN01051619` / app `000000503432`)
- `~/kuleuven_creds/B.cookies`  ← account B (`IN01051651` / app `000000503434`)

Neither file exists in this VM (`~/kuleuven_creds/` is absent), and SAP OData sessions expire
quickly, so cookies must be captured immediately before a run. Until they are dropped in, the harness
halts at startup with a clear message rather than touching the live university system.

## What IS done and committed
- **`tools/authz_matrix.py`** — the complete execution harness for all 8 sweeps, faithful to the
  brief. Stdlib-only (Python 3.12 verified).
- **`vm-results/02-authz-matrix.plan.jsonl`** — the full request plan produced by `--dry-run`
  (no network): **293 planned live requests** across the 8 sweeps, cookies redacted. This is the
  exact set of calls the live run will make, reviewable before you authorize execution.

### Request plan (from the dry run — this is the shape the live matrix will fill)
| Sweep | what it tests | planned live requests |
|---|---|---|
| 1 | privileged-field MERGE matrix on OWN application (`statusCode`, `isAppFeePayed`, `caseAdmin`, `institution`, `program`, `guid`, …) + compound | 48 rows / ~28 reqs |
| 2 | `$batch`-wrap of every Track-A 403/400 read; inner-vs-direct status compare (+changeset for writes) | 10 |
| 3 | Sweep-1 write set **without** `x-csrf-token`; any 204 = CSRF not enforced | 10 |
| 4 | `$expand` lateral read (own + one cross-user `Applicants('IN01051651')?$expand=…`) | 5 |
| 5 | FunctionImports `isPaymentDone` / `showSpringFall` / `showOptions` / `getSwitchOpenSearch` × input sets | 114 |
| 6 | illegal `statusCode` transitions on OWN app + workflow side-effect probe (baseline captured, **restored** after) | 16 |
| 7 | stored-XSS persistence probe on OWN free-text fields, **mandatory `""` cleanup + verify per field** | 150 rows / ~125 reqs |
| 8 | `$filter` OR-injection / `1 eq 1` / single-quote / `$select=*` over-exposure | 6 |
| **total** | | **~293 requests · ~5.4 min @ 1 req/s** |

(Row counts exceed request counts because COMPARE/CLASSIFY/NOTE bookkeeping rows are logged too.)

## Safety controls verified (unit-tested against the harness)
- **Host allow-list** — only `webwsp.aps.kuleuven.be`; rejects `idp.kuleuven.be`, `/esap/public/*`,
  and any other host/path. ✅
- **Target-ID guard** — any `IN########` or 12-digit application id in a request URL must be A's or
  B's; an **adjacent id aborts the run** (protects real applicants — the ethical hard line). ✅
- **Rate limit** — global ≥1.1 s between requests. ✅
- **IMMEDIATE-STOP** — a response carrying a name/email/DOB lacking every own-identity marker
  (`Intigriti`/`Test`/`treyky*`) halts that sweep-class and logs `IMMEDIATE_STOP`. ✅
- **Session-death detection** — 401 or 302→IdP raises `SessionExpired` and halts for fresh cookies. ✅
- **Sweep 7 cleanup** — every free-text field is reset to `""` in a `finally:` and re-read to verify. ✅
- **Sweep 6 restore** — baseline `statusCode` captured up front and restored after the transition
  tests (belt-and-suspenders; not required by brief). ✅
- **Log hygiene** — session cookies scrubbed from every logged response snippet (200-char cap). ✅

## To run it (once you have sessions)
```bash
mkdir -p ~/kuleuven_creds
#  paste account A's cookies (a 'Cookie: …' line, or a Netscape cookies.txt export) into:
#    ~/kuleuven_creds/A.cookies
#  and account B's into ~/kuleuven_creds/B.cookies
python3 intigriti/kuleuven_admissions/tools/authz_matrix.py            # all 8 sweeps
#  or a subset:  --sweeps 1,4,8      |   re-build summary:  --summary-only
```
On completion the harness writes `02-authz-matrix.jsonl` (one row per request) and regenerates this
`02-authz-matrix-summary.md` with the real sweep×200×403×anomaly table, every anomaly expanded
expected-vs-actual with a severity guess against the program tiers, explicit CLEAN-NEGATIVE lines for
sweeps that produced nothing, and Sweep-7 cleanup verification.
