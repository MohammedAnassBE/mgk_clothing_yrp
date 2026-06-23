# MGK Clothing `/web` — Improvement Roadmap

- **Created:** 2026-06-20
- **Planned start:** Monday 2026-06-22
- **App:** `mgk_clothing_yrp` (Frappe v16 + Vue 3/PrimeVue SPA at `/web`, site `mgk_yrp.site:8003`)
- **Source:** 6-analyst code survey (UX · feature-completeness · code-health · performance · backend/security · Desk parity) + lead-engineer triage.

> **Headline:** The app is feature-rich but carries **three write-path correctness bugs** in its most destructive operations (bulk submit/cancel, bulk edit, a forgeable approval gate) — mostly **small** fixes — plus one large functional gap (non-yarn Calculate Deliverables). Do the data-integrity P0s first; they are the highest risk and lowest effort.

## How to read this

- **Priority:** `P0` = do first (correctness / data-integrity / lifecycle blockers); `P1` = next; `P2` = opportunistic.
- **Effort:** `S` ≈ <½ day · `M` ≈ ½–2 days · `L` ≈ multi-day.
- Each item lists **What · Why · Where · Approach · Acceptance**. File paths are from the survey and should be re-confirmed at the first edit.

## Standing constraints (apply to every item)

- **Don't break List View features** — filters / tabs / search / sort / pagination / bulk / columns, and never change how a DocType's data renders into the list. (Restyle/extend only.)
- **Frontend-first**, but backend changes are allowed *only* in `mgk_clothing_yrp` (never `frappe`/`erpnext`; treat base `yrp`/`production_api` as reference unless the change is genuinely MGK-specific).
- **Verify by measurement** on `:8003` (Playwright e2e + computed styles / element counts), not by eyeballing.
- **Code review** any change >50 lines across the bench before "done" (CLAUDE.md rule 6).
- Conflict/error detection keys on **`exc_type`**, never a numeric HTTP status (Frappe maps most `ValidationError` → 417).

---

## 🔴 P0 — Write-path correctness (the dangerous bugs)

> These corrupt stock/audit data silently. Do them as one bundle on Monday — mostly S/M.

### 1. Bulk submit/cancel bypasses the stale-write guard  ·  high / **S**
- **What:** Thread each row's `modified` into the bulk submit/cancel calls.
- **Why:** `runBulkAction` calls `submitDoc(dt, row.name)` / `cancelDoc(dt, row.name)` with **no `modified`**, so a concurrent edit is treated as a normal submit and **silently clobbered** — on the most destructive, stock-moving operations. This is the exact bug the 2026-06-20 realtime work fixed for single docs; `submitDoc`/`cancelDoc` already accept a 3rd `modified` arg.
- **Where:** `frontend/src/views/dynamic/DynamicListPage.vue` (`runBulkAction` ~`:1439`); `frontend/src/api/client.js` (`submitDoc`/`cancelDoc`).
- **Approach:** Ensure `modified` is in the bulk list's `fetchFields` (list rows carry it), then pass `row.modified`. On a `TimestampMismatchError` row, skip + report it in the bulk-result summary ("3 of 5 submitted; 2 changed since you loaded — refresh"). Don't abort the whole batch.
- **Acceptance:** Two contexts; B holds a stale list; A edits row X; B bulk-submits incl. X → X is rejected (reported), the others succeed, X is **not** clobbered (API-confirmed). E2e on `:8003`.

### 2. `bulk_update_field` parent path uses `db_set` (bypasses validation)  ·  high / **M**
- **What:** Make the parent-field bulk update go through the controller, like the child path already does.
- **Why:** The parent branch calls `doc.db_set(...)` while the child branch calls `doc.save()`. The docstring claims controller validation is preserved — **false** for parent fields: mandatory cross-field rules, computed fields, and link integrity are skipped, so bulk edit can write invalid data.
- **Where:** `mgk_clothing_yrp/mgk_clothing_yrp/api/bulk_edit.py` (`bulk_update_field`).
- **Approach:** Switch the parent path to `doc.set(field, value)` → `_prepare_for_bulk_save()` → `doc.save()` so it matches the child path and the stated contract. Keep the per-row error collection.
- **Acceptance:** A bulk edit that violates a validation rule is **rejected per row** (not silently written); a valid one still succeeds; computed/linked fields recompute. Unit-style check + UI e2e.

