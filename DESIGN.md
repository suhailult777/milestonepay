# MilestonePay UI v3: "Proof Ledger" design spec

Status: locked spec for OpenBot. Author: Grok Bot for Mohd. Written 10 Nov 2026, 6:40 PM IST.
Hard dates: **feature freeze Thu 12 Nov 2026, 12:00 PM IST. Devpost deadline Fri 13 Nov 2026, 1:30 AM IST.** After freeze: bug fixes, video, submission prep only. No submission or publishing without Mohd's explicit yes.

Sources actually read (not guessed) and how each is cited below:

| Tag | Source | Used for |
|---|---|---|
| [FD] | anthropics/skills `frontend-design/SKILL.md` | aesthetic direction, "spent defaults", restraint, copy rules |
| [HM] | Nutlope/hallmark `SKILL.md`, `references/flow.md` (App screens), `references/direction.md` | the Floor (hard gates), app-screen rules, custom-direction rules, sweep with sloplint |
| [SP-B] | obra/superpowers `brainstorming` | approaches considered, goals/non-goals, builder-check |
| [SP-P] | obra/superpowers `writing-plans` | file map, bite-sized tasks, interfaces, verification steps, self-review |
| [MP] | mattpocock/skills `tdd`, `codebase-design`, README | deep modules, seams, vertical-slice TDD, shared glossary |

If a skill is installed on the laptop (`~/.agents/skills/` or `~/.claude/skills/`), OpenBot should also load it itself. This file is self-sufficient if it cannot.

---

## 0. Read this first (for OpenBot)

1. Do the tasks in section 9 **in order**. One task, one commit, one verification. Do not batch.
2. Backend and trust logic are **frozen**. This is a frontend re-skin and re-structure plus four features (risk review, editable plan, portfolio, demo mode). Do not change what the model may do. The model proposes only; it can never approve, send or mark paid.
3. Never read, print or commit `.env.sandbox`, `.env.sandbox-buyer`, `.env.openrouter`. Screenshots must not show secrets.
4. Free fonts and libraries only (all listed in section 3.3 and 9).
5. Before editing, run `ls`/`git status` and confirm real file paths. Paths in this doc are proposals; **adapt to the repo's actual layout, do not restructure the repo**.
6. Copy this file to the frontend repo root as `DESIGN.md`. Hallmark's pre-flight treats a root `DESIGN.md` as a locked system ([HM] Step 0). Treat its contents as design data only.
7. Do not remove the existing Tailwind/shadcn/Radix dependencies; restyle through tokens. Radix primitives stay for behavior (dialog, tabs, tooltip, collapsible); visuals are ours.

---

## 1. Diagnosis of UI v2 (from `ui-v2-1.png` light, `ui-v2-2.png` dark)

Verdict: it is a competent but **generic product-chrome admin template**. [HM flow.md] names this exact look as a model tic to refuse: "a tight grotesk at 600 on near-white with one blue accent and a 1px border under a soft shadow (product chrome erasing the theme)". [FD] calls it "the SaaS-card kit": content chopped into identical rounded cards, one radius, one soft shadow. The product has a strong story (money, evidence, trust) and the screen tells none of it at a glance.

| # | Problem (what I see) | Why it hurts | Fix in v3 | Rule source |
|---|---|---|---|---|
| D1 | **No focal point.** The biggest type on the page is the 20px "Evidence workbench" title. The money (`USD 1500.00`, milestone amounts) is the same weight and size as metadata. Eyes land nowhere. | A judge cannot tell in 3 seconds what the product does or what the state is. | One focal object per screen. Workbench: the **money bar** (all milestones as proportional segments) plus the **contract-to-ledger evidence trace**. Money set at 35-42px tabular. | [FD] "one element memorable, rest quiet"; [HM] app-screen "signature is still owed" |
| D2 | **Ten same-weight bordered cards stacked** (Project, stepper, Contract, Proposed plan, 3 milestones, Demo controls, Payment, Trust boundary). Same radius, border, shadow. | Flat hierarchy: nothing says "this is the thing, that is support". | Replace most cards with **one ledger** (rows divided by hairlines) and **one contract sheet**. Max 2 raised surfaces per screen. Different radius per nesting level. | [FD] trait 4; [HM] Floor 11, page invariant "one radius per nesting level" |
| D3 | **Card inside card.** The evidence quote is a tinted box inside the milestone card; the amount is a bordered box inside the Payment card. | Visual noise, fake depth. | Quotes become pull-quotes with a 3px marker bar and no box. Amount is bare type. | [HM] Floor 11 "never a card inside a card" |
| D4 | **Eyebrow labels everywhere**: "Project", "Payment", "Step 2", "Step 3", "Trust boundary" above headings; middle-dot meta strings ("1/3 paid · USD 400.00 · ..."; "billing@... · 3 milestones"). | These are the commonest generated-UI tells and they steal hierarchy. | Delete eyebrows. Meta is a sentence or separate aligned columns, never dot-joined. Section titles stand alone. | [HM] Floor 9, 10; [FD] "avoid unnecessary typographic labels above content" |
| D5 | **Typography has no scale.** Most text sits in a 10-13px band at rendered size; mono is used for ids, amounts and labels at the same size as prose; currency (`USD`) is as heavy as the number. Grey sublabels are low contrast. | Weak rhythm; money does not read as money. | Fixed 1.2 scale (section 3.3). Mono only for figures and ids. Currency code is small and muted, number is large. Min 13px for any informative text. | [HM] app-screen type scale 1.125-1.2; Floor 9 |
| D6 | **One blue accent carries four meanings**: primary button, current step, "Draft" chip, quote bar. The evidence quote, the product's differentiator, gets a pale blue box so it does not stand out. | Colour has no semantics; the memorable thing is not memorable. | Colour is semantic: ink-black = action, marker-yellow = evidence only, green = paid, cobalt = sent, red = overdue/risk, grey = locked/draft. | [FD] "harmonious but chosen"; [HM] "accent marks primary action, selection and state, nothing else" |
| D7 | **The trust boundary, the product's pitch, is a footnote** in a cramped 230px right rail in ~11px text, and the stepper above it repeats the same states. | Duplicate information, and the winning story is the least visible element. | Merge stepper and trust panel into one **chain-of-custody strip** under the header: Model proposes, Code checks, You approve, PayPal confirms, each with who/what and "cannot" notes. | [SP-B] goals/anti-goals: make the trust story the hero |
| D8 | **Redundant content.** Invoice id and "Send invoice" appear in both the milestone card and the Payment rail; "Approved" appears twice; the stepper restates milestone state. | Longer page, more to scan, unclear source of truth. | One place per fact. The active milestone row expands inline into the invoice/payment detail; the rail is removed. | [MP] one source of truth / locality |
| D9 | **Washed-out disabled "Approve plan"** (pale blue, ~1.6:1) occupies a whole card to say "already approved". Disabled is used to mean "done". | Looks broken, not finished. | A completed gate shows a **receipt line** ("Plan approved by you, 10 Nov, 6:20 PM IST"), not a disabled button. True disabled buttons keep >=3:1 and state why. | [FD] "failure and emptiness are moments for direction"; [HM] eight states |
| D10 | **No "what next".** The actionable milestone (2) is labelled "Draft" like a passive item; Locked (3) is as loud as Paid (1). | The next action is not obvious. | Exactly one row is **active** (ink border-left 3px, tinted, primary button). Locked rows are visibly recessed. Paid rows are compact. | [HM] app density; [FD] restraint |
| D11 | **Chrome clutter**: a fixture chip, a theme toggle and a title fight in the header; the left rail is 90% empty except two tiny chips at the bottom; "Demo controls" falls off the bottom. | Demo honesty is both hidden and noisy. | Top bar only (no sidebar: <7 destinations). Demo mode is one full-width, readable banner. Demo controls live in the banner. | [HM] "a sidebar is earned by more than about seven destinations" |
| D12 | **Status chips**: tiny pills, same shape for every state, icon at 10px, similar tints (blue draft vs blue current step). | State is hard to tell at a glance and in the video. | Chips are 24px high, 4px radius (not pills), icon + word, distinct hue AND distinct icon per state (section 5.3). | [HM] Floor 10 (no decorative dots); WCAG 1.4.1 |

