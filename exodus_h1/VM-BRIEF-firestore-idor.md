# VM BRIEF — Firestore access-control check on Fusion (Exodus E2E sync) — HIGH-POTENTIAL, do carefully

## Why this matters
The client uses **Firestore** (not RTDB) for **Fusion**, Exodus's encrypted personal sync:
- `collection("Users").doc(uid)` — per-user doc, `uid = hash(box.publicKey)`.
- `collection("channels").doc(x).collection("channelData")` — encrypted sync channels.
Anonymous Firebase sign-up is **enabled** (proven in `05-backend-recon.md`). If the Firestore rules
gate on `request.auth != null` (a very common misconfig) instead of ownership
(`request.auth.uid == uid`), then **any anonymous user can read and/or overwrite any user's sync
document** — a cross-tenant access-control bug (High/Critical), in-scope, not DoS. The data is
encrypted at rest, but (a) unauthorized READ across tenants is still a confidentiality/authorization
finding, and (b) unauthorized WRITE lets an attacker corrupt/overwrite other users' backups
(integrity). This is worth a careful, decisive check.

## RULES (privacy-critical — do not deviate)
- `User-Agent: h1-treyky` on every request. Single requests, no enumeration, no loops.
- **NEVER read, list, or store any real user's document or any real `uid`.** Do not guess/enumerate
  real uids. Do not dump collections.
- The decisive test uses a **non-existent, obviously-fake uid** so it reveals *rule behavior* with
  ZERO real data. That distinction is the whole point:
  - `403 PERMISSION_DENIED` on a fake doc → rules are ownership-gated → **locked (good), STOP, report locked.**
  - `404 NOT_FOUND` / `200` empty on a fake doc → the read was *allowed* (doc just doesn't exist) →
    **rules permit non-owner reads → FLAG. STOP. Do NOT then go read real docs** — report the rule
    behavior; impact is confirmed ethically with our OWN accounts only (see below).
- If you must demonstrate impact, use **only accounts/identities you create** (policy: "only interact
  with accounts you own"). Never touch a third party's data.
- Commit to `exodus_h1/vm-results/06-firestore-idor.md`. Do not submit anything.

## Probe A — unauthenticated read of a FAKE doc
```
curl -s -o /dev/null -w "%{http_code}\n" -A "h1-treyky" \
 "https://firestore.googleapis.com/v1/projects/exo-prod/databases/(default)/documents/Users/ZZZ_nonexistent_test_uid_treyky_0001"
```

## Probe B — anonymous-authed read of the same FAKE doc
Get a fresh anon idToken, then read the fake doc with it:
```
TOKEN=$(curl -s -A "h1-treyky" -X POST \
 "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=AIzaSyDxjHgyc4UkFrUptMX-B4s7YS-PfITLOmE" \
 -H "Content-Type: application/json" -d '{"returnSecureToken":true}' | jq -r .idToken)

curl -s -o /dev/null -w "%{http_code}\n" -A "h1-treyky" \
 -H "Authorization: Bearer $TOKEN" \
 "https://firestore.googleapis.com/v1/projects/exo-prod/databases/(default)/documents/Users/ZZZ_nonexistent_test_uid_treyky_0001"
```
Record the FULL status + body for both A and B. Also repeat B for a fake `channels` path:
`.../documents/channels/ZZZ_nonexistent_test_channel_treyky_0001`.

## Interpreting
| A (unauth) | B (anon auth) | Meaning |
|---|---|---|
| 403 | 403 | Rules ownership-gated → **locked**. Clean dead-end, report and stop. |
| 403 | 404/200 | **Anon-authed non-owner READ allowed** → misconfig. FLAG (High-potential). |
| 404/200 | 404/200 | **Unauthenticated non-owner READ allowed** → worse. FLAG (Critical-potential). |

## If FLAGGED — confirm WRITE + cross-tenant with OWN data only (stop-and-report if unsure)
Only if a read flag appears, and staying strictly on self-owned data:
- Attempt a Firestore `PATCH`/`commit` write to a **fake/own** doc id with the anon token to see if
  write is also permitted (create `Users/ZZZ_own_test_...` — a doc you own/created, not anyone else's).
- Do NOT write to, overwrite, or read any id that could belong to a real user.
Report exact requests/responses. Then STOP for the humans to write it up.

## Output
`06-firestore-idor.md`: Probe A/B statuses + bodies, the interpretation, and verdict
(locked / read-open / read+write-open). If locked, say so plainly — that closes the Firebase chapter.
