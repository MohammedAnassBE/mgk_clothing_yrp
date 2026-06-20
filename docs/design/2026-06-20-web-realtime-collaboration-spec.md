# /web Real-Time Collaboration — Design Spec

- **Date:** 2026-06-20
- **App:** `mgk_clothing_yrp` (the `/web` Vue 3 + PrimeVue SPA, site `mgk_yrp.site:8003`)
- **Status:** Draft for review
- **Author:** Claude (Opus 4.8) for Mohammed Anas
- **Related:** `2026-06-20-web-ui-polish-spec.md`

---

## 1. Problem

The `/web` SPA is **fetch-on-navigate only** — there is no live update mechanism (verified: zero `socket`/`realtime`/`EventSource`/polling in `frontend/src`). On a site with many concurrent users this causes two failures:

1. **Silent overwrite (data loss).** Two users open the same document. User A edits and saves; User B (still looking at the old copy) saves and **clobbers A's changes with no warning.** This is a *current latent bug*, not just a missing feature — see §3.
2. **Stale views.** A user looking at a document or a list does not see that someone else submitted / modified / created records. They act on outdated information.

The user's requirement (verbatim intent):

> WebSocket management in the front-end. Thousands of users; for a single document multiple users may make changes. If a user is viewing a *draft* document and another user *submits* it, show a popup **"Document was modified"** with a **Refresh** button. This works on **all doctypes, all documents, everywhere**. In the **list view** we also need a websocket connection, but **no popup** — the list should just update (e.g. another user creates a record → it appears). And if the document was modified without refreshing, the user **must not be able to save/update** (that would corrupt data).

---

## 2. What already exists (so we build minimally)

Frappe ships the entire realtime backbone. We reuse it; we do **not** write event-emitting code.

| Capability | Detail | Source |
| --- | --- | --- |
| Socket.IO server | Node process on `socketio_port` (default **9000**), namespace = site name | `apps/frappe/realtime/index.js` |
| Auth | Browser `sid` session cookie (sent with `withCredentials`); validated via `frappe.realtime.get_user_info` | `apps/frappe/realtime/middlewares/authenticate.js` |
| **`doc_update`** event | Fires on every doc save/cancel. Room `doc:<doctype>/<name>`. Payload `{ modified, doctype, name }` | `apps/frappe/frappe/model/document.py:1427` |
| **`list_update`** event | Fires on every non-single/non-child save. Room `doctype:<doctype>`. Payload `{ doctype, name, user }` | `apps/frappe/frappe/model/document.py:1435` |
| Subscribe (doc) | `socket.emit('doc_subscribe', doctype, name)` → joins `doc:<dt>/<name>` | `apps/frappe/realtime/handlers.js:58` |
| Subscribe (list) | `socket.emit('doctype_subscribe', doctype)` → joins `doctype:<dt>` | `apps/frappe/realtime/handlers.js:33` |
| **Stale-write check** | `check_if_latest()` raises `TimestampMismatchError` → **HTTP 417** (not 409 — see note) *if the client sends `modified`* | `apps/frappe/frappe/model/document.py:1015` |
| Error handling | The SPA's request layer already routes 404/409/**417** through `_server_messages` and surfaces the message — but throws a bare `Error` that drops `exc_type`/status | `frontend/src/api/client.js:63` |

> **Status correction (verified in source):** `TimestampMismatchError(ValidationError)` is a bare `pass` (`apps/frappe/frappe/exceptions.py:166`) → inherits `ValidationError.http_status_code = **417** Expectation Failed` (`exceptions.py:25`). The `409` belongs to `NameError` (`exceptions.py:57`); nothing remaps timestamp-mismatch to 409. **Detect conflicts on `exc_type === "TimestampMismatchError"` in the JSON error body — status-agnostic — not on a numeric code** (Frappe lumps many validation failures under 417). `client.js` must be enriched to carry `exc_type` on the thrown error so the save handler can branch (today it throws `new Error(msg)`, losing `exc_type`).

**The SPA lacks only two things:** the `socket.io-client` library (not in `frontend/package.json`), and it never sends `modified` on update.

---

## 3. The data-loss bug (must-fix, independent of websockets)

