# MGK Clothing `/web` — UI Polish Spec

**Date:** 2026-06-20
**App:** `mgk_clothing_yrp` · **Site:** `mgk_yrp.site` · **Surface:** the `/web` Vue 3 + PrimeVue 4 SPA
**Author:** Claude (with Mohammed Anas)
**Status:** DRAFT — for review before implementation

---

## 1. Goal & North-Star

Make the `/web` SPA *feel finished* — a crafted product, not a competent internal tool. The bar is the
`partners_api` design mockup (`~/Downloads/Telegram Desktop/ui-mockup.html`), which feels polished because
of a **disciplined system**, not a lucky look:

> **4 colour tokens + 1 font + opacity-derived neutrals + soft layered shadows + a tight type scale.**
> Everything (muted text, borders, hover, tints, focus rings) is *derived* from two neutral tokens by
> opacity. Result: perfect coherence, calm whitespace, clear hierarchy.

We port that exact system onto MGK's existing `--mgk-*` token layer, keeping MGK's teal identity.

## 2. Non-Goals (hard constraints)

- **Frontend-only.** No backend changes — no DocType edits, no Python, no schema/migrations, no API
  changes. Everything happens in `apps/mgk_clothing_yrp/frontend/`. *(User: "changes only in the UI,
  nothing in the back end.")*
- **No behaviour/logic changes.** The source-bin split logic, ungroup contracts, workflow actions, and
  data contracts in the heavy editors stay byte-for-byte. We restyle, we do not re-engineer.
- **No new features.** ⌘K, dark mode, action hierarchy already exist (on `feat/web-ui-revamp`) — we
  fold them in and elevate, we don't invent new capability.
- **No dependency churn** beyond adding the Inter webfont (self-hosted) and (optionally) PrimeVue
  `Skeleton`.

## 3. Locked Design Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| D1 | Brand colour | **Teal primary + indigo accent** | Keeps "Bright Workshop" identity + all prior teal work; teal is the *reference's own accent*, so it's design-system-approved. One-token flip to indigo-lead if desired later. |
| D2 | Font | **Inter** (self-hosted, variable) | The single biggest "polish" lever after spacing. Replaces system-font stack. |
| D3 | Colour model | **4 tokens + opacity** | `primary`, `accent`, `ink`, `surface`; everything else derived. Kills ad-hoc hex. |
| D4 | Nav | **Slim hover/pin-expand rail** (68px → 232px) with **module groups preserved**, pin toggle, mobile drawer | Best of both: airy like the reference, but keeps group findability for ~20 doctypes. |
| D5 | Home | **Reference dashboard layout** | Greeting + primary CTA → big stat cards → tabbed table card. |
| D6 | Density | Single `--pad` multiplier (Comfortable 1.0 / Compact 0.92), default Comfortable | Cheap, optional topbar toggle; can defer to a later phase. |
| D7 | Dark mode | Two-token swap (`ink`,`surface`) under `[data-dark]` / `.dark` | Reuses existing scaffolding; now *correct by construction* because colours are derived. |

## 4. The Token System

Rebuild `frontend/src/assets/styles/global.css` (and feed `theme.js`) around **four RGB-triplet tokens**
so opacity-derivation works (`rgb(var(--c-ink)/.56)`):

```css
:root{
  --c-primary: 13 148 136;   /* #0D9488  MGK teal  (hero: CTAs, active nav, links, focus) */
  --c-accent:  79 70 229;    /* #4F46E5  indigo     (secondary CTAs, highlights, info)    */
  --c-ink:     27 34 51;     /* #1B2233  near-black slate (all text/borders via opacity)  */
  --c-surface: 247 248 251;  /* #F7F8FB  cool near-white (page bg)                         */
  --r: 12px;                 /* card radius; controls 9px; badges 999px; modal 16px        */
  --pad: 1;                  /* density multiplier                                          */
}
[data-dark="1"], .dark{ --c-ink: 226 232 240; --c-surface: 17 21 33; } /* #E2E8F0 / #111521 */
```

**Derived neutrals (the discipline — no stray hex anywhere):**

| Use | Value |
|---|---|
| Primary text (`--mgk-ink`) | `rgb(var(--c-ink))` |
| Secondary / muted text | `rgb(var(--c-ink)/.56)` |
| Field label | `rgb(var(--c-ink)/.75)` |
| Card / control border | `rgb(var(--c-ink)/.10)` |
| Table row line | `rgb(var(--c-ink)/.08)` |
| Hover wash | `rgb(var(--c-ink)/.05)` |
| Input rest bg | `rgb(var(--c-ink)/.03)` |
| Badge tint bg | `rgb(var(--token)/.12–.14)` |
| Focus ring | `0 0 0 3px rgb(var(--c-primary)/.16)` |
| Card surface | `#fff` (light) / `rgb(255 255 255/.04)` (dark) |

**Status colours** stay as named semantic tokens (already AA-tuned) but expressed the same tinted-pill way:
`--c-success: 4 120 87`, `--c-warn: 180 83 9`, `--c-danger: 220 38 38`. Badges = `color: token; background: token/.12`.

**Back-compat:** keep the existing `--mgk-*` names as *aliases* mapped onto the new derived values, so the
14 editors keep working during migration and we delete hardcoded hex incrementally rather than in a risky
big-bang.

### Shadows (soft, layered, ink-based)
```
--shadow-sm:  0 1px 2px rgb(var(--c-ink)/.05), 0 1px 1px rgb(var(--c-ink)/.04);
--shadow-card:0 1px 2px rgb(var(--c-ink)/.05), 0 10px 28px rgb(var(--c-ink)/.06);
--shadow-pop: 0 10px 30px rgb(var(--c-ink)/.16);   /* dropdowns, toasts        */
--shadow-rail:0 16px 44px rgb(var(--c-ink)/.16);   /* expanded rail            */
--shadow-modal:0 30px 70px rgb(0 0 0/.35);          /* dialogs                  */
```

## 5. Typography Scale (Inter)

| Token | Size / weight / tracking | Used for |
|---|---|---|
| `--t-stat` | 24px / 800 / -0.5px | Dashboard stat numbers |
| `--t-h1` | 18px / 800 | Page greeting / page title |
| `--t-h2` | 14px / 700 | Card titles |
| `--t-section` | 13px / 700 / UPPER / .08em / ink·.5 | Section labels |
| `--t-body` | 14px / 500 | Inputs, body |
| `--t-nav` | 13.5px / 600 | Nav items |
| `--t-th` | 11px / 700 / UPPER / .04em / ink·.5 | Table headers |
| `--t-td` | 13px / 400 | Table cells |
| `--t-badge` | 11.5px / 700 | Status pills |
| `--t-label` | 12.5px / 600 / ink·.75 | Field labels |
| `--t-btn` | 13px / 600 | Buttons |

## 6. Spacing · Radius · Motion

- **Spacing:** keep the existing `--space-1..6` (4/8/12/16/20/24). *Enforce* its use — no raw px in new code.
- **Radius:** `--r:12px` cards · `9px` controls/buttons/inputs · `999px` badges · `16px` modals · `18px` "device"/hero frames.
- **Motion:** standard ease `cubic-bezier(.16,1,.3,1)`, durations 140ms (controls) / 180ms (rail) / 200ms (overlays).
  - Toasts slide in from right; dialogs fade+rise; rail width transitions; route fade (already present);
    bulk bar + filter chips fade/slide; table rows fade on add/remove; section collapse animates height.

## 7. Responsive Model

Two primary breakpoints (mobile-first):

| Band | Width | Nav | Grids |
|---|---|---|---|
| **Mobile** | `< 768px` | Off-canvas **drawer** + hamburger in topbar | Stats 2-col → 1-col; tables become stacked card-rows or x-scroll; forms 1-col |
| **Desktop** | `≥ 768px` | **Rail** (68px, hover/pin-expand to 232px) | Stats 4-col; tables full; forms 2–3 col |
| *(Wide)* | `≥ 1280px` | Rail | Content max-width 1180px, centred |

Rule of thumb baked into every screen section below: **desktop = horizontal density (rail + multi-col);
mobile = vertical stack (drawer + single column + larger tap targets ≥ 44px).**

## 8. Component Kit (the reusable layer — build once, reuse everywhere)

All specced to the reference. Implemented as PrimeVue theme overrides (`theme.js`) + a few thin wrappers.

- **Buttons** (`9px` radius, weight 600, gap 7px, 140ms, hover brightness 1.06):
  `primary` filled teal · `accent` filled indigo · `ghost` outline `ink/.14`, hover `ink/.05` · `danger` `#dc2626`.
  Sizes: default `8px×14px·13px`, small `5px×10px·12px`. Loading shows spinner **and** verb ("Saving…").
- **Badges/Tags:** pill, `token/.12` bg + `token` text, 11.5px/700. Variants: primary, accent, muted, success, warn, danger.
- **Inputs:** `ink/.03` bg, `ink/.14` border, `9px`; focus → teal border + `primary/.16` ring + white bg.
  Required-error state → `danger` border + `danger/.12` bg, message under field.
- **Tabs:** underline style — active = teal text + 2px teal underline; inactive `ink/.6`.
- **Table:** `th` 11px UPPER `ink/.5`; rows separated by `ink/.08` lines; hover `ink/.05`; padding `10–12px`.
- **Cards:** `#fff`, `1px ink/.10` border, `--r`, `--shadow-card`.
- **Toasts:** white card, 4px left border by kind (teal/accent/amber/red), slide-in, top-right.
- **Dialogs:** max 460px, `16px` radius, header/body/footer sections, overlay `ink/.45`, fade+rise.
- **Empty state:** consolidate every editor's ad-hoc empty onto one `.mgk-empty` (dashed border, teal icon,
  muted text, optional CTA). Variants: `.inline` (compact grids) / `.hero` (page-level).
