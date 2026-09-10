# VM BRIEF — Bank J.Van Breda (Intigriti) — Track A2: deep mobile static + local-device analysis

Extends Track A (`VM-BRIEF-track-a-mobile-config.md`, run that first if not already done). Still
**no live bank server contact** — everything here is APK static analysis + a device/emulator we
control. Rules from Track A apply unchanged (real bank, be conservative, @intigriti.me for any test
account, no touching `secure.*`/`web-xs2a.*` yet, commit to `intigriti/bank_van_breda/vm-results/`).

## OUT OF SCOPE per program policy — do NOT spend time on these
Absence of certificate pinning; lack of jailbreak/root detection; lack of obfuscation; lack of
anti-debugging/binary protection/SSL pinning; exploits only possible in a jailbroken environment;
crashes from malformed URL schemes. Zero payout for any of these — skip entirely.

## Note on rooting/Frida as a tool
Using a rooted emulator or Frida to research the app is fine. The exclusion only applies if the
**resulting vulnerability itself** only works on a rooted device. If a bug you find with root's help
is also exploitable on a stock, non-rooted phone, it's in scope. Always ask: "would this work on my
mom's normal phone?" — if yes, it counts.

## Task 1 — AndroidManifest.xml audit (both apps)
```
cd ~/bvb_apks
for apk in bankvanbreda bankdekremer; do
  echo "=== $apk manifest ==="
  cat ${apk}_decompiled/AndroidManifest.xml | grep -A2 -iE 'exported="true"|<activity|<service|<receiver|<provider|allowBackup|debuggable|android:scheme|<intent-filter'
done
```
Look for:
- `android:exported="true"` on activities/services/receivers **without** a matching
  `android:permission` — candidate for unauthorized local invocation.
- `android:allowBackup="true"` with no `fullBackupContent`/`dataExtractionRules` restricting
  sensitive data — candidate for `adb backup` data extraction.
- `android:debuggable` set true in a release build (shouldn't be, but check).
- Custom `<data android:scheme="...">` deep link definitions — note every custom scheme + host.

## Task 2 — exported component local testing (emulator/test device, NOT bank servers)
Install the APK on an emulator or your own rooted test device (`adb install`). For every exported
activity found in Task 1:
```
adb shell am start -n <package>/<activity-name>
```
Does it land you on an authenticated screen, a settings page, or anything that should require login?
Note the exact component + what it exposes. For exported services/receivers, check if they accept
Intent extras that trigger a sensitive action (test with your OWN test account only, never touch
data that isn't yours).

## Task 3 — WebView JS-bridge audit
```
for apk in bankvanbreda bankdekremer; do
  echo "=== $apk WebView bridges ==="
  grep -rn "addJavascriptInterface" ${apk}_decompiled --include=*.smali -A3
  grep -rn "setJavaScriptEnabled(true)\|WebSettings" ${apk}_decompiled --include=*.smali | head -20
  grep -rn "loadUrl\|loadDataWithBaseURL" ${apk}_decompiled --include=*.smali | head -20
done
```
For any `addJavascriptInterface` found: what native methods does it expose to the web content? What
URL(s) does that WebView actually load — a fixed bank-controlled page, or something that could ever
be influenced by external/attacker data (a deep link param, a QR code, a pushed URL)? If the WebView
only ever loads the bank's own fixed pages, this is likely a dead end — say so.

## Task 4 — local data-at-rest review (your own test account's data only)
If `allowBackup="true"` (from Task 1):
```
adb backup -f bvb_backup.ab <package>
# convert with android-backup-extractor or similar, then inspect
```
Or on a rooted emulator, pull the app's data dir directly:
```
adb shell "run-as <package> tar cf - /data/data/<package>" > appdata.tar
```
Inspect SharedPreferences XML, SQLite DBs, and cache files for: session tokens, account numbers,
balances, PINs, or auth credentials stored in plaintext or weakly obfuscated (e.g., base64 only).
Only ever do this against YOUR OWN test account's data.

## Task 5 — deep link logic review
For each custom scheme found in Task 1, trace in the decompiled code what the receiving
activity/intent-filter actually DOES with the URI's parameters. Specifically: can a deep link
pre-fill a payment recipient/amount, link an account, or perform any state-changing action using
attacker-supplied parameters? (Not "does it crash" — that's excluded — but "does it do something
security-relevant with untrusted input.") This mirrors the Exodus `exodus://fiatOnramp` pattern.

## Task 6 — auth/session code review (jadx source, not just grep)
Read (don't just grep) the login/session-handling classes: how is the session token stored after
login, how is it attached to outgoing API requests, and — critically — does any API call let the
**client** specify which account/customer ID to fetch, rather than the server deriving it purely
from the authenticated session? Any client-suppliable account/customer identifier is the strongest
lead for Track B's IDOR hunt once we have credentials — flag exactly which endpoints do this.

## Output
`intigriti/bank_van_breda/vm-results/02-deep-mobile-analysis.md`: findings per task, per app.
Redact/truncate any real secret values found (note type + location, don't paste the raw secret into
the committed report). Flag anything from Task 6 clearly — that directly sets up Track B.
