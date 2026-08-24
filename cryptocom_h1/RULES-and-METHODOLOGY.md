# Crypto.com HackerOne — Rules digest & safe methodology

Working reference for authorized testing on the Crypto.com HackerOne program
(hackerone.com/crypto). Registered-researcher, in-scope, PoC-driven only.

## Hard prohibitions (instant-ban / ineligibility territory — never do these)

- **DoS — nuanced, read carefully.** Volumetric/flood DoS is OUT ("Denial-of-service
  requiring **significant traffic or specialized tools**"), and blind DoS = None.
  BUT the severity doc rates **Availability (High)** = *"single-request server
  deadloops, complete system crashes requiring manual restart, API failures
  blocking all platform transactions"* → a **single-request** crash / algorithmic
  deadloop (no traffic volume needed) is an in-scope **High**. The Hedera
  single-request-crash *class* is valid here; the flood/amplification-at-volume
  angle is not. Operational limit still binds (*"not... disrupt any of our
  operations"*): demonstrate with ONE controlled PoC and stop — never sustained
  or crash-looping. Resource exhaustion in *limited* features = Availability-Low.
- **No targeting users/employees/staff.** No social engineering, phishing,
  malware, deceptive software (browser/IDE extensions, packages, "AI skills"),
  or extracting telemetry/data from anyone's machine.
- **No draining or blocking other people's funds** (smart contracts) — automatic
  ineligibility for the whole program.
- **No accessing other real users' data beyond a minimal, consented PoC.** Prove
  access with your OWN test accounts / the smallest possible demonstration; never
  mass-dump real customer PII even though that's the "impact" being scored.
- **No scanner-only reports.** Automated-scanner output without manual
  verification + a working PoC is marked **Spam**. Every finding must be manually
  reproduced.
- **Report only through the H1 program.** No public disclosure.

## Scope (only assets within Crypto.com's control)

Three reward bands — value is concentrated in the authenticated APIs:

- **Extreme-tier ($10k–$1,000,000):** `crypto.com/exchange`, **mobile-app APIs
  (incl. BFF)**, **Exchange APIs requiring an account**, `app.mona.co`.
  Extreme (up to $1M) = quick/immediate >$1M fund loss OR mass customer-PII dump.
- **Standard ($1k–$5k crit, avg high $6.4k):** `web.crypto.com`, `og.com`,
  wildcards **`*.crypto.com`** and **`*.mona.co`**, mobile apps.
- **Low tier (small):** travel/tickets/tax/js/nft/price subdomains.

Third-party assets (e.g. help.crypto.com vendors) only in scope if the bug is
caused by a Crypto.com misconfiguration.

Crown-jewel app requires a **KYC signup** to test (100M+ users). Budget for that
if going after the exchange/wallet APIs.

## Severity map — CIA impact matrix (H if *complete* impact on ANY one axis)

High requires all four: clear/immediate impact, no complex interaction, critical
function/sensitive data, fully reproducible PoC.

| Axis | **High** | **Low** |
|---|---|---|
| **Confidentiality** | full DB dump; decrypt ALL TLS; arbitrary file read on critical server; FULL PII; ALL private wallet keys | partial PII; full PII limited scope (~100 customers); limited-capability creds; hashed creds |
| **Integrity** | unrestricted SQLi; root RCE; priv-esc to admin; manipulate ALL balances; modify multi-user transaction data | stored XSS (presentation only); CSRF on profile settings; formula injection; session fixation; single-user XSS |
| **Availability** | single-request deadloop; full crash needing manual restart; API failure blocking ALL transactions | single-account lockout; rate-limit gaps; resource exhaustion in limited features |

- **Critical / Extreme ($10k–$1M):** loss of funds, full account takeover on
  money-moving APIs, mass PII exfiltration (the top end of the above).
- **None (N):** blind DoS, clickjacking w/o data theft, banners, stack traces,
  public blockchain addresses, cache-timing w/o data leak. (Don't bother.)

Caps: multiple Lows don't combine into a High; significant user interaction caps
at Low; staging/dev < prod; physical/insider = Low/None.

Takeaway: severity = **completeness of impact on one CIA axis**. Partial = Low;
complete = High; funds/mass-PII/ATO = Critical/Extreme.

## Highest-EV, in-bounds vulnerability classes to hunt

All safe/non-destructive; all map to High/Critical by the matrix above:

1. **Broken access control / IDOR** on account-scoped API endpoints — reading or
   acting on another account's data/orders/funds. (Test with two of your own
   accounts; never a real third party.) This is the classic exchange-API crit.
2. **Authorization / business-logic flaws** in value-moving flows — state changes
   or privilege you shouldn't have (e.g. manipulate an order/withdrawal/reward
   flow in your own account in a way that shouldn't be allowed).
3. **Account-takeover chains** — auth bypass, token/session handling, OAuth/SSO
   misconfig, password-reset flaws.
4. **SSRF** on `developer-*`/API hosts, and **secrets exposure** in `js.crypto.com`
   / other JS bundles (leaked keys, internal endpoints).
5. **Server-side injection** (SQLi, template, GraphQL authz on `/nft`) with real
   data-access impact.

## Division of labor (honest)

- **You** run the actual authorized testing on your side (this sandbox cannot
  reach crypto.com, and the program requires manual, human-verified PoCs).
- **I** help with: recon strategy, endpoint/attack-surface analysis, reading JS
  bundles / API responses you capture, reasoning about auth/logic flaws,
  designing minimal safe PoCs, and writing up findings to their PoC standard.
