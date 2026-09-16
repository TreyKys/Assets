# DigitalOcean — Droplet web-console trust model & the cross-tenant RCE theory (2026-09-16)

Reconstructed from DO's open-source `droplet-agent` (github.com/digitalocean/droplet-agent,
an in-scope asset). This is the strongest high-value lead of the engagement. **Honest status:
a well-founded *theory* pointing at a Critical authenticated test — NOT a confirmed bug.**
The client code proves the blast radius is maximal; only a backend authorization check
(untestable without an account) stands between "safe" and "cross-tenant root."

## The full web-console SSH flow (reconstructed)
1. User clicks "Launch Droplet Console" in `cloud.digitalocean.com`.
2. Backend generates a temporary SSH keypair and writes the public key into the **target
   Droplet's metadata** as a `dotty_key`. Shape (from `sysaccess/common.go`):
   `{ "os_user": "...", "ssh_key": "<algo> <key>", "actor_email": "...", "ttl": <seconds> }`.
3. Backend sends a **port-knock**: a TCP SYN to the Droplet's SSH port with hardcoded magic
   `seq=68796879` ("DODO"), `ack=848489` ("TTY") (`watcher/ssh_watcher.go`).
4. Agent's packet sniffer detects the knock → fetches `http://169.254.169.254/metadata/v1.json`
   over plain HTTP (`watcher/fetcher.go`) → parses `dotty_keys` (`ssh_key_parser.go`) →
   injects each into `authorized_keys` of the key's `os_user` (`sysaccess/*`), with a TTL.
5. Console connects over SSH using the temp key.

## Trust analysis (what the client proves)
- **No cryptographic verification of dotty keys.** The agent trusts whatever
  `169.254.169.254` returns. Root of trust = the metadata service + the backend that populates
  it. (This is a standard cloud-metadata trust model — NOT itself a bug.)
- **`os_user` is attacker-specifiable and unrestricted** (`\S+`, then `GetUserByName`). A
  dotty key can target `root`. So a dotty-key injection = **root**, not a limited user.
- **Injection hardening is present** (`containsNewlineOrEncodedNewline` blocks
  authorized_keys line-injection) — so the naive newline trick is dead.
- **Therefore ALL cross-tenant safety rests on step 2's authorization**: does the backend
  verify the caller owns the target Droplet before writing a `dotty_key` to its metadata?

## THE Critical test (authenticated — needs an account + 1 own Droplet)
Provision a Droplet you own (Droplet A) and note its ID. Then drive the "launch console" /
dotty-key-provisioning API (captured from the panel's network calls) but substitute a
**Droplet ID / resource you do NOT own** (or a fabricated/adjacent integer ID — Droplet IDs
are enumerable integers). Watch for any of:
- The API accepting a target Droplet that isn't yours (BOLA on the console-provisioning call).
- Being able to set `os_user=root` and an arbitrary `ssh_key` you control in the request.
- The dotty key landing in another tenant's Droplet metadata.
If yes → inject your public key into a victim Droplet → SSH in as root → **cross-tenant RCE,
Exceptional tier ($8k–$10k)**. Use `whoami`/`hostname`/`/etc/hostname` as the acceptable PoC.
This is DO's explicitly-stated #1 wanted class ("broken authorization → other customer
records" / "cross-VM / multi-tenancy break"). Only touch your OWN second Droplet as the
"victim" to prove it safely — never a real customer's.

## Lower-severity observations (from the same code, likely Low/Info — not worth solo reports)
1. **Forgeable port-knock**: the trigger is static, hardcoded magic numbers, now public. Any
   internet host that can SYN a Droplet's port 22 can force the agent to resync metadata
   (rate-limited 5/s via `golang.org/x/time/rate`). No key injection (keys still come from
   trusted metadata) → low impact, but a real design weakness (a per-Droplet secret/nonce
   would be stronger). Bundle as hardening context, not a standalone bounty.
2. **`webAddr = ":303"` binds `0.0.0.0`** on the non-Linux (`new_watcher_general.go`) build —
   an unauthenticated `/new_metadata` trigger exposed on all interfaces, while the sibling
   debug server is deliberately `127.0.0.1:304`. Linux droplets use the port-knock watcher,
   so impact is limited to non-Linux builds; still, forced-refresh only (low).
3. **Plain-HTTP metadata fetch** (`http://169.254.169.254`, `//nolint:gosec`) — standard for
   link-local metadata; not independently exploitable.

## Why this matters / honest framing
- Reportable *now*, unauthenticated: nothing here is a confirmed bug (the repo is "no bounty";
  the standalone observations are Low/Info).
- The **value** is the theory + the exact, pre-scoped Critical test. If the console
  provisioning authz is flawed, this is the biggest payout on the program. The client code
  proves the consequence is root-level and cross-tenant — it does NOT prove the backend is
  vulnerable. That requires the authenticated test above.
- This is the strongest reason yet to run the (card-gated, but paid-resource-cheap) account
  phase: one Droplet (~$4/mo, deletable same day) unlocks the highest-ceiling test we found.