`DocDetail.vue` → `buildPayload()` (≈ `:3048`) builds the PUT body but **omits `modified`**. Trace of why that silently clobbers:

1. `updateDoc` PUTs `/api/resource/<dt>/<name>` with body that has **no** `modified` (`client.js:214`).
2. Backend `frappe.get_doc(dt, name, for_update=True)` loads the *current* DB row (latest `modified`).
3. `doc.update(data)` — `data` has no `modified`, so `doc.modified` stays at the **current DB value**.
4. `check_if_latest()` compares DB `modified` against `_original_modified` (= the value the client "sent", which is the current DB value) → **they match → no error → overwrite.**

**Fix:** include the `modified` the client *loaded* in the payload. Then step 3 sets `doc.modified` to the *stale* value, the compare mismatches, and Frappe raises `TimestampMismatchError` (**HTTP 417** — detect via `exc_type`, see §2 note), which the SPA already surfaces. This is the hard, server-enforced guard for requirement #3 and works even if the websocket is down.

> **Critical invariant:** the realtime layer must **never** silently mutate `doc.value.modified`. The conflict guard depends on `doc.value.modified` reflecting *what the user loaded*. Realtime only sets a *flag*; the loaded `modified` changes only on an explicit reload (Refresh button or after a successful save). Violating this defeats the guard and re-introduces the clobber.

---

## 4. Architecture

```
                 ┌────────────────────────────┐
                 │  Frappe Socket.IO  (:9000)  │  emits doc_update / list_update
                 └─────────────┬──────────────┘
                               │ sid cookie (withCredentials)
                 ┌─────────────▼──────────────┐
                 │  useRealtime.js (singleton) │  one connection per tab
                 │  connect / on / off /       │  ref-counted subscriptions
                 │  docSubscribe / listSubscribe│
                 └──────┬───────────────┬──────┘
                        │               │
          ┌─────────────▼───┐     ┌─────▼──────────────────┐
          │  DocDetail.vue   │     │  DynamicListPage.vue    │
          │  • conflict guard│     │  • debounced fetch()    │
          │  • stale banner  │     │  • selection-aware      │
          └──────────────────┘     └─────────────────────────┘
```

### 4.1 `useRealtime.js` (new composable — the only new infra file)

A **module-singleton** so every component shares one socket (the Frappe Desk pattern). Responsibilities:

- **Lazy connect** on first subscription; build URL as
  `` `${location.protocol}//${location.hostname}:${port}/${siteName}` `` where `port = window.frappe.boot.socketio_port || 9000` and `siteName = window.frappe.boot.site_name`.
  *(Note: build from `hostname`, not `location.origin` — origin already carries `:8003` and would double-port. Frappe's own `socketio_client.js` does the host-only construction.)*
- `io(url, { withCredentials: true, reconnectionAttempts: 5, secure: location.protocol === 'https:' })`.
- **Ref-counted subscribe/unsubscribe** per room so navigating between docs cleanly joins/leaves `doc_subscribe` / `doc_unsubscribe` rooms.
- Expose: `onDocUpdate(doctype, name, cb)`, `onListUpdate(doctype, cb)`, each returning a disposer for `onUnmounted`.
- **Degrade gracefully:** if the socket never connects (server down, blocked), the SPA works exactly as today. Realtime is strictly additive; the §3 hard guard still protects saves.

### 4.2 Backend change (minimal, one field)

`get_boot()` in `www/web.py:86` returns `site_name` and `user` but **not** `socketio_port`. Add it:

```python
"socketio_port": frappe.conf.socketio_port or 9000,
```

That is the **only** backend change. No new endpoints, no event emitters (Frappe core already emits). This is necessary infra wiring for a websocket feature — out of scope of the earlier "frontend-only UI polish" rule, which applied to the *restyle* task, not to this new capability.

---

## 5. Feature A — Detail view (all doctypes via `DocDetail.vue`)

Two layers, independent, both required:

### A1. Hard write guard (server-enforced, always on) — **save + submit + cancel**

The guard must cover **every standard write verb**, not just plain save (verified — see §A1.1):

- **Save:** in `buildPayload()` for **edit mode only**, add `payload.modified = doc.value.modified` (skip on create).
- **Submit / Cancel:** `submitDoc`/`cancelDoc` (`client.js:450/461`) today PUT only `{docstatus:1|2}` with **no `modified`**, so a stale submit/cancel is **unguarded** — and a stale submit on an already-submitted doc is silently accepted by Frappe as `update_after_submit`. Fix: thread `doc.value.modified` → `submitDoc(dt, name, modified)` / `cancelDoc(dt, name, modified)` and through `useDoc.submit/cancel`. The timestamp check (`document.py:1035`) runs **before** the docstatus-transition check, so it catches both "someone edited the draft" and "someone already submitted it."
- **Conflict detection:** key on **`exc_type === "TimestampMismatchError"`** (status-agnostic; the status is 417, but do not key on the number). Replace the raw server text with a friendly message + a **Refresh** affordance: *"This document was changed by someone else after you opened it. Refresh to load the latest version, then re-apply your changes."* Surface = existing error banner (`DocDetail.vue:235`) + a Refresh button calling `docState.load(id)`. Requires enriching `client.js` to attach `exc_type` to the thrown error.
- Result: even with websockets off, a stale save/submit/cancel **cannot** silently overwrite.

#### A1.1 ⚠️ Coverage boundary — custom whitelisted methods bypass the guard
The `modified`-in-payload guard protects the **standard `/api/resource` PUT** path. Verified facts:
- **Item grids ARE covered** (good news): grid edits save through the standard PUT — grouped JSON is ungrouped in `before_validate`/`sync_vue_item_details` — so once `modified` is in the payload, grid saves are guarded. (The earlier worry that grids bypass via `group/ungroup_items_from_ui` was wrong.)
- **Custom action methods are NOT covered:** `mgk_clothing_yrp/mgk_clothing_yrp/api/work_order.py` — `calculate_deliverables` (`:295`, saves `:447`/`:563`), `approve` (`:69`), `reject` (`:81`) — each does `frappe.get_doc("Work Order", name)` (**fresh load**) then `.save()`. A fresh load makes `_original_modified == DB.modified`, so `check_if_latest()` always passes → **silent clobber** of any change made after the user's form load.
- **Fix (backend, in-scope — `mgk_clothing_yrp`, not `production_api`):** add an optional `modified` arg to these methods; right after `get_doc`, pre-flight:
  ```python
  if modified and cstr(wo.modified) != cstr(modified):
      frappe.throw(_("{0} was modified after you opened it. Please refresh.").format(wo.name),
                   frappe.TimestampMismatchError)
  ```
  Client passes the loaded `modified`; on `TimestampMismatchError` the SPA shows the same Refresh affordance. (Do **not** poke the private `_original_modified`.)
- **Scope call (see §9.5):** `calculate_deliverables` is the meaningful clobber surface (it persists computed deliverables/receivables onto the WO) → recommend **in v1**. `approve`/`reject` are approval-state only (lower risk) → same pattern, can ride along or defer.

### A2. Live "document modified" notice (websocket)
- On doc load: `onDocUpdate(doctype, name, cb)` (joins `doc:<dt>/<name>`).
- On event: compare `event.modified` to the loaded `doc.value.modified`.
  - **Newer** → set `staleNotice = true` (does **not** touch `doc.value`). Render a **non-blocking banner**: *"This document was modified. [Refresh]"*. Refresh → `docState.load(id)` → clears the notice and adopts the new `modified`.
  - **Equal/older** → ignore (this is the echo of the user's own save, or out-of-order).
- **Self-save suppression** works on the timestamp alone: after the user's own save we reload and adopt the latest `modified`, so the inbound echo compares equal → no banner. (`doc_update` carries no `user`, so timestamp comparison is the mechanism — and it's sufficient.)
- **Subscribe/unsubscribe lifecycle (verified):** `AppLayout.vue:19` keys the view by `$route.path`, so `DocDetail` **fully remounts on every `:id` change** → `onBeforeUnmount` is guaranteed to fire. So **subscribe in `loadAll()` after the doc loads (~`DocDetail.vue:1972`)** and **unsubscribe in the existing `onBeforeUnmount` (~`:2057`)**. **No `id` watcher is needed** for teardown — the remount makes cleanup automatic. (The composable's ref-counting still de-dupes the shared socket.)

**Why a banner, not a modal:** the requirement says "popup with a refresh button." A modal that interrupts typing is hostile during data entry. Recommended default: a **persistent inline banner at the top of the form** (dismissible, with Refresh). *Decision flagged in §9 — switch to a true modal dialog if you prefer the harder interrupt.*

---

## 6. Feature B — List view (all doctypes via `DynamicListPage.vue`)

- On mount: `onListUpdate(doctype, cb)` (joins `doctype:<dt>`).
- On event matching the current doctype: **debounced (500 ms) `listState.fetch()`** — which already re-applies the *current* filters, tabs, search, sort, pagination. Also call `loadCounts()` to refresh tab badges. **No popup** (per requirement).
- **In-place merge is explicitly rejected.** Re-running `fetch()` is the safe path: a new/edited/deleted row may or may not belong to the current filtered+sorted+paged view, and blind insertion would corrupt offsets, sort order, and filter scoping. Debounced refetch reuses the battle-tested query and **preserves every list feature** (filters / tabs / search / sort / pagination / bulk / columns). This directly honors the standing rule: *do not change how any doctype renders into the list view.*

### Selection-aware refresh (UX safety)
Auto-refetching while the user has rows checked for a bulk action would drop their selection. Recommended default:
- **No selection active** → debounced auto-refetch (seamless).
- **Selection active** (`selectedRows.length > 0`) → **do not yank the table.** Show a subtle pill *"New updates available — Refresh"*; refetch automatically once the selection clears, or immediately if the user clicks the pill.

*Decision flagged in §9.*

---

## 7. Files touched

| File | Change | Type |
| --- | --- | --- |
| `frontend/package.json` | add `socket.io-client@^4.7.x` | dep |
| `frontend/src/composables/useRealtime.js` | **new** singleton socket composable | new |
| `frontend/src/api/client.js` | enrich thrown error with `exc_type`/status; `submitDoc`/`cancelDoc` accept + send `modified` | edit |
| `frontend/src/composables/useDoc.js` | thread `doc.value.modified` into `submit()`/`cancel()` | edit |
| `frontend/src/views/dynamic/DocDetail.vue` | (a) `buildPayload` adds `modified` on edit; (b) conflict (`exc_type`) → friendly banner + Refresh; (c) subscribe `doc_update` → stale banner | edit |
| `frontend/src/views/dynamic/DynamicListPage.vue` | subscribe `list_update` → debounced `fetch()` + `loadCounts()`, selection-aware | edit |
| `mgk_clothing_yrp/www/web.py` | `get_boot()` adds `socketio_port` | edit (1 line) |
| `mgk_clothing_yrp/api/work_order.py` | `calculate_deliverables` (+ `approve`/`reject`) accept `modified` + pre-flight `TimestampMismatchError` (§A1.1) | edit (backend) |

The two shared frontend components mean the feature lands on **every doctype at once**, satisfying "all doctypes, everywhere," with zero per-doctype code. The only per-doctype backend touch is the Work Order custom-method guard (§A1.1) — the one doctype with a non-PUT write path.

---

## 8. Edge cases & decisions baked in

- **Own save echo** → suppressed by timestamp compare (§A2).
- **Submit/cancel** → guarded the same way as save (`modified` threaded through `submitDoc`/`cancelDoc`, §A1); the `doc_update` banner also fires for another user's submit/cancel, and Refresh re-derives the submit/cancel button state from the new `docstatus`.
- **Custom action methods** (`calculate_deliverables` etc.) → guarded by the §A1.1 backend pre-flight, not the payload — enumerated explicitly because they don't go through the REST PUT.
- **Socket down / blocked** → SPA behaves exactly as today; the §3/§A1 hard guard still prevents clobbering. No hard dependency on realtime for correctness.
- **Permission scoping** → rooms are server-side permission-checked; a user only receives events for docs/doctypes they can read. No client-side leak.
- **Reconnect storms** → `reconnectionAttempts` capped; on reconnect we re-emit current subscriptions.
- **Many rapid list changes** → 500 ms debounce coalesces into one refetch (mirrors Desk's `debounced_refresh`).
- **Hot-doctype fanout at scale (Q5)** → with thousands of users on a busy `doctype:<dt>` room, every save fans out to all of them → a debounced refetch each. **v1 decision: accept** — the 500 ms per-client debounce bounds it and a 20-row refetch is cheap. *v2 optimization (documented, not built):* skip the refetch when the changed `name` provably can't fall in the current filtered+sorted page (compare against the in-memory page window). Not v1.
- **socketio process not running** (dev) → prerequisite: `bench start` runs it; document this; feature silently no-ops otherwise.

---

## 9. Open decisions (recommended defaults chosen; override any)

1. **Detail notice style** — *Recommended:* dismissible **inline banner** with Refresh (non-interrupting). Alternative: blocking modal dialog. → choose.
2. **List refresh while a bulk selection is active** — *Recommended:* defer with a "New updates" pill, don't drop selection. Alternative: always auto-refresh immediately. → choose.
3. **Scope of doctypes** — *Recommended:* enable everywhere (both shared components) since the requirement says "all doctypes." No exclusions. → confirm.
4. **Conflict recovery** — *Recommended (phase 1):* Refresh discards local edits (user re-applies). A field-level merge/diff is **out of scope** for v1 (large effort). → confirm deferral.
5. **Custom-method guard (§A1.1) in v1?** — *Recommended:* yes for `calculate_deliverables` (real clobber surface on Work Order); `approve`/`reject` ride along (same 3-line pattern) or defer (approval-state only). → confirm.

---

## 10. Verification plan (per bench discipline — measured, not eyeballed)

1. **Hard guard:** two authenticated sessions (Playwright contexts). Both open the same Work Order. A saves; B saves stale → assert the save is rejected with **`exc_type === "TimestampMismatchError"`** (HTTP **417**) + friendly banner + Refresh restores B to latest. Assert that with the fix removed (no `modified` in payload), B's save *clobbers silently* (proves the bug existed).
2. **Detail live notice:** B viewing a draft; A submits it → assert banner appears on B within ~1s, `doc.value.modified` unchanged until Refresh, Refresh adopts new `modified` + updated `docstatus`.
3. **Self-save no false positive:** A saves twice → assert no banner shown to A.
4. **List live update:** B on a list (with an active filter + a non-default sort + page 2); A creates/edits a matching record → assert the list refetches within debounce, **filters/sort/page preserved**, tab counts updated, **no popup**.
5. **List selection safety:** B has rows selected; A changes a record → assert selection is **not** dropped and the "updates" pill appears.
6. **Submit/cancel guard:** B opens a draft; A edits (or submits) it; B submits stale → assert rejected with `exc_type === "TimestampMismatchError"`, not silently accepted as `update_after_submit`.
7. **Custom-method guard (§A1.1):** B opens a Work Order; A changes it; B clicks **Calculate Deliverables** stale → assert `calculate_deliverables` raises `TimestampMismatchError` (and, with the fix removed, that it clobbers — proving the bypass existed).
8. **Regression:** full list feature sweep (filters/tabs/search/sort/pagination/bulk/columns) unchanged; detail Details/Address&Contact/Linked tabs unchanged; **zero console errors**.
9. **Degrade:** kill socketio → assert SPA fully functional and the hard guard still rejects stale writes.

---

## 11. Rollout & risk

- **Risk: low-to-moderate.** Additive composable + two seams in shared frontend components + one boot line + a scoped Work Order backend guard. The only behavior *change* to existing flows is the §3/§A1 fix (which converts a silent clobber into a correct rejection — strictly safer).
- **>50-line change across the bench** → mandatory `superpowers:requesting-code-review` before "done" (CLAUDE.md rule 6). (Confirmed: a fresh-context reviewer is the agreed division of labor — one implementer, one independent reviewer.)
- **Phasing:**
  1. **Hard write guard** [highest value, no socket]: `modified` on save + submit + cancel, the `exc_type` conflict UX, **and** the §A1.1 custom-method guard. Pure data-safety; ships and verifies on its own.
  2. **`useRealtime` + detail live banner**: socket connect, `doc_subscribe`, stale notice.
  3. **List live refresh**: `doctype_subscribe`, debounced `fetch()`, selection-aware pill.
  Each phase independently shippable and verifiable.
