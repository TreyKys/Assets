# VM BRIEF — Bank J.Van Breda & C° — Track B: Conversations-XSS escalation (no-account paths)

**Purpose:** the Track-A2 static analysis proved a client-side HTML/JS-injection sink in the
Conversations WebView (see `vm-results/02-deep-mobile-analysis.md`), and the first submission (self-XSS
PoC) was closed as OOS ("Self-XSS that cannot be used to exploit other users"). Escalation to the
cross-user case has been blocked because the eligibility wall on account creation (Belgian
self-employed) means we cannot send a payload from an authenticated session.

This brief pursues **four escalation angles that DO NOT need a live account**. Each either turns the
finding into architectural cross-user proof from the client code we already have, or identifies an
unauthenticated intake surface that reaches the same server-side render pipeline.

**Nothing in this brief touches Bank Van Breda's live banking infrastructure.** Tasks 1–3 are pure
grep/read of the decompiled DLLs Track A2 already extracted. Task 4 is GET-only fetches of the two
public marketing sites, ≤1 req/sec, no form submissions.

## Scope (STRICT — do not deviate)

- Tasks 1–3 (static): read only from the DLLs already on the VM under
  `~/bvb_apks/extracted/` (or wherever Track A2 landed the `pyxamstore`-decompressed assemblies).
  If the extraction directory is missing, re-run the Track A2 extraction steps first — do **not**
  re-download APKs unless the current ones are gone.
- Task 4 (recon): ONLY `https://www.bankvanbreda.be/*` and `https://www.bankdekremer.be/*`.
  **GET only**, `User-Agent: Mozilla/5.0 (compatible; security-research)`, ≤1 req/sec,
  no form submissions, no POSTs, no crawling beyond depth 2 from each root.