- **Skeletons:** shimmer placeholders for table rows, form field grids, and the big editor grids — shown
  while data loads instead of blank/`Loading…` text.

## 9. Screen — App Shell (`AppLayout` / `AppSidebar` / `AppTopbar`)

**Desktop (`≥768`):**
```
┌────┬──────────────────────────────────────────────────────────┐
│rail│ topbar: [hamburger·hidden] [search ───] [bell] [avatar]   │ 56px
│68px├──────────────────────────────────────────────────────────┤
│ ▢  │                                                            │
│ ▢  │   main content  (max-w 1180, pad 22×28)                    │
│ ▢  │                                                            │
│ ⚙  │                                                            │
└────┴──────────────────────────────────────────────────────────┘
rail hover/pin → 232px, slides over content with --shadow-rail, group labels fade in
```
- Rail rest = 68px icon-only; hover or pinned = 232px showing logo wordmark + **group headers** +
  labelled items. Active item = `primary/.12` bg + teal text + teal 3px left mark. Pin button persists
  (reuse `useSidebarCollapse`). Settings/Desk pinned to bottom.
- Topbar 56px white, `ink/.10` bottom border: left = page title (mobile: hamburger), centre-left = search
  pill (max 340px, opens ⌘K), right = bell, theme toggle, avatar (accent bg, initials) + role.