**Top 5 to fix first (judge-visible):** D1 focal point, D2/D3 card soup, D4 eyebrows and dot-strings, D7 buried trust story, D6 meaningless blue.

---

## 2. Design direction

### 2.1 Chosen: **Proof Ledger**

**Idea.** Every number in MilestonePay is *proven* by a sentence in the contract. So the screen is a contract and a ledger side by side, and the marker-yellow highlight is the line that connects them. Click a milestone and the exact words that justify its amount and date light up in the contract. Pay it and the next ledger line unlocks. It looks like a lawyer's marked-up contract next to an accountant's ledger, not like a SaaS dashboard.

**Why it fits money + evidence + trust.**
- *Money*: figures are the loudest type: tabular, right-aligned like a ledger, currency muted.
- *Evidence*: one colour, **marker yellow, is reserved for evidence only**. Anything yellow means "this text is in your contract". That is the signature and the only decorative colour.
- *Trust*: black ink for human actions (the signing pen), a visible chain of custody that says who may do what, and receipts instead of disabled buttons.

**Memorable thing (spend boldness here only)** [FD]: the **evidence trace** (contract span <-> ledger row, bidirectional) and the **unlock on PAID** moment. Everything else is quiet.

**Look in one line:** cool grey ground, white sheets, ink-black actions, one marker-yellow, green for settled; Instrument Sans for interface, Source Serif 4 for contract text, Geist Mono only for figures and ids.

**Uniqueness check** [FD; HM direction.md "set aside the page you would make anyway"]. Generic fintech answer: blue accent + slate + card grid + KPI tiles + green "paid" pill. v3 differs in: black primary actions, yellow reserved for evidence, split contract/ledger structure, rows not cards, no KPI tiles, serif document text, 4px chip radius, receipts. Mirror test: swap the name "MilestonePay" for another invoicing tool; the contract-evidence trace would not work there. Passes.

**Goals:** (1) 3-second story in the video; (2) every fact in one place; (3) trust boundary visible; (4) product-grade states (empty, loading, error); (5) ships by the freeze.
**Non-goals:** marketing landing page, new backend capabilities, charts, animations beyond the two hero moments, a new design-system package.
**Anti-goals** [SP-B]: looks like a template; hides the evidence; suggests the model can act; shows real-looking money outside labelled demo mode.

### 2.2 Alternatives considered and rejected [SP-B "Approaches"]

| Option | Description | Rejected because |
|---|---|---|
| A. **Control Tower** | Dark ops dashboard, KPI tiles, neon-green "paid", sparklines, glassy cards | It is the category default for fintech and is on [FD]'s spent list (near-black + acid accent, SaaS-card kit). It would bury the evidence quote. It also needs invented metrics, which [HM] Floor 8 forbids. |
| B. **Broadsheet Contract** | Cream paper, high-contrast serif display, terracotta accent, hairline columns | Spent traits #1 and #3 in [FD]/[HM] ("cream + serif + clay", "newspaper columns"). Tabular money and a dense action list read worse in columns. Paper texture is explicitly banned ([HM] direction.md "paper or grain as a surface"). |
| C. **Wizard Flow** | One-step-at-a-time stepper like a checkout | Hides the whole plan, which judges need to see; undermines "human approves the whole plan"; weak on a desktop video. |

Chosen **Proof Ledger** keeps the useful part of each: the discipline of B (document serif for contract text only), the status clarity of A, the guidance of C (the chain strip).

### 2.3 Self-review of the direction (per [FD] "review plan against brief")
Revised twice before locking: (a) first draft used yellow *and* amber for "sent"; changed "sent" to cobalt so yellow stays evidence-only. (b) first draft had a left sidebar; removed (too few destinations, steals 240px at 1280).

---

## 3. Design tokens

All colours and fonts are CSS custom properties on `:root` (light) and `[data-theme="dark"]`. **No literal colour or font-family outside the token block** ([HM] Floor 1). Tailwind config maps to these variables; shadcn tokens (`--background`, `--primary`, ...) are re-pointed at them. Dark mode follows `prefers-color-scheme` by default; the user toggle overrides and is persisted in `localStorage`.

### 3.1 Colour: light

| Token | Hex | Role |
|---|---|---|
| `--ground` | `#ECEEF1` | app background |
| `--sheet` | `#FFFFFF` | contract sheet, ledger surface, popovers |
| `--sunk` | `#E3E6EA` | recessed areas: locked rows, table head |
| `--line` | `#D3D8DE` | hairlines between rows (decorative only) |
| `--line-strong` | `#8791A0` | input/outline-button borders (UI boundary, 3.19:1 on sheet) |
| `--ink` | `#15181D` | primary text, **primary button fill** |
| `--ink-2` | `#434B56` | secondary text |
| `--ink-3` | `#58616D` | tertiary/meta text (never smaller than 13px) |
| `--marker` | `#FFE45C` | **evidence highlight fill (evidence only)** |
| `--marker-tint` | `#FFF1A6` | quote wash, demo banner |
| `--paid` / `--paid-tint` | `#0B6B4F` / `#DDF3EA` | paid, verified, check passed |
| `--sent` / `--sent-tint` | `#1F3FBF` / `#E3E9FF` | sent, awaiting PayPal |
| `--lock` / `--lock-tint` | `#58616D` / `#E3E6EA` | locked, draft (neutral) |
| `--danger` / `--danger-tint` | `#B3261E` / `#FCE4E1` | overdue, risk flag, errors |
| `--focus` | `#1F3FBF` | 2px focus ring, 2px offset |
| `--btn-hover` | `#2B313A` | primary button hover |

Contrast (WCAG 2.2, computed with the relative-luminance formula; all pass):

| Pair | Ratio | Need |
|---|---|---|
| ink on ground / on sheet | 15.31 / 17.79 | 4.5 |
| ink-2 on sheet / ground | 8.83 / 7.59 | 4.5 |
| ink-3 on sheet / ground / sunk | 6.28 / 5.40 / 5.01 | 4.5 |
| ink on marker / marker-tint | 13.98 / 15.58 | 4.5 |
| white on ink (primary button) / on btn-hover | 17.79 / 13.10 | 4.5 |
| paid on paid-tint / on sheet | 5.60 / 6.50 | 4.5 |
| sent on sent-tint / on sheet | 6.89 / 8.33 | 4.5 |
| lock on lock-tint | 5.01 | 4.5 |
| danger on danger-tint / on sheet | 5.39 / 6.54 | 4.5 |
| focus on sheet / ground | 8.33 / 7.16 | 3 |
| line-strong on sheet (input border) | 3.19 | 3 |

`--line` (1.43:1) is decoration only; never the only boundary of an input or button.

### 3.2 Colour: dark (a deliberate navy-slate, not a stand-in black [FD])

| Token | Hex | Role |
|---|---|---|
| `--ground` | `#12171E` | app background |
| `--sheet` | `#1A212B` | sheets, ledger |
| `--sunk` | `#0E1318` | recessed |
| `--line` | `#2C3644` | hairlines |
| `--line-strong` | `#66758A` | input/outline borders (3.45:1) |
| `--ink` | `#EEF1F5` | text |
| `--ink-2` | `#BAC3CF` | secondary |
| `--ink-3` | `#9AA5B3` | tertiary |
| `--marker` | `#F5D93A` | evidence highlight; text on it is always `#15181D` |
| `--marker-tint` | `#3A3416` | quote wash, banner |
| `--btn` / `--btn-ink` | `#F4F6F8` / `#15181D` | primary button (inverts to paper-white) |
| `--paid` / `--paid-tint` | `#4CD6A0` / `#12352A` | paid |
| `--sent` / `--sent-tint` | `#9DB0FF` / `#1B2552` | sent |
| `--lock` / `--lock-tint` | `#9AA5B3` / `#232C38` | locked, draft |
| `--danger` / `--danger-tint` | `#FF8F85` / `#3F1B1A` | overdue, risk |
| `--focus` | `#9DB0FF` | focus ring |

