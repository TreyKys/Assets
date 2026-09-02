# Best-fit HackerOne targets — matched to your proven Hedera pattern

Your winning pattern (Hedera): read open-source code → self-host on a cheap VM
you SSH into from your phone → find backend logic/resource bugs that reproduce
with a single crafted request.

## Important industry context (verified Aug 2026)

Before picking a target, know the landscape:

- **HackerOne's Internet Bug Bounty (IBB) is PAUSED** as of March 2026 — no new
  submissions. It was the classic funnel for open-source bug rewards.
- **Payouts across programs dropped hard in 2026**: critical avg ~$2,257
  (was $9,250); high ~$1,009 (was $4,429). AI-assisted vuln finding is
  outpacing remediation, and programs are compensating by cutting.

Translation: **any specific payout figure in this list is uncertain — verify on
each program's live HackerOne page on your account before investing time.**

## The shortlist (all open-source, self-hostable, on HackerOne)

Ranked by fit to your setup + odds of a real find.

### 1. Nextcloud — the strongest match
- HackerOne: `hackerone.com/nextcloud`
- Self-hostable (Docker one-liner, no AWS needed). PHP. Access-control /
  file-sharing logic bugs pay well historically.
- Why it fits: you spin up your own instance, create two test accounts, look
  for IDOR / auth-logic in the sharing layer. Exactly the Hedera setup.
- Verify: is it currently paying? (was up to ~$5k historically). Check scope
  before investing.

### 2. Mattermost — Go, self-hostable
- HackerOne: `hackerone.com/mattermost`
- Go backend (closer to your Hedera comfort). Self-hostable. Cares about API
  auth, plugin sandbox escape, and permission-model bugs.
- Why it fits: Go source reading is what you already did well; the auth model
  is complex; teams/channels/permissions is a rich logic surface.

### 3. Discourse — Ruby forum
- HackerOne: `hackerone.com/discourse`
- Self-hostable, 100% open source. $256 minimum bounty (verified).
- Why it fits: mature program, willing to pay for logic bugs. Ruby (I can read
  it with you).
- Caveat: heavily hunted — like GitLab, obvious veins mined.

### 4. Sentry — Django/Python, self-hostable
- HackerOne: `hackerone.com/sentry`
- Open-source. Ingestion pipeline, event processing — resource / parser bugs
  are your sweet spot.
- Why it fits: the ingestion path handles untrusted event JSON at scale, and
  parser/complexity bugs there have the Hedera flavor.

### 5. Rocket.Chat — Node/JS, self-hostable
- HackerOne: `hackerone.com/rocketchat`
- Similar surface to Mattermost; less hunted.

### 6. Wildcard — smaller/newer blockchain relays and infra (Immunefi/Cantina)
- Your Hedera win *was* a blockchain JSON-RPC relay. That's your sharpest
  proven niche.
- Look for newer non-EVM chains launching bridges/relays in the past 6-12
  months. Immunefi lists them; some don't have a novice fee.
- Not on HackerOne, but honest note: this is where your specific skill
  already worked once.

## What to check on each program's HackerOne page (before you invest hours)

For each candidate, verify on your signed-in H1 account:

1. **Is it a PAID program or VDP-only?** (VDP = reputation/rep only, no money.)
2. **"Assets in scope"** — is "self-hosted instance" or the source repo listed?
3. **Reward table** — what are current Low/Med/High/Critical amounts?
4. **Resolved-report count** on each asset — high = crowded (skip); low or
   zero = less trodden (favor).
5. **Response efficiency / avg time to bounty** — some programs are slow or
   ghost researchers. Slow programs are still fine, but plan accordingly.
6. **Out-of-scope rules** — especially: DoS clauses, "internally known issues"
   handling, and any exclusions on the vuln class you plan to hunt.

## Honest recommendations

- **Start with Nextcloud OR Mattermost** — best fit for your setup (self-host +
  backend code reading), and both accept the vuln classes you're good at
  (auth/IDOR/logic + resource bugs).
- **Do NOT waste time on Discourse or Sentry first** — they're excellent
  programs but heavily hunted. Try them only if #1 and #2 give you traction
  and you want a bigger surface.
- **Don't chase specific payout figures I've quoted** — verify live. The
  industry cut payouts in 2026, and my figures are from mixed-date sources.

Sources: [IBB paused (Infoworld)](https://www.infoworld.com/article/4154210/internet-bug-bounty-program-hits-pause-on-payouts.html) · [HackerOne payout cuts (The Register)](https://www.theregister.com/security/2026/05/21/hackerone-takes-an-axe-to-its-bug-bounty-rewards/5244458) · [Nextcloud bounty program](https://nextcloud.com/blog/introducing-the-nextcloud-bug-bounty-program/) · [Mattermost H1](https://hackerone.com/mattermost)
