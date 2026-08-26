# Best-fit HackerOne targets — matched to your proven setup

Your winning pattern (Hedera): phone → SSH → cloud Linux VM → **clone open-source
code, run your own instance, find backend logic/resource bugs by reading + testing**.
This shortlist keeps that exact workflow. Everything here is **open-source and
self-hostable**, so you never fight Cloudflare, a phone-vs-web-app mismatch, or a
KYC/geo wall — you own the instance.

## Fit criteria
- Open-source + self-hostable (read the code, run it yourself) ✔ your edge
- Backend-heavy (logic, access-control, resource/algorithmic bugs) ✔ your Hedera skill
- Paid bounty on HackerOne (you're set up there) — **verify it's paid, not VDP-only**
- No submission fee, no financial-KYC, no geo trap

## Ranked shortlist

### 1. GitLab  — the gold standard for this workflow
- **Why it fits:** huge open-source codebase (GitLab CE), officially encourages
  hunting on your **own self-hosted instance**, mature paying program, wide range
  of accepted bug classes (access control, SSRF, injection, logic). This is the
  single best match for "read source + self-host + get paid."
- **Start:** `docker run` GitLab CE on your VM; pick one feature area (CI/CD
  runners, webhooks, import/export, GraphQL API) and read that code deeply.
- **Caveat:** popular, so avoid the obvious front-door; go where the crowd doesn't
  (obscure API params, import parsers, background jobs).

### 2. Nextcloud  — self-hostable, less trodden than GitLab
- **Why it fits:** self-hosted file/collab platform (PHP), active HackerOne bounty,
  strong appetite for access-control / IDOR / auth-logic bugs. Smaller crowd than
  GitLab.
- **Start:** self-host via Docker; focus on sharing/permissions logic and app APIs.

### 3. Mattermost  — Go backend, self-hostable
- **Why it fits:** open-source Slack alternative in **Go** (closer to your
  backend-service comfort), self-hostable, paying program, values API auth/logic
  and resource bugs.
- **Start:** run the server locally; read the REST API + permissions layer.

### 4. Grafana Labs  — Go, self-hostable, active
- **Why it fits:** open-source observability (Go), self-hostable, active HackerOne
  program; data-source proxying is a recurring SSRF/authz hotspot — right up your
  code-reading alley.

### 5. Discourse  — Ruby forum, self-hostable
- **Why it fits:** open-source, self-hostable, paying; logic/access-control bugs in
  a big readable codebase.

## Wildcard (your sharpest niche): blockchain infra
Your Hedera bug was a **blockchain JSON-RPC relay** — that's your most-proven
edge. Other open-source **nodes/relays/bridges** are the closest possible match.
Many live on Immunefi/Cantina rather than HackerOne, and some Immunefi programs
have **no** novice fee — worth checking per-program. If you want to double down on
exactly what you already did well, this is it.

## Honest notes
- I can't see live HackerOne program pages from here (login-gated/egress-blocked).
  **You're signed in — verify each is currently PAID (not VDP-only) and in-scope
  before investing.** Don't take my payout memory as current truth.
- Open-source programs are competitive too. Your edge isn't "find any bug" — it's
  applying the Hedera method (read a specific subsystem's code, find where it does
  unbounded/unsafe work, prove it on your own instance) to a corner others skip.
- Same setup as before: cheap cloud VM, SSH from the phone, `git clone`, `docker
  compose up`, read + test. That's the whole toolkit.