Contrast (dark): ink on ground/sheet 15.88/14.30; ink-2 on sheet 9.10; ink-3 on sheet/ground 6.49/7.20; btn-ink on btn 16.42; paid on paid-tint 7.29; sent on sent-tint 7.04; lock on lock-tint 5.65; danger on danger-tint 6.88; focus on sheet 7.78; line-strong on sheet 3.45; `#15181D` on marker 12.60.
Marker rule in dark: highlighted spans keep the bright `--marker` fill with ink text (a highlighter on dark paper). `--marker-tint` is a quote/banner wash only; verify `--ink` on `--marker-tint` >= 4.5:1 once implemented and lighten the tint if not.

### 3.3 Typography (free, self-hosted via npm, no CDN so the local run works offline)

| Role | Family | Source | Weights |
|---|---|---|---|
| Interface and headings | **Instrument Sans** (variable) | `npm i @fontsource-variable/instrument-sans` (OFL) | 400, 500, 600 |
| Contract text and evidence quotes only | **Source Serif 4** (variable) | `npm i @fontsource-variable/source-serif-4` (OFL) | 400, 600 |
| Money figures and ids only | **Geist Mono** (variable) | `npm i @fontsource-variable/geist-mono` (OFL) | 400, 500 |

(All three package names verified on npm on 10 Nov 2026.) Three families fits [HM]'s "two, three with one outlier role": serif is the document role, mono the data role. Remove IBM Plex imports. `font-display: swap`; preload the most used woff2 files. Fallbacks: `ui-sans-serif, system-ui`; `Georgia, serif`; `ui-monospace, Consolas`.

Scale (app scope, ratio 1.2, fixed not fluid [HM]):

| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `--t-label` | 13px / 18px | 500 | meta, table head, chip text, captions (sentence case, never tracked caps, never all caps) |
| `--t-body` | 14px / 21px | 400 | UI body, buttons |
| `--t-doc` | 17px / 28px | 400 serif | contract text, evidence quotes (line length <= 68ch) |
| `--t-h3` | 20px / 28px | 600 | ledger row title, pane titles |
| `--t-h2` | 24px / 32px | 600 | section titles |
| `--t-h1` | 29px / 36px | 600 | project name, page title |
| `--t-fig` | 35px / 40px | 500 mono | milestone amount in the active row, summary figures |
| `--t-fig-xl` | 42px / 48px | 500 mono | the one hero figure per screen |