**Mobile (`<768`):**
```
┌──────────────────────────────────────┐
│ [☰] [search ───────────] [bell] [SK]  │ 56px
├──────────────────────────────────────┤
│  main content (pad 16)                │
└──────────────────────────────────────┘
☰ → drawer slides in (248px) over a scrim; tap scrim/route-change closes
```

## 10. Screen — Home / Dashboard (`HomePage.vue`) — *matches the reference exactly*

**Desktop:**
```
Good morning, Administrator                                  [ + New ▾ ]
Here's today across the operation.
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│   0      │ │   1      │ │   0      │ │   5      │   stat cards
│ Design   │ │ Pending  │ │ Vendor   │ │ Open     │   number 24/800
│ Approvals│ │Inspections│ │ Bills    │ │ Work Ord │   label 12/ink·55
└──────────┘ └──────────┘ └──────────┘ └──────────┘   4-col, gap 14
┌──────────────────────────────────────────────────────────┐
│ [Recent WOs] [Awaiting inspection] [Flagged]              │  tab card
│ CODE        ITEM            QTY     STATUS                 │
│ WO-…        Towel …         120     ● Submitted            │
│ …                                                          │
└──────────────────────────────────────────────────────────┘
```
- **Greeting block** (left): `--t-h1` greeting + muted subtitle. **Primary CTA** (right): `+ New ▾` split
  button — default = most-common create (Work Order), menu = the rest of "Quick Create". Folds the current
  loose "Quick Create" button row into one clean action.
