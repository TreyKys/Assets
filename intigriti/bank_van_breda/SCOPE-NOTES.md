# Bank J.Van Breda & C° — Intigriti program vetting

## Verdict: STRONG target — proceed

- First bug bounty program (fresh scope). 211 submissions, only 33 accepted, 40 researchers total.
  Low crowding for a financial target.
- Two related brands, shared infra likely: Bank Van Breda + Bank de Kremer.
- Mobile apps (Android + iOS, both brands) in scope at TIER 1 (highest payout tier).
- IDOR explicitly welcomed in policy, with explicit severity-scoring guidance (UUID guessability
  affects Attack Complexity/Privileges Required) — they expect and want access-control findings.
- Explicitly want: "breach of confidential data" and "performing financial transactions".
- Test credentials available via program FAQ — need NOT use real bank accounts.
- `web-xs2a.bankvanbreda.be` = PSD2 open-banking XS2A API (account info / payment initiation) —
  Tier 1, prime IDOR/authz surface given financial-transaction data.
- Rate limit: 5 req/sec automated tooling permitted. Safe harbor applies.
- Standard exclusions (no DoS/brute-force, no social engineering, no physical/MITM, personnel excluded).

## Payout table
| Severity | Tier 1 | Tier 2 |
|---|---|---|
| Low | €150 | €100 |
| Medium | €750 | €400 |
| High | €2,000 | €1,000 |
| Critical | €5,000 | €2,000 |
| Exceptional | €10,000 | €4,000 |

## In-scope assets
**Tier 1:** `*.mobile.bankdekremer.be`, `*.mobile.bankvanbreda.be` (wildcards),
`be.bankvanbreda.mobile` (Android), `be.bankdekremer.mobile` (Android),
2x iOS apps (VanBredaOnline + one other), `secure.bankdekremer.be`, `secure.bankvanbreda.be`,
`web-xs2a.bankvanbreda.be`

**Tier 2:** `*.bankdekremer.be`, `*.bankvanbreda.be`, `*.vanbredacarfinance.be`,
`secure.vanbredavendor.com`, `vpn.jvanbreda.be`

## Plan — two tracks
**Track A (start now, no creds needed):** Pull both APKs, run the Firebase/client-config playbook
(firebase_hunt/PLAYBOOK.md) — check for embedded Firebase config, hardcoded secrets, open rules.

**Track B (needs test creds from program FAQ):** IDOR/access-control hunt on secure.bankvanbreda.be,
secure.bankdekremer.be, and especially web-xs2a.bankvanbreda.be (PSD2 XS2A API — account/transaction
data). This matches exactly what the program policy invites.

## Next step
Get test-credential info from the program FAQ tab. Start Track A (APK pull) in parallel — doesn't
need credentials.


## CRITICAL UPDATE — credential path likely blocks Track B

Program's actual answer on getting test access: fill out their contact form, mention you're an
Intigriti researcher, go through their **real customer onboarding** (no test/sandbox credentials).
**"Normal costs will apply"** and **"onboarding is only possible for Belgian self-employed people,
entrepreneurs or liberal professions."** Use your Intigriti email when asked.

This is a hard eligibility wall, not just friction — a non-Belgian, non-self-employed researcher
cannot legally complete this onboarding. Track B (authenticated IDOR hunt on secure.*/web-xs2a.*)
is **not viable** via this path unless the researcher genuinely qualifies.

**Next move:** message the program directly via Intigriti (not the physical contact form) and ask
for read-only test/sandbox credentials instead, citing the eligibility mismatch. Reasonable ask
given their policy explicitly wants IDOR findings tested.

**Unaffected — proceed regardless:**
- Track A/A2 (mobile APK static analysis) — zero credentials needed.
- Unauthenticated web/subdomain recon within scope — `*.bankvanbreda.be`/`*.bankdekremer.be`
  wildcards may hide forgotten staging/dev assets; `vpn.jvanbreda.be` (Tier 2, in scope) is a
  VPN portal — classic unauthenticated target (known-CVE check, auth bypass, info disclosure),
  no account needed at all.