- **OUT OF SCOPE — DO NOT TOUCH:**
  - `login.bankvanbreda.be`, `xs2a-api-web.bankvanbreda.be`, `wero.bankvanbreda.be`, any
    subdomain that authenticates a real user
  - Any host that isn't the two `www.*.be` marketing sites
  - Any live banking API (the mobile app's server endpoints are not to be probed from the VM)

## Prerequisites
- Python 3.8+ (stdlib only for parsing / grepping)
- `dotnet-sdk-8.0` + `ilspycmd` (already installed on the VM from Track A2) if any DLL needs a
  re-decompile pass
- `curl`, `xmllint` for Task 4

## Tasks

### Task 1 — `SenderFullName` provenance and customer control (the strongest lead)

**Question this task settles:** is `SenderFullName` a customer-editable value on the sender side,
such that a customer can set their own display name to an XSS payload and any staff or third party
who opens a conversation from that customer sees the payload rendered raw?

**Prior finding to build on:** Track A2 confirmed `HTMLHelper.GetHTMLChatMessageSource(msg)`
interpolates `{msg.SenderFullName}` raw (no encoding) into the HTML string bound to the WebView.

**Steps:**

1. In `BVB.EOS.OnlineBanking.UI.Mobile.dll` (and any `.Model.dll` / `.Contracts.dll` sibling),
   grep for the type definition of the Message DTO carrying `SenderFullName`. Note whether
   the property is:
   - client-set on send (attacker directly controls the string), OR
   - server-set at delivery time (populated from an identity record the customer might edit
     elsewhere).
2. Find the code path that populates `SenderFullName` on OUTGOING messages —
   `Services/Server/Communication.cs` `AddMessage` / `CreateConversation` / `SendMessage`. Does
   the client send SenderFullName as part of the DTO, or does the server compose it from the
   authenticated session identity?
3. Regardless of #2, find every **customer-editable profile field** and its API contract:
   - Look for `UpdateProfile`, `UpdateUser`, `UpdatePersonalData`, `EditProfile`, `ProfileVM`,
     `MyDetailsVM`, `PersonalDataVM`, or similar view-models and their `Update*` service calls
   - For each, list: the DTO name, the fields (JSON property names), and note whether any field
     is a "display name / full name / preferred name / signature / greeting" that would plausibly
     feed into SenderFullName rendering
4. Then trace the RECEIVE side: search for every string interpolation of `.SenderFullName`,
   `.SenderName`, `.DisplayName`, `.FullName`, `.Signature`, `.Greeting`, `.From`,
   `.CorrespondentName` in every `.cs` file under the decompiled `BVB.*.Mobile.*` assemblies.
   For each hit, note:
   - the file + line
   - whether the interpolation is HTML-encoded (via `HtmlEncoder`, `HttpUtility.HtmlEncode`,
     `WebUtility.HtmlEncode`, `System.Web.Security.AntiXss`) or raw
   - the render context (WebView.Html property? label text? plain text log?)
5. **Bonus:** the Track A2 note flagged `AllowFileAccessFromFileURLs=true` and the `jsBridge`
   native interface. If the raw sink includes `<span>{msg.SenderFullName}</span>` inside a
   `<script>` tag or a JS string, note that separately — that's a script-context injection which
   is significantly worse than HTML-body context.

**Deliverable — section in `03-xss-escalation.md`:**
- **Verdict:** one of {`customer-editable → cross-user XSS provable architecturally`,
  `server-derived only → SenderFullName path closes here`, `partial — customer edits sender-side
  data that server merges into SenderFullName`}
- Evidence: exact file:line for every relevant sink and source
- If verdict is the first: draft a 4–5-line attack sequence explaining who does what to whom

### Task 2 — `templateMergeContent` and bank-authored template render path

**Question this task settles:** does a bank-authored message template ever merge a
customer-influenced value (transaction counterparty, standing-order description, IBAN memo,
custom notification name) into a message body that then renders through the same unsanitized
HTMLHelper path?

**Prior finding to build on:** Track A2 flagged that the Message DTO carries a server-set
`templateMergeContent` field but did not trace what merges into it.

**Steps:**

1. Grep for `templateMergeContent`, `TemplateMergeContent`, `MergeContent`, `Template.Merge`,
   `RenderTemplate` across the assemblies. Note every write-site (where the field is populated).
2. For each write-site, trace backwards to find WHERE the merged value comes from. Common sinks
   to look for:
   - `Transaction.CounterpartyName`, `Transaction.CommunicationText`, `Transaction.Reference`,
     `Transaction.Memo`, `Transaction.RemittanceInformation`
   - `StandingOrder.Description`, `StandingOrder.Name`, `StandingOrder.Beneficiary`
   - `Beneficiary.Name`, `Beneficiary.CustomLabel`
   - `Notification.Title`, `Notification.Body`, `UserDefinedNotification.*`
     (`CreateUserDefinedNotificationDto` was flagged in the submission)
   - `Card.NicknameCustom`, `Account.CustomLabel`
3. For each merged value, note whether the customer can set it via a self-service API call
   (find the corresponding `Update*` or `Create*` service method) and whether the SET path
   applies any encoding/sanitization (grep for `HtmlEncode`, `Regex.Replace`, `Sanitize`).
4. Trace forward from `templateMergeContent` to the HTML render — does the templated message
   go through `HTMLHelper.GetHTMLChatMessageSource` / `GetHTMLFullScreenMessageSource` or a
   sibling? Or a different, sanitized renderer?
5. Enumerate the receiver of these bank-authored templates: is it always the customer who
   triggered the transaction (self-loop), or can a template addressed to `OLBUSER` receiver
   type carry customer-influenced content to a *different* customer / advisor?

**Deliverable:**
- **Verdict:** one of {`cross-user path via customer-controllable X`, `no customer-controllable
  value reaches templateMergeContent`, `path exists but a sanitizer breaks the chain at Y`}
- Evidence: file:line for every source, sink, and (if present) sanitizer
- If verdict is the first: 4–5-line attack sequence

### Task 3 — Every other customer-editable field → WebView sink

Broader sweep to catch anything Tasks 1 & 2 don't cover. This is where the "unknown unknowns" live.

**Steps:**

1. Enumerate every C# type used as a *send-side* DTO from the mobile client. Grep for
   `class *Dto`, `class *Request`, `class *Contract` in the decompiled sources, and for each
   note which string properties it carries.
2. For each such property, note whether:
   - it round-trips into a subsequent read (look for the corresponding response DTO)
   - the response DTO's field is ever interpolated raw into an HTML template
     (search `.cs` for `${` / `{propertyName}` in a string that also contains `<html`,
     `<body`, `<script`, `<img`, `<div`, `WebView`, `.Html =`, `.Source =`, `.HtmlSource`,
     `LoadHtml`)
3. Prioritize properties that look meant for humans (names, labels, descriptions, memos,
   references, remarks, comments) over IDs/GUIDs/numbers.
4. Cross-reference with the receiver-type enum values (`OLBUSER`, `EMPLOYEE`, `BRANCH`,
   `HELPDESK`) — anything customer-authored that a `EMPLOYEE`/`BRANCH`/`HELPDESK` role will
   see rendered through an HTML pipeline is a cross-user candidate.

**Deliverable:**
- Table: `dto_field × set-side-encoding × render-side-encoding × who-sees-it × cross-user?`
- Top-3 highest-EV candidates called out with a 2–3-line attack sketch each

### Task 4 — Public unauth intake forms on the marketing sites

**Question this task settles:** does any form on `www.bankvanbreda.be` or `www.bankdekremer.be`
funnel customer-typed text into the same helpdesk/Conversations backend that renders unsanitized
in the mobile app?

**Steps (GET-only, no submissions):**

1. `curl -sSL https://www.bankvanbreda.be/robots.txt` and `https://www.bankvanbreda.be/sitemap.xml`
   (and the `bankdekremer.be` equivalents) — enumerate paths.
2. Fetch the home page + every path from sitemap that has "contact", "complaint", "klacht"
   (nl), "plainte" (fr), "vraag", "hulp", "callback", "feedback", "meldung", "message" in the
   URL or title. Save each to `~/bvb-recon/`. Depth ≤2 from each root.
3. For each form discovered, extract:
   - form `action` URL and method
   - every input field (name, type, maxlength)
   - the destination hostname (does it post to a bank-internal endpoint or a third-party form
     handler like HubSpot / Salesforce / Zendesk?)
4. For each form, hypothesize the backend: does the destination look like it feeds into the
   same helpdesk queue that Conversations reads from? Evidence:
   - subdomain patterns (`crm.`, `helpdesk.`, `support.`, `contact.`)
   - JS bundles that reference the same API base URL the mobile app uses
   - a data-flow hint in comments / hidden fields
5. Note whether any form's HTML page renders back the submitted content (some sites show a
   confirmation page echoing the user's message — that's a self-XSS surface at minimum but
   might also indicate the same render pipeline).