- **Stat row:** the 4 work-queue counts from `useHomeQueues`, rendered as **big bold stat cards**
  (number `--t-stat`, label muted). Whole card clickable → the relevant filtered list. Replaces the current
  small icon+number cards.
- **Tabbed table card:** replaces the "Jump to" card grid with a useful **recent-work table** (tabs =
  Recent / Awaiting / Flagged), clean rows, status pills. *Data already available via existing list APIs —
  no backend change.*

**Mobile:**
```
Good morning, Administrator           [ + ]   ← icon-only CTA
Here's today…
┌────────┐ ┌────────┐
│  0     │ │  1     │     stats 2-col
└────────┘ └────────┘
┌────────┐ ┌────────┐
│  0     │ │  5     │
└────────┘ └────────┘
[Recent ▾]  (tabs become a select if cramped)
card-rows: WO-… · 120 · ●Submitted   (stacked, not a wide table)
```

## 11. Screen — List (`DynamicListPage.vue`)

**Desktop:**
```
Work Orders                                   [filters] [cols] [ + New ]
[All] [Draft] [Submitted] [Cancelled]                       ← status tabs (underline)
[ search ─────────]   [active filter chips ✕]
┌──────────────────────────────────────────────────────────┐
│ ☐ CODE     ITEM         QTY    STATUS      DATE            │  th 11/UPPER
│ ☐ WO-…     Towel…       120    ●Submitted  20 Jun          │  rows, hover ink·05
└──────────────────────────────────────────────────────────┘
[selection bar slides up when rows checked]      [paginator]
```
- Status tabs → underline style. Filter chips fade in/out. **Skeleton rows** while loading (not blank).
  Selection bar animates in. Empty → `.mgk-empty.hero`. Currency/number/date via shared formatters; empty
  cell = "—".

**Mobile:** toolbar collapses to `[search] [⏷filters]`; status tabs scroll horizontally; **table → card list**
(each row a card: title + key fields + status pill); selection via long-press/checkbox; paginator → "Load more".

## 12. Screen — Detail (`DocDetail.vue`)

**Desktop:**
```
‹ Back   WO-2627-00493            ●Submitted     [Primary CTA] [More ▾] [Cancel]
[Details] [Activity] [Linked]                                  ← tabs
┌───────────────────────────────┐  ┌───────────────────────┐
│ field grid (2–3 col)          │  │ meta card             │
│  Value (16/700)               │  │  Created / Modified   │
│  label (11/UPPER/muted)       │  │  Owner / Workflow     │
│ ── child tables (DataTable) ──│  └───────────────────────┘
└───────────────────────────────┘
```
- Action hierarchy (already on revamp branch): one filled-teal primary CTA + `More ▾` overflow + separated
  Cancel. Field display = value-as-hero over label. Child tables get header band + skeleton + `.mgk-empty`.
  Save buttons show verb + spinner. Failed-required field gets a red border + the banner names it.

**Mobile:** header wraps (title + status on row 1, actions collapse into a single `Actions ▾`); tabs scroll;
field grid → 1-col; meta card moves below; child tables → card rows.

## 13. The 14 Heavy Editors — consistency pass (not a redesign)

