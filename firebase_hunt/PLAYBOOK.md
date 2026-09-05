# Firebase / client-config misconfig hunting — reusable playbook

The pattern that worked end-to-end on Exodus (extract client → pull embedded backend config → check
rules). Exodus was locked; most programs aren't. This is **non-DoS**, signal-building, phone+VM
friendly, and lands real High/Critical when it hits. This doc = target selection + tooling + probes +
the scope/ethics rules that keep it legitimate.

## GOLDEN RULES (read first — this is what keeps you safe and paid, not banned)
1. **Only test Firebase projects that belong to an IN-SCOPE asset of a program you are authorized on.**
   The Firebase project must be the *target's own*. Many apps embed a **third-party SDK's** Firebase
   (analytics vendor, etc.) — that project belongs to the vendor, NOT your target → out of scope, do
   not touch. Confirm ownership (project id matches the target's naming, or the app is first-party).
2. **Read-only, non-destructive, minimal.** Prove access with a single benign read (or a write to a
   doc YOU created). **Never dump, enumerate, or exfiltrate real user data** — that's a privacy
   violation that voids safe harbor. On a hit: capture proof of *access*, STOP, report.
3. **Never write to / overwrite / delete anyone else's data.** To prove write access, create your own
   throwaway doc/key with an obvious marker (e.g. `bugbounty_treyky_test`), then delete it.
4. **Check the program page BEFORE testing:** is it PAID or VDP? Are "mobile apps" / the web app / the
   backend / `*.firebaseio.com` in scope? Any DoS/automated-scan exclusions? Add `h1-treyky` (or the
   platform equivalent) to your User-Agent.
5. **Respect rate limits.** OpenFirebase and manual probes = a handful of requests, not a scan storm.

## Target selection (where this actually hits)
Favor targets that (a) ship a **mobile app** (APK = trivial Firebase-config extraction) or a JS-heavy
web app, and (b) are **less picked-over**:
- HackerOne / Bugcrowd / Intigriti / YesWeHack programs with **Android app in scope**.
- Newer programs, recent scope additions, smaller companies, non-security-vendor products.
- Startups / fintech / social / IoT companies app — teams that shipped fast on Firebase.
- **Skip** the hyper-mature targets (big tech, exchanges like Exodus) — they lock rules down.
- Prefer **paid** for money; VDPs are fine for building signal as a newbie.
Finding them: on HackerOne, filter Directory by "Mobile" asset type / bounty; grab the Play Store /
APK. Google-dork: `site:*.firebaseio.com`, or search program scopes for `firebase`.

## Tooling (install on the VM — non-root user)
```
# OpenFirebase — automated extract + rules check (APK/IPA/web)
pipx install openfirebase   # or: git clone https://github.com/Icex0/OpenFirebase && pip install -r requirements.txt
# APK acquisition + decompile
sudo apt -y install apktool jadx  # jadx for reading decompiled code
# (APKs: from the vendor's site, APKMirror/APKPure for a public build, or the Play Store via your device)
```

## Workflow (batch it — it's a numbers game)
1. Pick 5–10 authorized, in-scope programs with Android apps.
2. For each: get the APK → run `openfirebase --apk app.apk` (extracts config + checks
   RTDB/Firestore/Storage/RemoteConfig/CloudFunctions read+write, flags service-account keys).
   - Manual fallback: `apktool d app.apk`, then `grep -rniE "firebaseio|firebaseapp|appspot|google-services|databaseURL|apiKey" .`
3. Triage OpenFirebase's hits. For anything flagged, **manually confirm minimally** (below), then
   STOP and write it up. Don't over-test.

## Manual probe reference (generalized from the Exodus briefs)
Given `PROJECT`, `APIKEY`, `BUCKET=PROJECT.appspot.com`:
```
# RTDB open read
curl -s -A "h1-treyky" "https://PROJECT.firebaseio.com/.json?limitToFirst=1&print=pretty"
#  -> data = OPEN (flag). {"error":"Permission denied"} = locked.

# RTDB open WRITE (only to a self-marked path; delete after)
curl -s -A "h1-treyky" -X PUT -d '{"t":"bugbounty_treyky_test"}' "https://PROJECT.firebaseio.com/bugbounty_treyky_test.json"
#  then DELETE: curl -X DELETE "https://PROJECT.firebaseio.com/bugbounty_treyky_test.json"

# Firestore per-collection read (needs a real collection name from the client code)
curl -s -A "h1-treyky" "https://firestore.googleapis.com/v1/projects/PROJECT/databases/(default)/documents/<collection>?pageSize=1"
#  200 w/ docs = readable. 403 PERMISSION_DENIED = locked. (Use a FAKE doc id to test rules w/o real data.)

# Storage bucket list
curl -s -A "h1-treyky" "https://firebasestorage.googleapis.com/v0/b/BUCKET/o?maxResults=1"
curl -s -A "h1-treyky" "https://storage.googleapis.com/BUCKET/"

# Anonymous auth enabled? (only matters combined with auth!=null rules)
curl -s -A "h1-treyky" -X POST "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=APIKEY" -H "Content-Type: application/json" -d '{"returnSecureToken":true}'

# Remote Config (can leak feature flags / secrets)
curl -s -A "h1-treyky" -X POST "https://firebaseremoteconfig.googleapis.com/v1/projects/PROJECT/namespaces/firebase:fetch?key=APIKEY" -H "Content-Type: application/json" -d '{"appInstanceId":"test"}'
```

## Severity guide (what each hit is worth)
- **Open Firestore/RTDB READ of user data** → High/Critical (PII/data breach; severity scales with data sensitivity).
- **Open WRITE** → Critical (integrity: tamper other users' data / escalate).
- **Hardcoded service-account key** (private key JSON in the client) → Critical (full admin).
- **Open Storage read/write** → High/Critical depending on contents.
- **Anonymous auth enabled** alone → informational UNLESS rules gate on `auth != null` (then it's the
  bypass — combine and it's High/Crit). (This is the exact thing Exodus had but their rules were
  ownership-gated, so it was inert.)
- **Remote Config leaking secrets** → Medium/High.

## Reporting
Reuse the capstone/report format in `../exodus_h1/REPORT-1-*.md`. Include: the exact APK/web source
the config came from, the minimal proof-of-access request/response (redact any real data you
incidentally saw), impact, and remediation (set proper security rules / rotate any leaked SA key).
One report per project/finding. Non-DoS → good for signal.

## Why this beats grinding a hardened target
Exodus taught us the ceiling of a locked target. This playbook is a repeatable funnel: run it across
many authorized programs, most are locked (fast dead-ends), but the hit rate on smaller/newer apps is
real — and each hit is a clean, non-DoS High/Critical that builds reputation and pays.
