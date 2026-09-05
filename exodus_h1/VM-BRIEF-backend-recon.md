# VM BRIEF — Firebase + backend config recon (creative, in-scope, NOT DoS)

You are the execution agent. This targets Exodus's own backend (in scope: "websites and subdomains
under Exodus's control"). It must be done **minimally and responsibly** — this is a config/rules
check, NOT an attack. Read the RULES section twice.

## Why this is worth doing
The extracted client embeds Exodus's Firebase project config. Misconfigured Firebase security rules
(unauthenticated read/write to RTDB/Firestore/Storage, or open sign-up) are a common real
High/Critical and are NOT DoS. The API key itself is public-by-design and is NOT a bug — only
misconfigured RULES are. When rules are correct this is a quick dead-end.

## Firebase config (from client `network/index.js`)
```
apiKey:            AIzaSyDxjHgyc4UkFrUptMX-B4s7YS-PfITLOmE
authDomain:        exo-prod.firebaseapp.com
databaseURL:       https://exo-prod.firebaseio.com
projectId:         exo-prod
storageBucket:     exo-prod.appspot.com
messagingSenderId: 166438186762
appId:             1:166438186762:web:a7f33e96f9bf3d73
```

## RULES — read carefully (violating these harms real users and the program relationship)
- Add header `User-Agent: h1-treyky` to EVERY request.
- **ONE probe per service. Read-only. No writes. No brute-force. No automation loops. No rate hammering.**
- These are single, benign, non-destructive reads — equivalent to loading a URL — which is within
  "public internet surface" testing. Do NOT escalate to "extended testing" (many requests, fuzzing,
  writes): the program requires emailing `bugbounty@exodus.com` for that. If a probe suggests an issue,
  **STOP and report — do NOT dump, enumerate, or access any real user data** (that's a privacy
  violation the policy forbids). We disclose the misconfig; we never harvest data.
- Do NOT touch Exchange / XOSWAP / fiat / blockchain-RPC hosts.
- Commit findings to `exodus_h1/vm-results/05-backend-recon.md`. Do not submit anything.

## Probes (run each ONCE, record exact status + first line of response)

### 1. Realtime Database rules
```
curl -s -A "h1-treyky" "https://exo-prod.firebaseio.com/.json?limitToFirst=1"
```
- `{"error":"Permission denied"}` → **locked (good, expected)**. Record and move on.
- Any JSON data / not-permission-denied → **potentially open**. STOP. Record the status only (do NOT
  pull more paths / more data). This would be the finding.

### 2. Firestore (REST, unauthenticated)
```
curl -s -A "h1-treyky" "https://firestore.googleapis.com/v1/projects/exo-prod/databases/(default)/documents?pageSize=1&key=AIzaSyDxjHgyc4UkFrUptMX-B4s7YS-PfITLOmE"
```
- 403 `PERMISSION_DENIED` → locked. `200` with documents → potentially open; STOP + record status only.

### 3. Storage bucket listing
```
curl -s -A "h1-treyky" "https://firebasestorage.googleapis.com/v0/b/exo-prod.appspot.com/o?maxResults=1"
curl -s -A "h1-treyky" "https://storage.googleapis.com/exo-prod.appspot.com/"
```
- 403 → locked. 200 with an object list → potentially public; STOP + record status only.

### 4. Auth — is unauthenticated sign-up / anonymous enabled?
```
# anonymous sign-in attempt (identitytoolkit) — tells us if anon auth is on
curl -s -A "h1-treyky" -X POST "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=AIzaSyDxjHgyc4UkFrUptMX-B4s7YS-PfITLOmE" -H "Content-Type: application/json" -d '{"returnSecureToken":true}'
```
- `OPERATION_NOT_ALLOWED`/`ADMIN_ONLY_OPERATION` → sign-up disabled (good). A returned `idToken` →
  anonymous/self sign-up is enabled; record it (only relevant if combined with permissive rules).

## Light API surface checks (ONE unauthenticated GET each; record status/shape only)
Only these in-scope custom APIs (NOT blockchain RPC, NOT exchange/fiat):
```
curl -s -A "h1-treyky" -i "https://ctr.a.exodus.io/registry" | head -20
curl -s -A "h1-treyky" -i "https://assets-gateway-clarity-api.a.exodus.io/assets" | head -20
```
Note anything that looks like: unauthenticated access to non-public data, verbose errors/stack traces,
IDOR-shaped IDs, CORS `Access-Control-Allow-Origin: *` with credentials, or open redirects. Record
observations; do NOT fuzz or iterate IDs (that's "extended testing" → needs permission first).

## Output
`exodus_h1/vm-results/05-backend-recon.md`: a table of each probe → exact HTTP status + one-line
result + verdict (locked / potentially-open / needs-human-review). If everything is locked (likely),
say so plainly — that's a clean, fast dead-end and we move on. If anything is potentially open, STOP
and flag it for the humans; do NOT explore further.