`InspectionEntryEditor`, `ProductionOrderView`, `BOMMappingEditor`, `ProcessMatrixEditor`,
`StockItemGridEditor`, `GRNReceivedTypeEditor`, `IPDConfigView`, etc. **Structure and logic stay frozen.**
They inherit the new system automatically (tokens, font, shadows, radius). On top of that, a **mechanical,
low-risk pass** per editor:

1. Replace hardcoded hex (e.g. `#9ca3af`, `#f0fdf4`, `#be123c`) with `--c-*`/status tokens.
2. Replace raw-px spacing with `--space-*`.
3. Swap ad-hoc empty states for `.mgk-empty`.
4. Add load skeletons where the grid currently flashes blank.
5. Add the small motions (row add/remove, section collapse).

This is the ideal slice to **fan out in parallel** during implementation (one agent per editor, isolated,
verified) — high volume, low coupling, each independently checkable against a before/after screenshot.

## 14. Dark Mode

Already scaffolded. Because all colour is now derived from `ink`/`surface`, dark mode becomes *correct by
construction* — flip the two tokens, cards become `white/.04`, borders/text/tints re-derive automatically.
We keep the topbar toggle (persisted, OS-default) and re-verify the previously-patched dark surfaces
(DataTable rows, Tabs, Dialog, paginator, menus) under the new derived values.

## 15. Phasing & Sequencing

**Phase 0 — Visual proof (de-risk before touching Vue).** Produce an **MGK-branded clickable mockup**
(the reference HTML, re-tokenised teal-primary, with MGK's real nav/groups, real home queues, real
doctypes) so you can *see and toggle* the exact target — light/dark, density, desktop/mobile — and approve
the look before any real code. *Matches how your friend delivered, which you liked.*

**Phase 1 — Token foundation.** Rewrite `global.css` + `theme.js` to the 4-token+opacity system, add Inter,
shadows, type scale; alias old `--mgk-*` names. *Propagates everywhere; nothing should visually break.*

**Phase 2 — App shell.** Rail nav (groups + pin + drawer) + topbar.

**Phase 3 — Home/dashboard.** Reference layout (stats + tabbed table), desktop + mobile.

**Phase 4 — List + Detail.** `DynamicListPage` + `DocDetail`: tabs, pills, skeletons, empty states, mobile
card-rows, motion.

**Phase 5 — Editor consistency pass.** Fan out across the 14 editors (parallel, isolated, screenshot-verified).

**Phase 6 — Polish sweep.** Density toggle, dark-mode re-verify, a11y/touch, motion QA.

Each phase ends with before/after screenshots on `:8003` and your sign-off.

## 16. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Token migration visually regresses legacy editors | Alias old `--mgk-*` → new derived values; migrate hex incrementally; screenshot-diff each editor |
| Rail hover-expand feels finicky / hurts touch | Pin toggle + full drawer on mobile; expand on hover *and* focus; generous hit area |
| Inter webfont FOUT / weight | Self-host variable Inter, `font-display:swap`, preload |
| Home redesign needs new data | Uses existing list/queue APIs only — **no backend change** |
| Big diff (>50 lines) lands unreviewed | Per CLAUDE.md rule 6, run `requesting-code-review` before claiming any phase done |

## 17. Definition of Done (per phase)

- Builds clean: `npm --prefix frontend run build`.
- Verified live on `http://mgk_yrp.site:8003/web` via `pw-shot.mjs` — **desktop and mobile** widths, light
  and dark, no console errors.
- Before/after screenshots captured and diffed.
- No backend file touched (git diff scoped to `frontend/`).
- Code review passed for any >50-line phase.

## 18. Open Questions (minimal)

1. **Branch:** continue on `feat/web-ui-revamp` (has dark mode + ⌘K + action hierarchy already) and rename,
   or start `feat/web-ui-polish` fresh from it? *(Recommend: continue on the revamp branch — the foundation
   is there.)*
2. **Home "+ New" default action:** is **Work Order** the single most common create? (Affects the split-button default.)
3. **Density toggle:** ship in Phase 2 or defer to Phase 6? *(Recommend defer.)*