### 3. Approval log is forgeable — `before_submit` trusts `approved_by`  ·  high / **M**
- **What:** Re-assert the approver role server-side at submit, and lock the approval fields.
- **Why:** `before_submit` only asserts `approved_by` is *set*; the role check lives **only** in `approve()`. `approved_by` / `rejection_reason` / `mgk_approval_log` are ordinary writable fields, so anyone with WO write can stamp `approved_by` + append a fabricated "Approved" log via a normal save and submit — the audit trail is untrustworthy.
- **Where:** Work Order `before_submit` (MGK doc_event in `hooks.py` → controller); approval logic in `mgk_clothing_yrp/mgk_clothing_yrp/api/work_order.py`.
- **Approach:** In `before_submit`, re-verify the current user (or `approved_by`) holds the configured approver role for the WO's process; and lock `approved_by`/`rejection_reason`/`mgk_approval_log` from direct writes (permlevel or a `validate` guard that rejects out-of-band changes). The only legitimate writer is `approve()`/`reject()`.
- **Acceptance:** A user with WO-write but **not** the approver role cannot submit by hand-stamping `approved_by` (server rejects); the normal Approve→Submit flow still works. E2e + a negative API test.

### 4. Clamp `link_search` `page_length`  ·  medium / **S**
- **What:** Cap the link-search page size.
- **Why:** `limit_page_length = int(page_length or 20)` is **unbounded** on a whitelisted endpoint → a direct caller can pull every readable row of any doctype via leading-wildcard `LIKE` scans.
- **Where:** the `searchLink` backend method (`mgk_clothing_yrp/mgk_clothing_yrp/api/…` — confirm via `frontend/src/api/client.js` `searchLink`).
- **Approach:** `limit_page_length = min(int(page_length or 20), 100)` (match Frappe's own cap).
- **Acceptance:** A request asking for 100000 rows returns ≤100. No UX change for normal typeahead.

---

## 🔴 P0 — Operators forced back to Desk (lifecycle/parity blockers)

### 5. Non-yarn (matrix-mode) Calculate Deliverables has no `/web` entry  ·  high / **M**
- **What:** Add a matrix demand-entry modal that sends `{item_variant, qty}` rows to the existing backend.
- **Why:** **The backend is already done and verified** — `calculate_deliverables` dispatches to `_calculate_matrix_deliverables` → `calculate_major_deliverables`; it only `frappe.throw`s because no UI sends matrix rows. This blocks the deliverable/receivable step for **every cutting/stitching/packing Work Order** (the majority of processes). Highest ROI — the server half exists.
- **Where:** `frontend/src/views/dynamic/CalculateDeliverablesModal.vue` (currently yarn-only); `mgk_clothing_yrp/mgk_clothing_yrp/api/work_order.py` (`_calculate_matrix_deliverables`).
- **Approach:** Branch the modal on the WO's process (yarn vs matrix); for matrix, render a variant + qty entry grid (reuse the variant resolution the backend expects). Pass `modified` (the guard is already wired). Reload deliverables/receivables on success like the yarn path.
- **Acceptance:** A non-yarn draft WO can calculate deliverables end-to-end in `/web`; stale `modified` still rejected; receivables render.

### 6. Work Order close / reopen has no `/web` action  ·  high / **M**
- **What:** Surface the Close-Request → Close-Approve gate (and reopen) in `/web`.
- **Why:** base `yrp` `update_stock` implements the full close gate, leftover-stock reversal (SLEs), and reservation close-out, but `/web` only shows `open_status` read-only. Operators can run a WO in `/web` but must use **Desk to ever close it** — the terminus that books final stock adjustments.
- **Where:** `frontend/src/views/dynamic/DocDetail.vue` (WO actions area, near `WorkOrderApproval`/`CalculateDeliverablesModal`); backend `yrp` `update_stock` whitelisted methods (call over HTTP, don't reimplement).
- **Approach:** Add Close-Request / Close-Approve / Reopen buttons gated by the server's permission/state flags (mirror the `get_approval_state` pattern). Confirm dialogs name the consequence (stock reversal). Thread `modified` for the guard.
- **Acceptance:** A WO can be requested-closed, approved-closed, and reopened entirely in `/web`, with the correct role gating and stock effects; no Desk trip needed.

---

## 🟡 P1 — Floor-app resilience & mobile UX

> It runs on tablets/phones on the production floor — these are reliability/usability, not nice-to-haves.

| Item | Impact / Effort | Where |
| --- | --- | --- |
| **Global error boundary** — one render error currently white-screens the whole SPA (no `onErrorCaptured`); add an app-level "something went wrong / reload" fallback | high / M | `App.vue` / `AppLayout.vue` |
| **Mobile table fallback** — lists & child DataTables have no `overflow-x`/scrollable/card mode; columns squish or hide Status/chevron on a phone | high / M | `DynamicListPage.vue`, `DocDetail.vue`, `global.css` |
| **File attachments** — no upload surface anywhere in `/web` (FilterPanel even excludes Attach); PO/GRN/Inspection need bills, weighment slips, photos | high / M | new component + detail integration |
| **Keyboard/focus** — clickable rows are mouse-only (no `tabindex`/role/`keydown.enter`); no `:focus-visible` on bespoke buttons; two `outline:none` overrides | medium / M | lists, `HomePage.vue`, `CommandPalette`, buttons |
| **S-effort UX cluster** — sticky bulk-action bar, real 404/NotFound route, mobile topbar collapse (~360px overflow) | medium / S | layout + router |

## 🟡 P1 — Remaining Desk parity & performance

| Item | Impact / Effort | Notes |
| --- | --- | --- |
| **Job-work Purchase Invoice** (piece/debit/approval math) is entirely Desk-only | high / L | biggest remaining domain port |
| **Debit two-stage approval** (`approve_debit`) not exposed in `/web` | medium / S | mirror `WorkOrderApproval` pattern |
| **GRN-against-WO "Reload source items"** dead-ends in Desk; DC bundle/transit routing not surfaced | medium / M | |
| **List load: 1 query + N+1 count requests, refired on every realtime tick** | high / M | batch/cache counts; the realtime refetch amplifies this |
| **No `manualChunks`** — PrimeVue vendor fragmented across 5 eager chunks; a `useToast`/`InputNumber` chunk is 153kB | high / M | Vite `manualChunks` to split vendor |
| **DocDetail load is a deep waterfall** with a redundant full second doc fetch; `fetch_from` serial | high / M | parallelize + drop the duplicate fetch |
| Route chunks not prefetched on idle/hover | medium / S | |

## ⚪ P2 — Maintainability & lower-value polish

- **Zero automated tests** for ~7,500 lines of frontend logic — stand up a test floor (Vitest + a couple of Playwright e2e as smoke). *(high / M to start)*
- Move per-doctype business logic into the existing `config/fields` registry *(high / L)*; decompose `DocDetail.vue` (5000 lines, 221 decls, 713 lines CSS) into composables + sub-components *(medium / L)*; extract shared format/status utils; stop swallowing errors silently.
- **`calculate_deliverables` wholesale-replaces receivables** — drops manually-added rows on every run; warn in UI, ideally add an `is_calculated` marker *(medium / M, real footgun on an explicit action)*.
- List **CSV/Excel export** + saved filters/views *(medium / M)*; **home-page KPIs** (pending bills, WIP qty from existing list filters) + editable IPD blueprint *(L)*; Activity timeline omits communications/assignments *(S)*.
- Validate `attribute_name` in `update_mapping_values` before minting Item Attribute Values *(low / S)*; `fetch_grn_details` missing `check_permission('read')` + `useLinkTitles` pulls full meta for one field *(low / S)*.

## ⚡ Quick wins (high impact, S effort — grab these almost for free)

- **Bulk `modified` threading** (P0 #1) — also a quick win.
- **"Add comment" UI on the Activity tab** — `addComment()` already exists in `client.js` (wired only into `WorkflowActions`); the Activity tab is read-only, so floor staff can't leave "rework needed" notes.
- **`link_search` clamp** (P0 #4).
- **`:focus-visible` + sticky bulk bar** (P1 UX cluster).
- **Matrix demand-entry modal** (P0 #5) — backend's already built.

---

## Suggested Monday plan

1. **Morning — P0 write-path bundle** (#1 bulk-guard `S`, #4 `link_search` clamp `S`, then #2 `bulk_update_field` `M`, #3 approval lock `M`). One branch, e2e each, one code review. Highest risk, lowest effort, and #1 follows straight from the realtime work.
2. **Afternoon — P0 parity** (#5 matrix Calculate Deliverables — backend ready; #6 WO close/reopen if time).
3. Pick up P1 (error boundary + mobile tables) once P0 is verified + merged.

## Verification checklist (per item, before "done")

- [ ] Two-context e2e on `:8003` proving the fix (and, for the bugs, proving the *old* behavior was broken).
- [ ] List-view feature sweep unchanged (filters/tabs/search/sort/pagination/bulk/columns).
- [ ] Zero new console errors.
- [ ] `exc_type`-based conflict handling (never numeric status).
- [ ] Code review for any >50-line change.

## Open decisions for the owner

- P0 #3: lock the approval fields via **permlevel** (cleaner, needs a Custom Field perm change) vs a **validate guard** (no schema change)? → pick Monday.
- P0 #6: expose **Reopen** to the same role as Close-Approve, or a separate role? → confirm against MGK Settings.
- P1 attachments: which doctypes get upload first (PO / GRN / Inspection)? → start with one.
