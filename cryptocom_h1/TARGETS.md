# Crypto.com HackerOne — complete in-scope target inventory

Program stats (from scope page): total bounties paid **$1,624,275**; average
bounty range **$476–$572**; top realized **$5,000–$201,000**; **1,131 reports in
last 90 days** (very active / heavily picked-over); last report resolved 7h ago.

---

## Low Bounty Tier — Critical $200–$500 (small money)
1. `travel.crypto.com`
2. `tickets.crypto.com`
3. `tax.crypto.com`  — *Critical & High severity only*
4. `js.crypto.com`  — static JS host (secret/endpoint recon target)
5. `https://crypto.com/nft`  — *GraphQL-based DoS reward capped $500*
6. `experiences.crypto.com`
7. `developer.crypto.com`
8. `developer-platform-api.crypto.com`
9. `developer-api.crypto.com`
10. `https://crypto.com/price`  — *max severity Medium*

## Extreme Tier ELIGIBLE — Critical $10k–$1M (avg $15k); Extreme up to $1M
1. `https://crypto.com/exchange`
2. **Crypto.com mobile app APIs that require an account** — *includes any BFF APIs* (needs KYC account)
3. **Crypto.com Exchange APIs that require an account** — *includes any BFF APIs* (needs account)
4. `app.mona.co`

## Extreme Tier NOT Eligible — Critical $1k–$5k (avg $10.8k); High $200–$1k (avg $6.4k)
1. `web.crypto.com`
2. `og.com`
3. `*.mona.co`  — **wildcard**
4. `*.crypto.com`  — **wildcard** (broadest surface; 101 resolved reports / 25% of all activity)
5. `com.monaco.mobile`  — iOS app (App Store)
6. `co.mona.android`  — Android app (play.google.com/store/apps/details?id=co.mona.android)
7. `merchant.crypto.com`
8. (one further asset in this tier carried a "GraphQL DoS capped $200" / "Critical & High only" note)

## Smart Contract — Critical $50,000–$1,000,000
1. `explorer.cronos.org/token/0x2e53c5586e12a99d4CAE366E9Fc5C14fE9c6495d`
2. `etherscan.io/token/0xfe18ae03741a5b84e39c295ac9c856ed7991c38e` — CDCETH; Critical up to $50k, Extreme up to $1M (needs Solidity/audit skills — different lane)

---

## Strategic read (honest)
- **Money is bimodal:** average payout ~$500, but a few land $50k–$201k. Most
  researchers get the ~$500 end. Set expectations accordingly.
- **Highest EV for us (web/API, no Solidity):** the two **wildcards** (subdomain
  enumeration → forgotten/weak asset) and the **account-required APIs** (IDOR /
  authz, needs KYC signup). `js.crypto.com` + web bundles = the free, phone-doable
  starting point (secrets + endpoint discovery).
- **Skip for now:** `crypto.com/nft` (GraphQL DoS capped $500), `crypto.com/price`
  (Medium max), smart contracts (different skillset).
- **Competition is heavy** (1,131 reports/90d) — the realistic win is a subtle
  authz flaw or a leaked secret others missed, not low-hanging fruit.
