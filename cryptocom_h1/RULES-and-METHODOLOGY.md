# Crypto.com HackerOne — Rules digest & safe methodology

Working reference for authorized testing on the Crypto.com HackerOne program
(hackerone.com/crypto). Registered-researcher, in-scope, PoC-driven only.

## Hard prohibitions (instant-ban / ineligibility territory — never do these)

- **No disruption / DoS.** Policy: *"You commit to not attempting to sabotage or
  disrupt any of our operations."* Out-of-scope list: *"Denial-of-service
  requiring significant traffic or specialized tools."* Severity doc: blind DoS
  = **None (N)** severity (worthless). → The Hedera crash/OOM/amplification
  playbook is triple-excluded here. Do not point it at any crypto.com asset.
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

## Severity map (their CVSS CIA-impact model) — where High/Critical actually is

- **Critical / Extreme:** loss of funds, full account takeover on money-moving
  APIs, mass PII exfiltration.
- **High:** *complete* data/access compromise — full DB dump, all private keys,
  all payment-card details, complete PII exposure, arbitrary file read on a
  critical server, full TLS decryption. ("Clear and immediate, directly
  exploitable, critical functions/sensitive data, fully reproducible.")
- **Low:** *partial* disclosure — some restricted info, limited-scope PII,
  limited-capability creds, predictable session IDs, hashed creds.
- **None (N):** blind DoS, clickjacking w/o data theft, banners, stack traces,
  public blockchain addresses, cache-timing w/o data leak. (Don't bother.)

Takeaway: severity here is driven by **how much sensitive data/access/funds** a
bug yields. Partial = Low, complete = High, funds/mass-PII = Critical.

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