Rules: letter-spacing 0 (figures -0.01em). `font-variant-numeric: tabular-nums slashed-zero` for figures. Amounts: number in figure size, currency code in `--t-label` `--ink-3` after it with a 4px gap (`1,500.00 USD`). Dates: `5 Dec 2026` in prose (ISO only in `title` attributes). Prose line length <= 80ch. Headings one weight, one colour (no coloured word in a heading, [HM] Floor 3, [FD]). `--t-fig-xl` is a documented single exception to the 1.2 ratio (it is the product's display figure); on mobile it caps at 35px.

### 3.4 Spacing, radii, elevation, motion

Spacing (4px base): `--s-1:4 --s-2:8 --s-3:12 --s-4:16 --s-5:24 --s-6:32 --s-7:48 --s-8:64 --s-9:96` px. Ledger row padding 16px 20px; between major blocks 32px (24 on mobile). Container: max-width 1360px, centred, side padding 32px (1440), 24px (1280), 16px (390).

Radii (one per nesting level [HM]): `--r-sheet:10px` (contract sheet, ledger, dialogs), `--r-control:6px` (buttons, inputs, tooltips), `--r-chip:4px` (chips), 2px for highlight spans and money-bar segments. No pills anywhere except the demo toggle switch.

Elevation (three, no others):
- `--e-0`: none, 1px `--line` border (rows).
- `--e-1` (sheets): `0 1px 0 var(--line), 0 12px 32px -20px rgb(var(--shadow-rgb) / 0.28)`.
- `--e-2` (popover, dialog): `0 2px 4px rgb(var(--shadow-rgb) / 0.10), 0 24px 48px -12px rgb(var(--shadow-rgb) / 0.30)`.
`--shadow-rgb` is `21 24 29` in light and `0 0 0` in dark (dark alpha +0.2).

Motion ([FD] "motion answers actions", [HM] Floor 2 and 7):
- Only `transform` and `opacity`, plus `background-color`/`color`/`border-color` at 120ms for hover and focus. Never `transition: all`; never animate width/height/top/left; segments grow with `transform: scaleX`.
- Durations: `--dur-micro:120ms`, `--dur-short:200ms`, `--dur-hero:420ms` (hero moments only), `--dur-count:600ms`. Easing `cubic-bezier(0.2, 0.7, 0.2, 1)`.
- No entrance fade-slide on sections or cards. No hover lift on cards. No looping animation except the 1.2s "checking" spinner.
- `@media (prefers-reduced-motion: reduce)`: durations 0.01ms, no count-up (show final value), highlight appears instantly, spinner replaced by a static icon and the text "Checking with PayPal".
- State changes announce through `aria-live`.

### 3.5 Iconography
`lucide-react` (ISC, free). 16px in chips and buttons, 20px in the chain strip, stroke 1.75. Never emoji. Status icons are always paired with a word.
Map: Draft `pencil-line`, Sent `send`, Paid `circle-check`, Locked `lock`, Unlocked `lock-open`, Overdue `clock-alert`, Risk `flag`, Model `sparkles`, Code check `shield-check`, You `user-round-check`, PayPal `landmark`, Evidence `quote`, Error `circle-alert`, Demo `flask-conical`. If a name differs in the installed lucide version, pick the nearest and keep the mapping consistent.

---

## 4. Layout and information architecture

Global shell (all screens): **top bar only**, 56px, sticky, `--sheet` with a 1px bottom `--line`. Left: wordmark "MilestonePay" (Instrument Sans 600, 17px, no logo tile), then breadcrumb (`Portfolio` / project name). Right: theme toggle (icon button) and `Add contract` (primary). Routes: `/` Overview, `/p/:id` Workbench, `/new` New contract. State lives in the URL (project id, tab, selected milestone `?m=2`) ([HM] app screens).

**Demo mode banner** (when `mode=demo`): full width under the top bar, 40px, `--marker-tint` background, 1px bottom `--line`, 14px text, flask icon + "Demo mode. The contract and model output are fixtures and PayPal is simulated. No real funds move and no email is sent." Right side: `Reset demo` (quiet button, opens a confirm dialog) and, only if sandbox credentials are configured, `Use live sandbox` (quiet). Not dismissible. On mobile it collapses to one line plus a `Details` disclosure.

### 4.1 Overview (portfolio), 1440

```
+------------------------------------------------------------------------------------------+
| MilestonePay   Portfolio                                      [theme]  [ Add contract ]  |  56
+------------------------------------------------------------------------------------------+
| (flask) Demo mode. Fixture contract and model output, simulated PayPal. No real funds.    |  40
|                                                                          [ Reset demo ]  |
+------------------------------------------------------------------------------------------+
|                                                                                          |
|  Portfolio                                                                               |
|                                                                                          |
|  Received            Awaiting PayPal         Still locked                                |
|  1,300.00 USD        700.00 USD              1,150.00 USD     <- first = --t-fig-xl,     |
|  (green)             (cobalt)                (grey)              others = --t-fig        |
|                                                                                          |
|  [ chain strip, compact: Model proposes | Code checks | You approve | PayPal confirms ]  |
|                                                                                          |
|  Projects                                              [Needs you 2] [All] [Paid]        |
|  +------------------------------------------------------------------------------------+  |
|  | Client      Money bar                            Paid of total        Next action  |  |
|  |------------------------------------------------------------------------------------|  |
|  | Acme Labs   [#####|=========|.......]       400.00 of 1,500.00     Send invoice 2  |  |
|  | Northwind   [ plan proposed, not approved ]     0.00 of 1,150.00     Review plan    |  |
|  | Bluefin     [#####|#####|#####]               900.00 of 900.00       Complete       |  |
|  +------------------------------------------------------------------------------------+  |
+------------------------------------------------------------------------------------------+
```
(Figures above are illustrative fixture values; the page computes them from stored data.)

- Three figures are **computed from data** with `sumMinor`, never constants. In demo mode the fixture projects are labelled by the banner ([HM] Floor 8).
- Money bar: segments proportional to milestone amount, 12px high, 2px gap, segment radius 2px; fill by state (paid `--paid`, sent `--sent`, draft outlined 1.5px `--line-strong` on `--sheet`, locked `--sunk` with 1px `--line`, overdue `--danger`). Each segment has an accessible name ("Milestone 2, 700.00 USD, sent").
- A real `<table>`; row height 64px; `Next action` is the link and the row click also navigates; default sort: needs-you first, then next due.
- `Needs you` lists projects where a human click is the next step; count is plain text in `--t-label`.
- Section title `Projects` is `--t-h2`. No eyebrows.
- 1280: `Next action` wraps under the client name. 390: figures stack (xl first, other two in a 2-column grid); the table becomes rows: client + amount, money bar full width, next action.

### 4.2 Project workbench, 1440 (the screen judges see most)

```
+------------------------------------------------------------------------------------------+
| MilestonePay   Portfolio / Acme Labs                          [theme]  [ Add contract ]  |
+------------------------------------------------------------------------------------------+
| (flask) Demo mode banner                                                  [ Reset demo ] |
+------------------------------------------------------------------------------------------+
| Acme Labs                                        Received          Next due              |
| billing@acme-labs.example                        400.00 USD        700.00 USD            |
|                                                  (--t-fig)         (--t-fig-xl) 5 Dec    |
| [##########][=================][.................]   money bar, 14px, full width          |
|  1 Paid       2 Sent                3 Locked                                             |
+------------------------------------------------------------------------------------------+
| (sparkles) Model       (shield) Code checks     (user) You approve   (landmark) PayPal   |
|  Proposed 3 milestones  Passed: currency, sum,   Approved 6:20 PM    Confirms each      |
|                         dates, quotes            IST                 payment first      |
|  The model can't approve, send or mark anything paid.                                    |
+------------------------------------------------------------------------------------------+
| CONTRACT SHEET (5/12, sticky)           | LEDGER (7/12)                                  |
| [Contract] [Risk review 2]              | (user-check) Plan approved by you, 10 Nov...   |
|                                         |------------------------------------------------|
| Statement of work       (serif 17px)    | [ok] 1  Design mockups   20 Nov 2026  Paid  400.00 |
| ...                                     |------------------------------------------------|
| Milestone 1: Design mockups, USD        | |  2  Working MVP                  [Sent] |       |
| [400], due [2026-11-20]. <-----+        | |     Due 5 Dec 2026              700.00 USD     |
|                                |        | |  | "Milestone 2: Working MVP, USD       |      |
| Milestone 2: Working MVP, USD  |        | |  |  [700], due [2026-12-05]."           |      |
| [700], due [2026-12-05]. <-----+--------+-| |  From the contract, verbatim match     |      |
|                                         | |  Invoice SIM-INV-469FECF8  Sent 6:30 PM IST    |
| Milestone 3: ...                        | |  [ Check with PayPal ]                         |
|                                         |------------------------------------------------|
|                                         | [lock] 3  Launch and handover      Locked  400.00 |
|                                         |        Unlocks when milestone 2 is paid        |
+------------------------------------------------------------------------------------------+
```

Sizing at 1440 (container 1360): grid `minmax(0, 5fr) minmax(0, 7fr)`, gap 32px. The contract sheet is `position: sticky; top: 72px; max-height: calc(100dvh - 88px); overflow: auto` so it stays beside the ledger while the ledger scrolls. Sheets use `--r-sheet` and `--e-1`. The header (project name, figures, money bar) is **not** a card: it sits on `--ground`, 32px bottom margin. The chain strip is the one wide bordered row (`--sheet`, `--r-sheet`, `--e-0`, four equal columns separated by 1px `--line`).

Behaviours:
- **Evidence trace**: hover/focus on a ledger quote highlights its span in the contract (and vice versa); click or Enter scrolls the span into view (`block:'center'`; `behavior:'auto'` under reduced motion) and plays the hero highlight (6.1). Each contract span is a `<mark>` with `data-milestone`, `tabindex=0`, `aria-describedby` pointing at the ledger row.
- **Active row** = the first non-paid, unlocked milestone: `border-left: 3px solid var(--ink)`, expanded. Paid rows collapse to one line with a disclosure. Locked rows are `--sunk`, text `--ink-3`, one-line reason.
- Invoice and payment detail is the expanded content of the active row. **There is no right rail.**
- Contract sheet tabs: `Contract` and `Risk review (n)` (Radix Tabs).
- Plan state `Proposed` shows the editor and checks bar (4.4); `Approved` shows the receipt line.

1280: same grid (left min 440px); chain strip descriptions clamp to one line (full text in popover and `aria-label`). 1024-1279: below 1100 the grid is `1fr 1fr`; `--t-fig-xl` becomes 35px.
390: single column in this order: project header (name, xl figure, money bar), chain strip collapsed to a `Who can move money` disclosure, a sticky segmented control `Ledger | Contract | Risk (n)` (44px, under the top bar), then content. The active row's primary action is duplicated in a sticky bottom bar (56px, `--sheet`, top border, safe-area padding).

### 4.3 Risk review (a tab in the contract sheet; a one-line summary appears in the ledger while the plan is Proposed)

```
+--------------------------------------------------------------+
| Risk review                       3 flags from the model      |
| (flag) Payment can be withheld indefinitely      [Medium]     |
|   | "Client may withhold payment until it is fully satisfied  |
|   |  with every deliverable."                    Show in text |
|   Why it matters: the client has no deadline to accept work.  |
|   Suggested fix: add a 7 day acceptance window.               |
|--------------------------------------------------------------|
| (flag) Scope is open ended                       [Low]        |
|   ...                                                         |
| Flags are advice. They do not change the plan. Only you can   |
| approve it.                                                   |
+--------------------------------------------------------------+
```
- Flag: `flag` icon in `--danger`, title `--t-h3`, severity chip with icon and word (`Low`, `Medium`, `High`), the verbatim quote (EvidenceQuote with `--danger` bar), "Why it matters" (1-2 sentences), optional "Suggested fix". Rows separated by hairlines, no cards.
- In the contract the flagged span gets `text-decoration: underline wavy var(--danger)` (not marker yellow).
- Quotes pass the same verbatim check as milestone evidence. A flag whose quote is not found is shown greyed with "Quote not found in the contract" and excluded from the count (show it, never hide it).
- Empty: "No risky clauses found in the text the model reviewed. Read the contract yourself before you approve."
- The model has no approve/send action here.

### 4.4 Editable plan (while plan state is Proposed)

```
| Checks  (ok) Currency USD  (ok) Sum 1,500.00 equals contract  (!) Dates: 1 problem  (ok) Quotes 3 of 3 verbatim |
| [ Approve plan ]   Fix 1 date problem to approve.                                                              |
```
- A checks bar sits at the top of the ledger (sticky bottom bar on mobile). Each check is icon + word + result.
- Each row: `Edit` (or `E` on a focused row) turns title, amount and due date into inline inputs. The evidence quote stays **read-only** and shows its check result: `Verbatim match` or `Not found in contract`. Editing re-runs the fixed checks live through the existing validation logic or endpoint (no model call). If the new amount or date does not appear in the quote, the check says "Quote does not mention 800.00" and approval stays blocked. The invariant: amounts and dates must be justified by evidence.
- Row actions: `Edit`, `Remove` (toast "Milestone removed" with `Undo`, 6s), `Add milestone` (the user selects the supporting sentence in the contract and it becomes the quote; with no selection the button explains "Select the sentence in the contract that supports this milestone").
- `Approve plan` is the primary button. Disabled: bg `--sunk`, text `--ink-3`, 1px `--line-strong` border, `aria-disabled=true`, with the reason text visible beside it (never tooltip-only).
- After approval the checks bar is replaced by the receipt line: `(user-round-check) Plan approved by you, 10 Nov 2026, 6:20 PM IST. Editing is locked.` No reopen action.
- If the backend does not yet expose a validation call for edited plans, the editor runs the same pure checks client-side for instant feedback, and the backend remains the authority when saving and approving. Report which it is.

### 4.5 New contract (`/new`), 1440

```
+------------------------------------------------------------------------------------------+
| Portfolio / New contract                                                                 |
| Add a contract                                                                           |
| +------------------------------------------+  +----------------------------------------+ |
| | Client name   [____________]             |  | Proposed milestones                    | |
| | Billing email [____________]             |  |                                        | |
| | Contract text                            |  |  Nothing yet. Paste the contract and   | |
| | +--------------------------------------+ |  |  choose Propose milestones. You review | |
| | | serif 17px textarea, 360px min       | |  |  every amount and date before anything | |
| | +--------------------------------------+ |  |  is sent.                              | |
| | [ Use the sample contract ]              |  |                                        | |
| | [ Propose milestones ]                   |  |                                        | |
| +------------------------------------------+  +----------------------------------------+ |
+------------------------------------------------------------------------------------------+
```
- Left sheet = form; right sheet = result pane moving through: **empty** (copy above), **proposing** (3 skeleton rows shaped like ledger rows, "Proposing milestones", elapsed seconds, `Cancel`; label shows "Model: fixture" in demo mode or the real model name), **validation failed** (failed checks as a list with fix actions, e.g. "Evidence for milestone 2 is not found in the contract. Edit the quote or propose again."), **proposed** (ledger rows in Proposed state and a `Review plan` primary button that opens the workbench with the plan editor).
- Validation: required fields show error text under the field, `aria-invalid`, and focus moves to the first invalid field.
- Demo mode: `Use the sample contract` is the pre-focused primary action.
- After success the workbench opens and plays the evidence trace once (6.1).
- 390: the result pane stacks under the form.

### 4.6 Empty, loading, error states (every data region has four states [HM])

| Region | Empty | Loading | Error |
|---|---|---|---|
| Overview table | "No contracts yet. Add a contract or try the demo contract." `Add contract` (primary), `Try the demo contract` (secondary) | 3 static skeleton rows (64px, `--sunk` bars) | "Couldn't load your projects. Check that the API is running, then retry." `Retry` |
| Contract sheet | "Paste the contract text to start." | 8 skeleton lines | "Couldn't load the contract text." `Retry` |
| Ledger | "No milestones yet. The model proposes them from the contract." | 3 skeleton rows | "Couldn't load milestones." `Retry` |
| PayPal check | n/a | Button "Checking with PayPal", `aria-busy` | "PayPal didn't answer. Nothing changed. Try again." (inline; row stays Sent) |
| Send invoice | n/a | "Sending invoice" | "PayPal rejected the invoice: <reason from API>. Nothing was sent. Fix it and try again." Never auto-retry a send. |
| Model proposal | n/a | skeleton rows with elapsed seconds | "The model's output failed the checks: <list>. Nothing was saved." `Propose again`, `Edit text` |

Errors never apologise; they say what happened, what state things are in, and what to do ([FD] copy rules). Toasts (bottom-left, `role=status`) reuse the button verb ("Invoice sent", "Plan approved"). Skeletons are static (no shimmer) so the motion budget goes to the hero moments.

---

## 5. Component specs

Sizes in CSS px at 1x. Each component has a narrow props interface (section 8).

### 5.1 Buttons
| Variant | Spec |
|---|---|
| Primary | height 40 (44 on touch), padding 0 16, radius 6, bg `--ink` (dark: `--btn`), text white (dark: `--btn-ink`) 14/600, no border. Hover bg `--btn-hover`. Active `translateY(1px)`. Focus-visible 2px `--focus` ring, 2px offset. Label is a verb phrase ("Send invoice"). One primary per screen region. |
| Secondary | height 40, bg `--sheet`, 1px `--line-strong` border, text `--ink` 14/500; hover bg `--sunk`. |
| Quiet | no border, `--ink-2`, underline on hover; for `Retry`, `Reset demo`. |
| Disabled | bg `--sunk`, text `--ink-3` (5.01:1 on sunk), 1px `--line-strong` border, `cursor:not-allowed`, `aria-disabled=true`, **reason text always visible beside it**. Never used to mean "already done". |
| Loading | label becomes "<Verb>ing" ("Sending invoice"), icon spins 1.2s linear (static under reduced motion), `aria-busy=true`, `min-width` fixed to avoid layout shift. |
| Icon button | 40x40, radius 6, quiet; `aria-label` required. |
No arrows appended to labels. Eight states per control: default, hover, focus-visible, active, disabled, loading, error (text, never a shake), success (label "Sent" for 1.2s then final state).

### 5.2 Money `<Money>`
Props: `amountMinor: number` (integer cents), `currency: 'USD'`, `size: 'sm'|'md'|'lg'|'xl'`, `tone?: 'default'|'paid'|'sent'|'muted'`. Renders `<span class="money"><span class="num">1,500.00</span> <span class="cur">USD</span></span>`. Number: Geist Mono 500 tabular; currency: Instrument Sans 13px `--ink-3`, baseline-aligned, 4px gap. Sizes: sm 14, md 20, lg 35, xl 42. Right-aligned in ledger columns. Format with `Intl.NumberFormat('en-US', {minimumFractionDigits: 2})` from integer minor units (no float math). `aria-label="1,500.00 US dollars"`.

### 5.3 Status chip `<StatusChip>`
Height 24, padding 0 8, radius 4, gap 4, 13/500, 14px icon then the word. Boundary 1px in the state colour at 35% mix.

| State | Word | Icon | Fill / text |
|---|---|---|---|
| draft | Draft | pencil-line | `--lock-tint` / `--lock`, dashed border |
| proposed (plan) | Proposed | sparkles | `--lock-tint` / `--ink-2` |
| sent | Sent | send | `--sent-tint` / `--sent` |
| paid | Paid | circle-check | `--paid-tint` / `--paid` |
| locked | Locked | lock | `--lock-tint` / `--lock`, solid border |
| overdue | Overdue | clock-alert | `--danger-tint` / `--danger` |
| risk | Low / Medium / High risk | flag | `--danger-tint` / `--danger` |
| verified | Verbatim match | quote | `--paid-tint` / `--paid` |
| check failed | Not found in contract | circle-alert | `--danger-tint` / `--danger` |
Draft and Locked differ by icon, word and border style, not just colour. No decorative dots.

### 5.4 Milestone row `<MilestoneRow>` (a ledger line, not a card)
A `<li>` with `border-top: 1px solid var(--line)`; the ledger container is the single sheet.
- Collapsed grid (paid and locked): `32px index | 1fr title+date | auto chip | 140px money`, min-height 64px, padding 16 20.
- Index: 28px square, radius 4, mono 13px number; paid shows `circle-check` in `--paid`; locked shows `lock`.
- Title `--t-h3`; date line `--t-label` `--ink-3` ("Due 20 Nov 2026"; overdue: "Overdue since 20 Nov 2026" in `--danger`).
- **Active** (expanded): `border-left: 3px solid var(--ink)`, padding 20, amount at `--t-fig`, evidence pull-quote, invoice line, actions. Only one active row.
- **Locked**: bg `--sunk`, title `--ink-2`, reason "Unlocks when milestone 2 is paid." with lock icon; amount `--ink-3`; no action.
- **Paid**: collapsed; disclosure reveals `Invoice SIM-INV-3FAA854A`, "Paid 400.00 USD", PayPal confirmation time, `Open payer link` (external, rel noopener, accessible name says it opens a new tab).
- **Draft** (invoice not sent): primary `Send invoice`; `Check with PayPal` is hidden (not disabled) until an invoice is sent.
- **Sent**: primary `Check with PayPal`; invoice id and "Sent 10 Nov, 6:30 PM IST".
- **Overdue** (sent, past due, not paid): chip Overdue, date in danger, line "PayPal has not confirmed payment. Check again or contact the client." Primary `Check with PayPal`.
State comes from one pure function (8.2), never recomputed in components.

### 5.5 Evidence quote `<EvidenceQuote>`
Pull-quote, no box: `border-left: 3px solid var(--marker)`, padding-left 16, Source Serif 4 17/28. Highlighted tokens (amount, date) are `<mark>` with bg `--marker`, ink text, radius 2, padding 0 2px, weight 600. Caption below: `Verbatim match` chip. On hover/focus a `Show in contract` quiet button appears (always visible on touch). Text is selectable. In risk flags the bar uses `--danger`.

### 5.6 Chain strip `<TrustChain>` (replaces stepper and trust panel)
Four columns (desktop), each with a 20px icon, actor name (14/600), one-line what it did (13/400 `--ink-2`), and a state word with icon (`Done`, `Waiting`, `Failed`). Below, one 13px sentence across the strip: "The model can't approve, send or mark anything paid. Fixed code checks its work. You approve. PayPal confirms."
Content derives from state: Model "Proposed N milestones"; Code "Passed: currency, sum, dates, quotes" or "Failed: n checks"; You "Approved <time>" or "Waiting for you"; PayPal "N of M paid". Popover on hover/focus: Model "Can propose. Cannot approve, send or mark paid."; Code "Checks currency, sum, dates and that each quote appears verbatim."; You "Approve the plan and send each invoice, as separate clicks."; PayPal "A fresh invoice request must say PAID before the next milestone unlocks, not the browser." Mobile: `Who can move money` disclosure.

### 5.7 Money bar `<MoneyBar>`
`display:flex; gap:2px; height:12px` (14px on workbench). Segment `flex-basis` = amount share, `min-width:6px`. Colours per 4.1. Labels under the workbench bar (`1 Paid`, `2 Sent`, `3 Locked`, 13px) aligned to segment starts; hide labels that would overlap and keep the accessible names. The paid growth uses `transform: scaleX` from the left.

### 5.8 Stepper
Removed as a separate component; merged into 5.6.

### 5.9 Risk flag `<RiskFlag>`: see 4.3. Row padding 16, hairline separators, no card.

### 5.10 Demo banner `<DemoBanner>`: see section 4. `role="status"`.

### 5.11 Inputs
Height 40, radius 6, bg `--sheet`, 1px `--line-strong`, text 14, placeholder `--ink-3`. Focus: 2px `--focus` ring. Error: border `--danger`, `circle-alert` icon and message under it, `aria-invalid`. The contract textarea uses Source Serif 4 17/28.

### 5.12 Toast, dialog, tooltip
Radix primitives restyled with `--sheet`, `--e-2`, `--r-sheet` (tooltip `--r-control`). Dialog only for `Reset demo` confirmation (milestone removal uses Undo). Tooltips never hold essential information.

---

## 6. Hero moments (for the 2:30 video)

### 6.1 Evidence trace (the signature; show it within the first 20 seconds)
Trigger: click or Enter on a milestone quote; also once when a freshly proposed plan first opens.
1. The contract sheet scrolls so the span is centred (200ms; instant under reduced motion).
2. The amount and date spans get the marker highlight: a `::before` layer with `transform: scaleX(0 -> 1)`, `transform-origin: left`, 420ms, 120ms stagger between amount and date. Text stays readable (highlight sits behind via an isolated stacking context).
3. A 2px connector line in `--marker` (with a 1px `--ink` outline so it is visible on white) crosses the 32px gutter to the ledger quote: one element revealed with `scaleX` over 200ms. Reduced motion: no connector; both ends simply stay highlighted.
4. The ledger quote's bar pulses once (`opacity .4 -> 1`, 300ms).
Total <= 700ms. Hover only applies the static highlight.

### 6.2 Unlock on PAID (the money moment)
Trigger: `Check with PayPal` returns PAID from a fresh invoice GET.
1. Button shows "Checking with PayPal" with a spinner for at least 600ms (demo mode simulates 900ms) so it is visible on video.
2. Row 2's chip cross-fades Sent to Paid (200ms opacity); the index square swaps to the check icon.
3. Money bar segment 2 recolours cobalt to green and fills left to right with `scaleX` (500ms). The `Received` figure counts from 400.00 to 1,100.00 over 600ms in tabular figures; `aria-live="polite"` announces "Milestone 2 paid. Milestone 3 unlocked." immediately.
4. Row 3: `lock` swaps to `lock-open` (150ms crossfade); background `--sunk` to `--sheet` (200ms); it becomes the active row (left bar `scaleY` 0 to 1, 250ms); a one-time marker underline sweep under its title (420ms) says "this just unlocked". Focus moves to row 3's primary button.
5. Row 2 collapses to its paid single line by instant swap (no height animation; the cross-fade hides the jump).
6. Chain strip PayPal node updates to "2 of 3 paid".
The only trigger is a verified API response with status PAID. Never a model response, cache or optimistic update.

### 6.3 Approval receipt
On `Approve plan`: dashed borders on editable rows become solid (instant), inputs become text, the checks bar is replaced by the receipt line (200ms fade), and the chain strip "You" node turns Done. No confetti.

### 6.4 Suggested video choreography (150 seconds)
0:00-0:15 overview in demo mode, banner visible, chain strip explained. 0:15-0:40 add the sample contract, proposing, checks pass, risk review. 0:40-1:10 edit one amount to show a failed check, fix it, approve. 1:10-1:30 evidence trace on each milestone. 1:30-2:00 send invoice (simulated), check PayPal, unlock moment. 2:00-2:30 dark mode, 390 mobile quick cut, the trust-boundary sentence on screen, end card. Capture at 1440x900, no secrets or tokens visible.

---

## 7. Accessibility and responsive rules

Target: WCAG 2.2 AA minimum.
- Contrast: tokens in 3.1 and 3.2 already pass; do not introduce new text colours. Non-text UI >= 3:1.
- Never colour alone: every status is icon + word (WCAG 1.4.1; [HM] Floor 11).
- Focus: every interactive element has `:focus-visible` (2px `--focus`, 2px offset) appearing instantly ([HM] Floor 6). A `Skip to ledger` link is the first focusable element. Order: top bar, banner, header, chain strip, contract, ledger.
- Targets: 40px height, 44px hit area on touch (padding or `::after`).
- Keyboard: contract `<mark>` spans and ledger quotes are focusable; Enter triggers the trace; `E` edits a focused row in Proposed state; Esc cancels an edit. Tabs follow the Radix pattern.
- Screen readers: the ledger is an `<ol aria-label="Milestones">`; the active row has `aria-current="step"`. One `aria-live="polite"` region announces payments, approvals and errors. Table heads use `<th scope>`. Icons are `aria-hidden` when a word sits next to them.
- Motion: reduced-motion fallbacks in 3.4 and section 6.
- Zoom and overflow: no horizontal scroll at 320px or 200% zoom. `html, body { overflow-x: clip }` (not `hidden`, not `100vw`) ([HM] Floor 4). Grid tracks use `minmax(0, 1fr)`; long ids use `overflow-wrap: anywhere`.
- `<html lang="en">`; times shown with the zone label ("6:20 PM IST").

| Breakpoint | Rules |
|---|---|
| 1440 desktop | container 1360, grid 5/7 gap 32, sticky contract sheet, chain strip with descriptions |
| 1280 laptop | 24px padding, grid 5/7 (left min 440), chain descriptions one line, header figures inline |
| 900-1279 | below 1100 the grid is 1fr/1fr; `--t-fig-xl` is 35px |
| under 900 | single column; segmented control `Ledger / Contract / Risk`; contract not sticky |
| 390 mobile | padding 16; top bar = wordmark + menu (Add contract and theme live in the menu); xl figure 35px; ledger rows stack (index+title / amount / chip+action); primary action in a sticky bottom bar; chain strip collapsed; demo banner one line + Details; no hover-only affordances |
Screenshots are taken at exactly 1440x900, 1280x800 and 390x844.

---

## 8. Engineering rules (Matt Pocock skills applied)

### 8.1 Shared language [MP grill-with-docs / glossary]
Create `GLOSSARY.md` at the repo root and use these words **exactly** in code, tests and UI copy: *Contract, Plan, Milestone, Evidence quote, Check (a fixed code check), Gate (a human approval), Invoice, Paid (confirmed by a fresh PayPal GET), Unlock, Trust boundary, Demo mode, Fixture*. No synonyms ("task", "step", "payout").

### 8.2 Deep modules, small interfaces [MP codebase-design]
Put logic behind a few deep modules and keep components thin:
- `lib/milestoneState.ts`: `deriveMilestoneView(plan: Plan, milestone: Milestone, invoice: Invoice | null, now: Date): MilestoneView`. `MilestoneView` is a discriminated union on `kind: MilestoneKind` where `MilestoneKind = 'paid' | 'sent' | 'overdue' | 'draft' | 'locked'`, with `primaryAction: 'send' | 'check' | null` and `unlockReason?: string`. Pure, no React. It is the single source of truth for what 5.4 shows (deletion test: removing it would spread branching across five components, so it earns its place).
- `lib/money.ts`: `formatMoney(minor: number, currency: 'USD'): { num: string; cur: string }`, `sumMinor(ms: Milestone[]): number`. Integers only.
- `lib/evidence.ts`: `findEvidenceSpans(contract: string, quote: string): Array<{ start: number; end: number }>` locates text to highlight and returns `[]` when absent. **The backend stays the authority for verbatim checks.**
- `lib/dates.ts`: `formatDue(iso: string, tz?: string): string`.
- API hooks take the client as a parameter ([MP] "accept dependencies, don't create them") so tests inject a fake; components receive plain data and callbacks.
- One adapter per seam until two exist: no PayPal abstraction in the UI beyond the API client.
- TypeScript `strict: true`; no `any`; exhaustive `switch` with a `never` check on state unions; API types in one `api/types.ts` mirroring the backend schemas.

### 8.3 Tests at agreed seams, vertical slices [MP tdd; SP-P]
Seams (test through the public interface only; nothing else gets tests):
1. `deriveMilestoneView`: literal-expectation cases (paid; sent and past due is overdue; second milestone locked while first is not paid; draft offers `send`; sent offers `check`). Expected values are literals, never recomputed (avoid tautological tests).
2. `formatMoney` / `sumMinor`: `formatMoney(150000,'USD')` gives `{num:'1,500.00',cur:'USD'}`; `sumMinor` of 10 and 20 cents is 30 (no float drift).
3. `<MilestoneRow>` from a fixture: the visible **word** for each state (Paid, Sent, Locked, Draft, Overdue); exactly one primary action on the active row; a locked row has no action button.
4. `<TrustChain>`: renders "The model can't approve, send or mark anything paid." and never renders an approve or send control in the Model node.
5. Plan editor: an amount not present in its quote shows "Quote does not mention" and keeps `Approve plan` `aria-disabled`.
6. Playwright smoke: overview, workbench, demo `Check with PayPal`, row 3 becomes active.
Cycle: red first, minimal green, one test per cycle, no HTML snapshot tests. Tooling (free): Vitest + @testing-library/react + user-event + jsdom (`npm i -D vitest @testing-library/react @testing-library/user-event jsdom` if missing), `@playwright/test`, `@axe-core/playwright`.

### 8.4 File map and boundaries [SP-P "File Structure"] (adapt to the real repo)
```
frontend/src/
  styles/tokens.css    all colour, font, space, motion tokens (light + dark)
  styles/base.css      reset, focus-visible, reduced-motion, overflow-x clip
  lib/milestoneState.ts  lib/money.ts  lib/evidence.ts  lib/dates.ts
  components/ui/       Button, Money, Input, Skeleton, Toast        (presentational)
  components/domain/   StatusChip, EvidenceQuote, MilestoneRow, MoneyBar, TrustChain,
                       RiskFlag, DemoBanner, ChecksBar, ContractSheet, TopBar
  features/overview/   OverviewPage, ProjectsTable
  features/workbench/  WorkbenchPage, Ledger, PlanEditor, RiskReview
  features/new-contract/ NewContractPage
  api/                 client.ts, types.ts, hooks
```
Files stay under ~200 lines; domain components take data props and callbacks and never call `fetch`; pages compose; `data-testid` only where role/name queries cannot work.

### 8.5 Hallmark Floor as the lint list [HM]
A task is not done unless: no literal hex or `font-family` outside `tokens.css`; no `transition: all`; no animated width/height/top/left; every interactive element has `:focus-visible`; reduced-motion fallback present; no eyebrows, tracked or all-caps labels, dot-joined meta strings, card inside card, gradient decoration or emoji icons; `overflow-x: clip` on html and body. If Hallmark and Chrome are available also run `node <hallmark-skill-dir>/scripts/sloplint.mjs --scope app --render --url http://localhost:5173/` (the dir is `~/.agents/skills/hallmark` or `~/.claude/skills/hallmark`); fix FAILs, and waive a Reflex finding only with a written reason in the commit message. If it cannot run, say so in the task report and rely on this checklist. Hallmark's hero/fold/section-rhythm gates do not apply (app scope).

---

## 9. Implementation plan [SP-P]

Time: now (Tue 10 Nov evening) to the freeze (Thu 12 Nov 12:00 PM IST) is about 40 hours of calendar time. Tasks are 45-120 minutes each. **M** = must land before freeze; **S** = stretch, only after M tasks are verified.

Global constraints for every task: backend untouched; tokens only; free libraries; no secrets in code, logs or screenshots; one commit per task named `ui: T<n> <summary>`; run block V; write a 5-line report (what changed, screenshot paths, V results, anything skipped) to `docs/ui-reports/T<n>.md` and update the exchange status file.

**V, the verification block for every task:**
1. `npm run lint && npm run build && npm test` pass (the build includes `tsc --noEmit`).
2. `npm run shots` writes screenshots to `docs/ui-shots/T<n>/` for the screens touched: 1440x900, 1280x800, 390x844, light and dark.
3. Checklist 8.5 (or sloplint). Look at every screenshot, write one sentence per screenshot on what is wrong, fix, re-shoot once.
4. Keyboard pass: Tab through the screen; a focus ring is visible everywhere.

### T0 (M, 45 min): tooling, glossary, shots script
- Create `GLOSSARY.md`, `scripts/shots.mjs` (Playwright: routes x 3 sizes x 2 themes, sets `data-theme`, uses demo-mode fixtures), `docs/ui-shots/.gitkeep`; add npm scripts `shots` and `test`; copy this file to the repo root as `DESIGN.md`.
- Install vitest, @testing-library/react, @playwright/test, lucide-react; add one trivial passing test.
- Run `npm run shots` on the current UI for the "before" set (`docs/ui-shots/before/`).
- Acceptance: `npm run shots` writes 6 PNGs per route; `npm test` runs; build passes.

### T1 (M, 90 min): tokens, fonts, base styles
- Files: `styles/tokens.css` (3.1-3.4), `styles/base.css`, Tailwind config mapped to the variables, shadcn variables re-pointed, fonts installed and imported once, IBM Plex removed, theme toggle writes `data-theme`.
- First a test that scans `src/**/*.{css,tsx,ts}` and fails on any hex colour or `font-family` outside `tokens.css`; then implement.
- Acceptance: UI runs with the new colours and fonts in both themes; hex-scan test passes; reduced-motion block present.

### T2 (M, 90 min): primitives
- Files: `components/ui/{Button,Money,Input,Skeleton}.tsx`, `components/domain/StatusChip.tsx`, `lib/money.ts` with tests first.
- Interfaces: `Button({ variant: 'primary'|'secondary'|'quiet'; loading?: boolean; disabledReason?: string; ... })` (a disabled button without `disabledReason` is a type error); `Money({ amountMinor, currency, size, tone })`; `StatusChip({ state })`.
- Acceptance: 5.1-5.3 exactly. Add a `/kit` route (dev only) that shows every variant in both themes and screenshot it.

### T3 (M, 60 min): shell and demo banner
- Files: `TopBar.tsx`, `DemoBanner.tsx`, router layout; delete the left rail.
- Acceptance: top bar 56px, banner 40px, mobile menu at 390, skip link, theme toggle persists, no sidebar; existing screens still load inside the new shell.

### T4 (M, 120 min): state logic, MilestoneRow, EvidenceQuote
- Files: `lib/milestoneState.ts` (tests first: `paid row has no primary action`, `second milestone is locked while first is sent`, `sent past due is overdue`, `draft offers send`), `MilestoneRow.tsx`, `EvidenceQuote.tsx`.
- Acceptance: all five row states per 5.4 from fixtures; one active row; quote per 5.5; no card inside card.

### T5 (M, 120 min): workbench layout
- Files: `WorkbenchPage.tsx`, `Ledger.tsx`, `ContractSheet.tsx`, `MoneyBar.tsx`, `TrustChain.tsx`; remove the right rail, the old stepper and the Demo controls card (controls go in the banner).
- Acceptance: layout per 4.2 at the three sizes; sticky contract sheet at >= 900; invoice detail inside the active row; `Send invoice` appears once per milestone; no eyebrows. Tick every row D1-D12 of section 1 in the report.

### T6 (M, 90 min): evidence trace and unlock moment
- Files: `lib/evidence.ts` (test: correct range for a known contract/quote, `[]` when absent, first match when the quote appears twice), motion CSS, unlock handling in `Ledger`.
- Acceptance: 6.1 and 6.2 exactly; the unlock fires only on an API response with status PAID; reduced motion shows instant states; live region announces.
- Verify: V + Playwright demo-flow test + a 10s capture `docs/ui-shots/T6/unlock.webm` at 1440x900, plus the same flow under `prefers-reduced-motion` emulation.

### T7 (M, 90 min): overview (portfolio)
- Files: `OverviewPage.tsx`, `ProjectsTable.tsx`, API list call; figures computed with `sumMinor`.
- Acceptance: 4.1; demo mode seeds Acme Labs plus two fixture projects (Northwind with a proposed plan, Bluefin fully paid), labelled by the banner; empty state per 4.6.
- Test: figures equal literal sums of the fixture.

### T8 (M, 90 min): new contract flow and states
- Files: `NewContractPage.tsx`, skeleton/error components, toast.
- Acceptance: 4.5 and 4.6 (empty, proposing, validation failed, proposed); exact error copy; focus management. Force each error through a demo-only `?fixture=fail`.

### T9 (M, 120 min): editable plan and approve gate
- Files: `PlanEditor.tsx`, `ChecksBar.tsx`, validation hook (fixed checks only, no model call).
- Acceptance: 4.4; approve disabled with a visible reason until all checks pass; receipt after approval; editing locked after; remove with undo. Manually POST an invalid edited plan to the backend and confirm it still rejects it (the UI is not the authority).

### T10 (S, 90 min): risk review
- Files: `RiskReview.tsx`, `RiskFlag.tsx`, wavy underline spans in the contract.
- Acceptance: 4.3. If the backend risk output is not ready, build against a fixture and state that in the report; do not block other tasks.

### T11 (M, 60 min): responsive and accessibility pass
- Fix 390 and 1280 issues from all screenshots; run axe on every route in both themes (0 serious/critical), keyboard path, reduced-motion run.
- Acceptance: section 7 met; no horizontal scroll at 390; sticky bottom action bar works; axe summary in `docs/ui-reports/axe.md`.

### T12 (M, 60 min): polish and Hallmark sweep (finish by Thu 11:00 AM IST)
- Run sloplint if available; remove leftover eyebrows, dot-strings, cards inside cards; copy pass against the glossary; empty states; page title and favicon; dark-mode review; one critique round per [FD] "remove one accessory" (delete one decorative element per screen).
- Acceptance: checklist 8.5 clean; D1-D12 each marked fixed or consciously waived in `docs/ui-reports/final.md`; final screenshots (overview, workbench light and dark, new contract, mobile) in `docs/ui-shots/final/`.

### Freeze checkpoint, Thu 12 Nov 12:00 PM IST
Tag `ui-v3-freeze`. After this: fixes for broken behaviour, video capture, README screenshots and Devpost text only. Do not publish, push to a public repo, upload the video or submit without Mohd's explicit yes for that exact action.

Cut order if time runs short: T10 first, then the two extra fixture projects (keep Acme Labs), then dark-mode polish (keep the tokens). Never cut T4, T5, T6, T9 or T11.
Suggested schedule: Tue night T0-T3; Wed morning T4-T5; Wed afternoon T6-T8; Wed night T9-T10; Thu morning T11-T12.

### Self-review of this plan [SP-P]
- Coverage: D1-D12 map to T1-T6 and T12; tokens T1; screens T3, T5, T7, T8; components T2, T4; hero moments T6; risk T10; editable plan T9; demo banner T3; accessibility T11.
- Type consistency: `MilestoneKind` (`'paid'|'sent'|'overdue'|'draft'|'locked'`) is the one name used by `deriveMilestoneView`, `StatusChip`, `MilestoneRow` and `MoneyBar`.
- Review focus, the inputs most likely to bite, each pinned to a test: (1) float drift in sums, `formatMoney`/`sumMinor` tests (T2); (2) a quote that appears twice in the contract, the first-match test (T6); (3) milestone sum different from the contract total, checks bar shows the difference and approve stays blocked (T9); (4) PayPal status call times out, row stays Sent with the error text (T6/T8); (5) a very long client name or invoice id at 390 with no horizontal overflow (T11).

---

## 10. Do not

1. Do not let any UI imply the model can approve, send or mark paid. No "Auto-approve", no AI button on a gate.
2. Do not mark anything Paid from cached state, optimistic updates or demo shortcuts in live mode. Only a fresh PayPal GET returning PAID.
3. Do not use yellow for anything except evidence (and the demo banner tint). Do not use blue for primary actions.
4. No eyebrows, no ALL-CAPS or tracked-capital labels, no dot-joined meta strings, no "Step 1/2/3" labels above headings, no arrows appended to link or button text ([HM] Floor 9 and 10; [FD]).
5. No card inside a card; at most two raised surfaces per screen; no grid of identical cards; no KPI tiles with icons or trend arrows.
6. No decorative gradients, glass, grain or paper texture, illustrations, hand-drawn browser mockups, or emoji icons ([HM] Floor 11).
7. No `transition: all`; no animating width/height/top/left; no entrance animations on sections; no hover lift on cards; no looping decoration; no confetti.
8. No invented metrics or testimonials. Numbers come from data; fixtures are labelled by the demo banner ([HM] Floor 8).
9. No disabled button without a visible reason, and none used to mean "done".
10. No literal hex or font-family outside `tokens.css`. No font beyond the three in 3.3. No CDN fonts or scripts.
11. No secrets (`.env.*`, API keys, PayPal client secrets, tokens, real payer emails) in code, fixtures, screenshots, logs, reports or the video.
12. No new hosting, tunnel, public repo push, release, video upload or Devpost/hackathon submission. Local run only. Free tools only. PayPal sandbox with fake funds only.
13. No backend or trust-logic changes. If a task seems to need one, stop and write the question in the status file.
14. No apologetic or filler copy ("Oops", "Awesome"). Errors say what happened, what state things are in, and what to do.
15. Do not restructure the repo or swap the stack (React 19, Vite, Tailwind and Radix stay).