**Deliverable:**
- Table: `page_url × form_action × destination_host × field_list × likely_backend`
- Top-2 "worth actively testing" forms called out (with a note on which fields would receive
  the payload if we ever did submit — we are NOT submitting from this brief)

## Deliverables

Commit to `intigriti/bank_van_breda/vm-results/`:
- `03-xss-escalation.md` — the four task writeups + a headline verdict
- `03-xss-escalation-evidence/` — copies of relevant decompiled `.cs` snippets (with line
  numbers) that support each verdict, so the researcher can quote them into the appeal without
  re-running the extraction
- `03-recon-forms/` — the raw HTML of the marketing-site forms for Task 4

Commit each file as it's produced; don't wait for the whole brief.

## Headline verdict format (top of `03-xss-escalation.md`)

Fill in one of:
- **STRONG** — Task 1 or 2 landed a cross-user path with clear architectural evidence. The
  appeal should quote the file:line evidence and re-frame the finding as cross-user stored XSS.
- **PARTIAL** — no full cross-user chain, but a plausible one gated by a server-side behavior
  we cannot observe. Appeal should re-request test credentials citing this specific chain.
- **NULL** — every no-account path closes cleanly. Appeal path is exhausted; move on.

## Non-goals

- No live requests to the bank's authenticated infrastructure
- No form submissions on the marketing sites (recon only)
- No re-testing of the Track A2 payment-deep-link Wero/XS2A conclusion (it's settled)
- No new decompilation unless a specific file needed for a task can't be read as-is
