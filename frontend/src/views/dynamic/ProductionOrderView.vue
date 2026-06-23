<!--
  ProductionOrderView — the Production Order grid editor (R2).

  PrimeVue port of apps/yrp/yrp/public/js/ProductionOrder/ProductionOrderTable.vue
  (the heaviest production editor) + the mount/round-trip contract in
  production_order.js. Drives the submittable Production Order doctype, whose
  hidden `item_details` Long Text field carries the grouped grid JSON.

  What this surface does
  ----------------------
  A Production Order is a set of item blocks. Each block picks an Item and shows a
  matrix: ROW-ATTRIBUTES (one row per attribute-value combination, e.g. Colour) ×
  the GRID-ATTRIBUTE (one column per value, e.g. Size), with a quantity per
  intersection. Blocks where the item has no row-attributes collapse to a single
  qty row across the grid columns; items with no grid-attribute collapse to one
  scalar qty. Settings (which attributes are active + which is the grid attribute)
  come from YRP Settings; the per-item attribute split comes from
  get_item_production_attributes(item).

  HTTP LOAD SOURCE (resolved — see report)
  ----------------------------------------
  frappe.client.get (what api/client.js getDoc uses) does NOT run onload, so
  __onload.item_details / __onload.production_settings are unavailable that way.
  The PERSISTED `item_details` field is the lean get_final_output() shape
  ([{item, entries:[{attributes, qty}]}]) — it is MISSING grid_attribute /
  grid_attribute_values / row_attributes that load_data needs. So we load via
  `frappe.desk.form.load.getdoc`, which runs onload and returns, on
  frappe.response.docs[0].__onload:
    - production_settings  → set_settings equivalent
    - item_details         → fetch_production_order_items() output (the ENRICHED
                             grouped shape load_data consumes — server stamps
                             grid_attribute / grid_attribute_values /
                             row_attributes per item from get_item_production_attributes)
  getdoc appends to frappe.response.docs (NOT `message`), so we read it with a raw
  fetch (same convention as api/client.js getMeta), not callMethod.

  ROUND-TRIP (RISK FLAG 4 — reproduced EXACTLY)
  ---------------------------------------------
  - loadData(data): identical algorithm to ProductionOrderTable.load_data — per
    group, branch on (grid_attr, rowAttrKeys): both → group entries into rows by
    the row-attribute key (ra=val|…) and scatter each entry's grid value into
    row.qty[gv]; grid only → one row, scatter qty by grid value; neither → one row
    with qty._default = sum of entry quantities.
  - getFinalOutput(): identical to ProductionOrderTable.get_final_output — per
    block with an item, per row, if grid_attr: emit one entry per grid value with
    qty > 0 (attrs = {...row.attrs, [grid_attr]: gv}); else emit one entry with
    qty._default if > 0. Groups with no entries are dropped. Result is the lean
    [{item, entries:[{attributes, qty}]}] shape → JSON.stringify → item_details.
  Save sends { ...header, item_details } via useDoc; the server's before_validate
  runs save_production_order_items() to (re)build the flat production_order_details
  child rows. We never write child rows ourselves.

  Actions (perm-gated, mirror DocDetail §7.1): Save (canWrite), Submit (canSubmit),
  Cancel (canCancel) — Production Order is submittable. id === "new" → create mode
  (blank, then POST + router.replace to the real name). Submitted/cancelled →
  read-only grid (matches set_edit(false) when docstatus !== 0).

  APIs (reused over HTTP; we do NOT import the Desk bundle / cur_frm / make_control)
  ---------------------------------------------------------------------------------
  - frappe.desk.form.load.getdoc → doc + __onload (settings + enriched item_details)
  - production_order.get_production_order_settings() → {attributes, grid_attribute,
    dependent_attribute, dependent_attribute_value} (create mode / fallback)
  - production_order.get_item_production_attributes(item) → {grid_attribute,
    grid_attribute_values, row_attributes, all_attributes} (on item select).
    NOTE: row_attributes is already {attr: [value-list]} (the server runs
    get_attribute_values), so the add-combination dropdowns read their options
    straight from block.row_attributes[attr] — no extra per-cell query (we avoid
    the Desk's positional-signature item.get_item_attribute_values link helper,
    which is awkward over HTTP, exactly as the R1a editor avoided its query helper).
-->
<template>
	<div class="po-view">
		<!-- Breadcrumb -->
		<nav class="crumbs">
			<a @click="goHome">Home</a>
			<span class="sep">/</span>
			<a @click="goList">Production Order</a>
			<span class="sep">/</span>
			<span class="crumb-cur mgk-mono">{{ isCreate ? "New" : id }}</span>
		</nav>

		<!-- Header -->
		<div class="detail-head">
			<div class="id-block">
				<div class="doc-id mgk-mono">
					<span v-if="isCreate">New Production Order</span>
					<span v-else>{{ id }}</span>
				</div>
				<div class="doc-title">
					Production Order grid
					<span v-if="grandTotal > 0"> · {{ formatNumber(grandTotal) }} pcs</span>
				</div>
			</div>

			<Tag
				v-if="!loading && !isCreate"
				class="head-status"
				:value="statusLabel"
				:severity="statusSeverity"
				rounded
			/>

			<div class="head-actions">
				<!-- draft (docstatus 0) or create -->
				<Button
					v-if="!readonly && canWrite('Production Order')"
					:label="isCreate ? 'Create' : 'Save'"
					icon="pi pi-check"
					size="small"
					:loading="saving"
					:disabled="loading || !!loadError"
					@click="onSave"
				/>
				<Button
					v-if="!isCreate && docstatus === 0 && canSubmit('Production Order')"
					label="Submit"
					icon="pi pi-arrow-right"
					iconPos="right"
					size="small"
					severity="secondary"
					outlined
					:loading="acting === 'submit'"
					:disabled="loading || !!loadError"
					@click="onSubmit"
				/>
				<!-- submitted (docstatus 1) -->
				<Button
					v-if="!isCreate && docstatus === 1 && canCancel('Production Order')"
					label="Cancel"
					icon="pi pi-ban"
					size="small"
					severity="danger"
					outlined
					:loading="acting === 'cancel'"
					@click="onCancel"
				/>
				<a v-if="!isCreate" class="desk-link" :href="deskUrl" target="_blank" rel="noopener">
					<i class="pi pi-external-link" /> Open in Desk
				</a>
			</div>
		</div>

		<!-- Loading / error -->
		<div v-if="loading" class="state-block">
			<i class="pi pi-spin pi-spinner" style="font-size: 1.5rem" />
			<span>Loading…</span>
		</div>

		<Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

		<template v-else>
			<!-- ── Header fields ── -->
			<section class="panel">
				<div class="panel-head"><h3>Order</h3></div>
				<div class="hdr-grid">
					<div class="fld-wrap">
						<label>Delivery Date <span class="req">*</span></label>
						<DatePicker
							:modelValue="toDateObj(header.delivery_date)"
							@update:modelValue="header.delivery_date = fromDateObj($event)"
							:disabled="readonly"
							dateFormat="dd-mm-yy"
							showIcon
							iconDisplay="input"
							fluid
						/>
					</div>
					<div class="fld-wrap">
						<label>Don't Deliver After <span class="req">*</span></label>
						<DatePicker
							:modelValue="toDateObj(header.dont_deliver_after)"
							@update:modelValue="header.dont_deliver_after = fromDateObj($event)"
							:disabled="readonly"
							dateFormat="dd-mm-yy"
							showIcon
							iconDisplay="input"
							fluid
						/>
					</div>
					<div class="fld-wrap">
						<label>Posting Date</label>
						<div class="fld-static">{{ formatDate(header.posting_date) || "—" }}</div>
						<small class="fld-hint">Set by the server on submit.</small>
					</div>
					<div class="fld-wrap">
						<label>Production Term</label>
						<AutoComplete
							v-model="header.production_term"
							:suggestions="termSuggestions"
							@complete="searchTerm"
							:disabled="readonly"
							placeholder="Submitted term (optional)"
							dropdown
							fluid
						/>
					</div>
					<div class="fld-wrap">
						<label>Lead Time</label>
						<div class="fld-static">
							<span v-if="leadTimeGivenDisplay != null && leadTimeGivenDisplay !== ''">
								{{ leadTimeGivenDisplay }} day(s)
							</span>
							<span v-else>—</span>
						</div>
					</div>
					<div class="fld-wrap wide">
						<label>Comments</label>
						<InputText v-model="header.comments" :disabled="readonly" placeholder="Optional note" fluid />
					</div>
				</div>
			</section>

			<!-- settings warning -->
			<Message v-if="!settings.attributes.length" severity="warn" :closable="false">
				No attributes are configured in YRP Settings → Production Order Settings. Items can
				still be added with a single quantity, but the size / attribute matrix will not appear.
			</Message>

			<!-- grid meta -->
			<div class="grid-meta">
				{{ items.length }} item block(s)
				<span v-if="grandTotal > 0"> · {{ formatNumber(grandTotal) }} total pcs</span>
			</div>

			<!-- ════════════════ ITEM BLOCKS ════════════════ -->
			<section
				v-for="(block, blockIdx) in items"
				:key="'block-' + blockIdx"
				class="panel po-card"
			>
				<!-- block header -->
				<div class="po-card-header">
					<div class="header-left">
						<div class="index-badge">{{ blockIdx + 1 }}</div>
						<div class="item-selector">
							<!-- Link/search picker (no select chevron). The blank-on-type was
							     NOT this component — it was an unguarded `block.rows[0]` in the
							     grid branches above (now guarded), which crashed while
							     block.item held a partial typed string. So the Link field is
							     restored. -->
							<LinkField
								:model-value="block.item"
								@update:model-value="block.item = $event"
								target-doctype="Item"
								:dropdown="false"
								:disabled="readonly"
								placeholder="Search Item…"
								@item-select="onItemSelected(blockIdx, $event.value)"
								@change="onItemMaybeCleared(blockIdx)"
							/>
						</div>
					</div>
					<div class="header-right">
						<div v-if="block.item && getBlockTotal(block) > 0" class="total-badge">
							<span class="label">Total Qty</span>
							<span class="value">{{ formatNumber(getBlockTotal(block)) }}</span>
						</div>
						<Button
							v-if="!readonly"
							icon="pi pi-times"
							text
							rounded
							severity="danger"
							size="small"
							v-tooltip.left="'Remove item'"
							@click="removeBlock(blockIdx)"
						/>
					</div>
				</div>

				<!-- block body -->
				<div class="po-card-body">
					<!-- grid: row-attributes × grid-attribute -->
					<template v-if="block.item && block.grid_attribute && hasRowAttributes(block)">
						<div class="table-container">
							<table class="grid-table">
								<thead>
									<tr>
										<th v-for="ra in rowAttrNames(block)" :key="'rh-' + ra" class="th-attr">{{ ra }}</th>
										<th v-for="gv in block.grid_attribute_values" :key="'gh-' + gv" class="th-size">{{ gv }}</th>
										<th class="th-total">Total</th>
										<th v-if="!readonly" class="th-action"></th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="(row, rowIdx) in block.rows" :key="'row-' + blockIdx + '-' + rowIdx">
										<td v-for="ra in rowAttrNames(block)" :key="'rv-' + ra" class="td-attr">
											<span class="attr-pill">{{ row.attrs[ra] || "" }}</span>
										</td>
										<td v-for="gv in block.grid_attribute_values" :key="'qc-' + gv" class="td-qty">
											<InputNumber
												v-model="row.qty[gv]"
												:disabled="readonly"
												:minFractionDigits="0"
												:maxFractionDigits="6"
												:min="0"
												class="cell-num"
												inputClass="qty-input"
												fluid
											/>
										</td>
										<td class="td-total">{{ formatNumber(getRowTotal(block, rowIdx)) }}</td>
										<td v-if="!readonly" class="td-action">
											<Button
												icon="pi pi-trash"
												text
												rounded
												severity="danger"
												size="small"
												v-tooltip.left="'Remove row'"
												@click="removeRow(blockIdx, rowIdx)"
											/>
										</td>
									</tr>
								</tbody>
								<tfoot v-if="block.rows.length > 1">
									<tr class="footer-row">
										<td :colspan="rowAttrNames(block).length" class="td-footer-label">Grand Total</td>
										<td v-for="gv in block.grid_attribute_values" :key="'ct-' + gv" class="td-footer-val">
											{{ formatNumber(getColTotal(block, gv)) }}
										</td>
										<td class="td-footer-grand">{{ formatNumber(getBlockTotal(block)) }}</td>
										<td v-if="!readonly" class="td-action"></td>
									</tr>
								</tfoot>
							</table>
						</div>

						<!-- add combination -->
						<div v-if="!readonly" class="add-row-section">
							<div class="add-row-inputs">
								<div v-for="ra in rowAttrNames(block)" :key="'add-ra-' + blockIdx + '-' + ra" class="add-attr-control">
									<Select
										v-model="block._addAttrs[ra]"
										:options="rowAttrOptions(blockIdx, ra)"
										showClear
										filter
										:placeholder="ra"
										fluid
									/>
								</div>
							</div>
							<Button
								label="Add Combination"
								icon="pi pi-plus"
								size="small"
								severity="secondary"
								outlined
								@click="addAttributeRow(blockIdx)"
							/>
						</div>
					</template>

					<!-- grid attribute only (no row attributes) — single row.
					     `block.rows[0]` guard: while the user is still TYPING an item name
					     (block.item is a partial string but the item isn't resolved yet —
					     grid_attribute null, rows empty), this branch must NOT render and
					     bind block.rows[0].qty (undefined → render crash → blank page). -->
					<template v-else-if="block.item && block.grid_attribute && !hasRowAttributes(block) && block.rows[0]">
						<div class="table-container">
							<table class="grid-table">
								<thead>
									<tr>
										<th v-for="gv in block.grid_attribute_values" :key="'gh1-' + gv" class="th-size">{{ gv }}</th>
										<th class="th-total">Total</th>
									</tr>
								</thead>
								<tbody>
									<tr>
										<td v-for="gv in block.grid_attribute_values" :key="'sq-' + gv" class="td-qty">
											<InputNumber
												v-model="block.rows[0].qty[gv]"
												:disabled="readonly"
												:minFractionDigits="0"
												:maxFractionDigits="6"
												:min="0"
												class="cell-num"
												inputClass="qty-input"
												fluid
											/>
										</td>
										<td class="td-total">{{ formatNumber(getRowTotal(block, 0)) }}</td>
									</tr>
								</tbody>
							</table>
						</div>
					</template>

					<!-- no grid attribute — single qty. `block.rows[0]` guard: while the
					     user is still TYPING (item not resolved → rows empty), this branch
					     would bind block.rows[0].qty._default on an empty array and crash
					     the render (blank page). Only render once a row exists. -->
					<template v-else-if="block.item && !block.grid_attribute && block.rows[0]">
						<div class="single-qty-box">
							<label class="qty-label">Enter Quantity</label>
							<InputNumber
								v-model="block.rows[0].qty._default"
								:disabled="readonly"
								:minFractionDigits="0"
								:maxFractionDigits="6"
								:min="0"
								class="single-qty"
								fluid
							/>
						</div>
					</template>

					<!-- initial state -->
					<div v-else class="empty-state">
						<i class="pi pi-inbox" />
						<p>Select an item to see the production grid.</p>
					</div>
				</div>
			</section>

			<!-- add item block -->
			<div v-if="!readonly" class="footer-actions">
				<button class="btn-add-item" @click="addBlock">
					<i class="pi pi-plus" />
					Add Another Item
				</button>
			</div>

			<div v-if="readonly && !items.length" class="empty-state panel">
				<i class="pi pi-inbox" />
				<p>This Production Order has no item rows.</p>
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from "vue"
import { useRouter } from "vue-router"
import Button from "primevue/button"
import Tag from "primevue/tag"
import Message from "primevue/message"
import InputText from "primevue/inputtext"
import InputNumber from "primevue/inputnumber"
import Select from "primevue/select"
import AutoComplete from "primevue/autocomplete"
import DatePicker from "primevue/datepicker"
import Tooltip from "primevue/tooltip"
import LinkField from "@/components/LinkField.vue"
import { callMethod, searchLink } from "@/api/client"
import { useDoc } from "@/composables/useDoc"
import { usePermissions } from "@/composables/usePermissions"
import { useAppConfirm } from "@/composables/useConfirm"
import { useAppToast } from "@/composables/useToast"

const vTooltip = Tooltip

const props = defineProps({
	id: { type: String, required: true },
})

const router = useRouter()
const toast = useAppToast()
const confirm = useAppConfirm()
const { canWrite, canSubmit, canCancel } = usePermissions()

const DOCTYPE = "Production Order"
const docState = useDoc(DOCTYPE)

const isCreate = computed(() => props.id === "new")

// ── reactive model ──
// header: editable scalar fields (mirrors the Desk form's own fields).
const header = reactive({
	delivery_date: "",
	dont_deliver_after: "",
	posting_date: "",
	production_term: "",
	lead_time_given: null,
	comments: "",
})
// settings: { attributes:[], grid_attribute, dependent_attribute, dependent_attribute_value }
// — the production_settings (mirrors ProductionOrderTable.set_settings). Used only
// for the "no attributes configured" warning here (per-item split comes from
// get_item_production_attributes); kept for parity + future use.
const settings = reactive({ attributes: [], grid_attribute: null })
// items: the editor blocks. Each:
//   { item, grid_attribute, grid_attribute_values:[], row_attributes:{attr:[vals]},
//     rows:[{ attrs:{ra:val}, qty:{gridVal:n | _default:n} }],
//     _addAttrs:{ra:val} }
// (_addAttrs is a local UI buffer for the add-combination row's pickers,
//  replacing the Desk's per-control make_control instances.)
const items = ref([])
const docstatus = ref(0)

const loading = ref(false)
const loadError = ref(null)
const saving = computed(() => docState.saving.value)
const acting = ref(null) // "submit" | "cancel" | null

// readonly = submitted/cancelled (mirrors set_edit(false) when docstatus !== 0).
const readonly = computed(() => docstatus.value === 1 || docstatus.value === 2)

// autocomplete buffers
const itemSuggestions = ref([])
const termSuggestions = ref([])

const deskUrl = computed(() => `/app/production-order/${encodeURIComponent(props.id)}`)

const DOCSTATUS_LABELS = { 0: "Draft", 1: "Submitted", 2: "Cancelled" }
const statusLabel = computed(() => DOCSTATUS_LABELS[docstatus.value] || "—")
const statusSeverity = computed(() => {
	if (docstatus.value === 1) return "success"
	if (docstatus.value === 2) return "danger"
	return "warn"
})

const grandTotal = computed(() => {
	let total = 0
	for (const block of items.value) total += getBlockTotal(block)
	return total
})
const leadTimeGivenDisplay = computed(() => {
	const baseDate = header.posting_date || todayStr()
	const days = dateDiffDays(header.delivery_date, baseDate)
	if (days !== null) return days
	return header.lead_time_given
})

// ════════════════ MATRIX HELPERS (mirror ProductionOrderTable) ════════════════
function flt(v) {
	const n = parseFloat(v)
	return Number.isNaN(n) ? 0 : n
}
function hasRowAttributes(block) {
	return Object.keys(block.row_attributes || {}).length > 0
}
function rowAttrNames(block) {
	return Object.keys(block.row_attributes || {})
}
function getRowTotal(block, rowIdx) {
	const row = block.rows[rowIdx]
	if (!row) return 0
	let total = 0
	for (const key in row.qty) total += flt(row.qty[key] || 0)
	return total
}
function getColTotal(block, gv) {
	let total = 0
	for (const row of block.rows) total += flt(row.qty[gv] || 0)
	return total
}
function getBlockTotal(block) {
	let total = 0
	if (!block.rows) return 0
	for (const row of block.rows) {
		for (const key in row.qty) total += flt(row.qty[key] || 0)
	}
	return total
}

// Row-attribute dropdown options for the add-combination row. get_item_production_attributes
// already returns row_attributes as {attr: [value-list]}, so the legal values are
// in-hand — no extra query (mirrors the Desk add_row_attrs picker's value set).
function rowAttrOptions(blockIdx, attr) {
	const block = items.value[blockIdx]
	if (!block?.item) return []
	const vals = block.row_attributes?.[attr]
	return Array.isArray(vals) ? vals : []
}

// ════════════════ BLOCK / ROW ACTIONS ════════════════
function newBlock(overrides = {}) {
	return {
		item: null,
		grid_attribute: null,
		grid_attribute_values: [],
		row_attributes: {},
		rows: [],
		_addAttrs: reactive({}),
		...overrides,
	}
}

function addBlock() {
	items.value.push(newBlock())
}

function removeBlock(blockIdx) {
	items.value.splice(blockIdx, 1)
}

// AutoComplete @change fires on free-text/clear — if the item was cleared, reset
// the block so the empty-state shows (mirrors having no item selected).
function onItemMaybeCleared(blockIdx) {
	const block = items.value[blockIdx]
	if (!block.item) {
		block.grid_attribute = null
		block.grid_attribute_values = []
		block.row_attributes = {}
		block.rows = []
		block._addAttrs = reactive({})
	}
}

// Mirror ProductionOrderTable.on_item_selected: fetch the item's production-attr
// split and (re)seed the block's grid + an initial row when there are no row
// attributes.
async function onItemSelected(blockIdx, itemName) {
	if (!itemName || readonly.value) return
	try {
		const d = await callMethod(
			"yrp.yrp.doctype.production_order.production_order.get_item_production_attributes",
			{ item: itemName },
		)
		if (!d) return
		const block = items.value[blockIdx]
		block.item = itemName
		block.grid_attribute = d.grid_attribute
		block.grid_attribute_values = d.grid_attribute_values || []
		block.row_attributes = d.row_attributes || {}
		block.rows = []
		block._addAttrs = reactive({})

		if (!hasRowAttributes(block)) {
			if (block.grid_attribute) {
				const qty = {}
				for (const gv of block.grid_attribute_values) qty[gv] = 0
				block.rows.push({ attrs: {}, qty })
			} else {
				block.rows.push({ attrs: {}, qty: { _default: 0 } })
			}
		}
	} catch (e) {
		toast.error("Item attributes", e.message)
	}
}

// Mirror ProductionOrderTable.add_attribute_row: validate every row-attr picked,
// reject duplicates, append a zeroed grid row, clear the pickers.
function addAttributeRow(blockIdx) {
	const block = items.value[blockIdx]
	const attrs = {}
	for (const ra of rowAttrNames(block)) {
		const val = block._addAttrs[ra]
		if (!val) {
			toast.warn("Incomplete", `Please select ${ra}.`)
			return
		}
		attrs[ra] = val
	}
	// duplicate check
	for (const row of block.rows) {
		let dup = true
		for (const ra of rowAttrNames(block)) {
			if (row.attrs[ra] !== attrs[ra]) {
				dup = false
				break
			}
		}
		if (dup) {
			toast.warn("Duplicate", "This combination already exists.")
			return
		}
	}
	const qty = {}
	for (const gv of block.grid_attribute_values) qty[gv] = 0
	block.rows.push({ attrs: { ...attrs }, qty })
	// clear pickers
	for (const ra of rowAttrNames(block)) block._addAttrs[ra] = null
}

function removeRow(blockIdx, rowIdx) {
	items.value[blockIdx].rows.splice(rowIdx, 1)
}

// ════════════════ get_final_output (RISK FLAG 4 — EXACT) ════════════════
// Per block with an item, per row: if grid_attr, emit one entry per grid value
// with qty > 0 (attrs = {...row.attrs, [grid_attr]: gv}); else emit one entry with
// qty._default if > 0. Groups with no entries are dropped. Lean shape — no
// settings — matching ProductionOrderTable.get_final_output exactly.
function getFinalOutput() {
	const output = []
	for (const block of items.value) {
		if (!block.item) continue
		const group = { item: block.item, entries: [] }

		for (const row of block.rows) {
			if (block.grid_attribute) {
				for (const gv of block.grid_attribute_values) {
					const qty = flt(row.qty[gv] || 0)
					if (qty <= 0) continue
					const attrs = { ...row.attrs }
					attrs[block.grid_attribute] = gv
					group.entries.push({ attributes: attrs, qty })
				}
			} else {
				const qty = flt(row.qty._default || 0)
				if (qty <= 0) continue
				group.entries.push({ attributes: { ...row.attrs }, qty })
			}
		}

		if (group.entries.length > 0) output.push(group)
	}
	return output
}

// ════════════════ load_data (RISK FLAG 4 — EXACT) ════════════════
// Rebuild the editor blocks from the enriched grouped item_details (the
// fetch_production_order_items shape). Identical branching to
// ProductionOrderTable.load_data.
function loadData(data) {
	const out = []
	if (!data || data.length === 0) {
		items.value = out
		return
	}

	for (const group of data) {
		const block = newBlock({
			item: group.item,
			grid_attribute: group.grid_attribute,
			grid_attribute_values: group.grid_attribute_values || [],
			row_attributes: group.row_attributes || {},
			rows: [],
		})

		const gridAttr = group.grid_attribute
		const rowAttrKeys = Object.keys(group.row_attributes || {})

		if (gridAttr && rowAttrKeys.length > 0) {
			const rowMap = {}
			for (const entry of group.entries || []) {
				const rowKeyParts = []
				const rowAttrs = {}
				for (const ra of rowAttrKeys) {
					const val = entry.attributes[ra] || ""
					rowKeyParts.push(ra + "=" + val)
					rowAttrs[ra] = val
				}
				const rowKey = rowKeyParts.join("|")
				if (!rowMap[rowKey]) {
					const qty = {}
					for (const gv of block.grid_attribute_values) qty[gv] = 0
					rowMap[rowKey] = { attrs: rowAttrs, qty }
				}
				const gvVal = entry.attributes[gridAttr]
				if (gvVal) rowMap[rowKey].qty[gvVal] = flt(entry.qty)
			}
			block.rows = Object.values(rowMap)
		} else if (gridAttr) {
			const qty = {}
			for (const gv of block.grid_attribute_values) qty[gv] = 0
			for (const entry of group.entries || []) {
				const gvVal = entry.attributes[gridAttr]
				if (gvVal) qty[gvVal] = flt(entry.qty)
			}
			block.rows.push({ attrs: {}, qty })
		} else {
			let total = 0
			for (const entry of group.entries || []) total += flt(entry.qty)
			block.rows.push({ attrs: {}, qty: { _default: total } })
		}

		out.push(block)
	}
	items.value = out
}

// ════════════════ LOAD (HTTP via getdoc — runs onload) ════════════════
function getCsrfToken() {
	return window.csrf_token || window.frappe?.csrf_token || ""
}

// Raw fetch of frappe.desk.form.load.getdoc — it appends to frappe.response.docs
// (NOT `message`), so callMethod can't read it. Mirrors api/client.js getMeta's
// reading of `json.docs`. Returns the doc (with __onload) or null.
async function fetchDocWithOnload(name) {
	const res = await fetch(
		`/api/method/frappe.desk.form.load.getdoc?doctype=${encodeURIComponent(DOCTYPE)}&name=${encodeURIComponent(name)}`,
		{
			method: "GET",
			credentials: "include",
			headers: {
				Accept: "application/json",
				"X-Frappe-CSRF-Token": getCsrfToken(),
			},
		},
	)
	if (res.status === 401) {
		window.location.href = "/login"
		throw new Error("Session expired.")
	}
	if (!res.ok) {
		const body = await res.json().catch(() => ({}))
		const serverMessages = body._server_messages
			? JSON.parse(body._server_messages)
					.map((m) => {
						try {
							return JSON.parse(m).message || m
						} catch {
							return m
						}
					})
					.join("\n")
			: null
		throw new Error(serverMessages || body.message || `Failed to load (${res.status})`)
	}
	const json = await res.json()
	const docs = json.docs || []
	return docs[0] || null
}

async function load() {
	loading.value = true
	loadError.value = null
	acting.value = null
	try {
		if (isCreate.value) {
			// Blank header; settings from get_production_order_settings(); one empty block.
			header.delivery_date = ""
			header.dont_deliver_after = ""
			header.posting_date = ""
			header.production_term = ""
			header.lead_time_given = null
			header.comments = ""
			docstatus.value = 0
			await loadSettingsDirect()
			items.value = [newBlock()]
		} else {
			const doc = await fetchDocWithOnload(props.id)
			if (!doc) throw new Error("Not found")
			header.delivery_date = doc.delivery_date || ""
			header.dont_deliver_after = doc.dont_deliver_after || ""
			header.posting_date = doc.posting_date || ""
			header.production_term = doc.production_term || ""
			header.lead_time_given = doc.lead_time_given ?? null
			header.comments = doc.comments || ""
			docstatus.value = Number(doc.docstatus) || 0

			const onload = doc.__onload || {}
			// settings (set_settings): production_settings from onload, else direct.
			const ps = onload.production_settings
			if (ps) {
				settings.attributes = ps.attributes || []
				settings.grid_attribute = ps.grid_attribute || null
			} else {
				await loadSettingsDirect()
			}
			// grid data (load_data): the ENRICHED grouped item_details from onload.
			loadData(onload.item_details || [])
		}
	} catch (e) {
		loadError.value = e.message || "Failed to load"
	} finally {
		loading.value = false
	}
}

async function loadSettingsDirect() {
	try {
		const ps = await callMethod(
			"yrp.yrp.doctype.production_order.production_order.get_production_order_settings",
		)
		settings.attributes = ps?.attributes || []
		settings.grid_attribute = ps?.grid_attribute || null
	} catch (e) {
		settings.attributes = []
		settings.grid_attribute = null
	}
}

// Ctrl/Cmd+S → Save (mirror the Desk + DocDetail shortcut, which the specialized
// editors were missing); Ctrl/Cmd+D → Cancel a submitted order. preventDefault
// stops the browser's "save page" dialog.
function onKeydown(e) {
	const key = (e.key || "").toLowerCase()
	if ((e.ctrlKey || e.metaKey) && key === "s") {
		e.preventDefault()
		if (readonly.value || saving.value) return
		onSave()
	} else if ((e.ctrlKey || e.metaKey) && key === "d") {
		e.preventDefault()
		if (docstatus.value === 1) onCancel()
	}
}
onMounted(() => {
	load()
	window.addEventListener("keydown", onKeydown)
})
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
watch(() => props.id, load)

// ════════════════ SAVE / SUBMIT / CANCEL ════════════════
// Validation mirrors the Desk validate(): item_details must be non-empty.
function buildPayload() {
	const finalItems = getFinalOutput()
	return {
		finalItems,
		payload: {
			delivery_date: header.delivery_date || null,
			dont_deliver_after: header.dont_deliver_after || null,
			production_term: header.production_term || null,
			comments: header.comments || null,
			// Lean grouped JSON → before_validate runs save_production_order_items()
			// to (re)build the flat production_order_details child rows.
			item_details: JSON.stringify(finalItems),
		},
	}
}

function buildValidatedPayload() {
	if (!header.delivery_date) {
		toast.warn("Missing Delivery Date", "Delivery Date is required.")
		return null
	}
	if (!header.dont_deliver_after) {
		toast.warn("Missing date", "Don't Deliver After is required.")
		return null
	}
	const { finalItems, payload } = buildPayload()
	if (!finalItems.length) {
		toast.warn("No items", "Add at least one item with a quantity before saving.")
		return null
	}
	return { finalItems, payload }
}

async function onSave() {
	const built = buildValidatedPayload()
	if (!built) return
	try {
		if (isCreate.value) {
			const result = await docState.save(built.payload)
			const newName = result?.name
			toast.success("Created", newName ? `Production Order ${newName} created` : "Order created")
			if (newName) router.replace(`/production-order/${encodeURIComponent(newName)}`)
		} else {
			await docState.save(built.payload, props.id)
			toast.success("Saved", `${props.id} updated`)
			await load()
		}
	} catch (e) {
		toast.error("Save failed", e.message)
	}
}

function onSubmit() {
	confirm.require({
		header: "Submit Production Order",
		message: `Submit ${props.id}? This validates the order and locks the grid.`,
		acceptLabel: "Submit",
		acceptClass: "p-button-primary",
		accept: async () => {
			acting.value = "submit"
			try {
				const built = buildValidatedPayload()
				if (!built) return
				await docState.save(built.payload, props.id)
				await docState.submit(props.id)
				toast.success("Submitted", `${props.id} submitted`)
				await load()
			} catch (e) {
				toast.error("Submit failed", e.message)
			} finally {
				acting.value = null
			}
		},
	})
}

function onCancel() {
	confirm.require({
		header: "Cancel Production Order",
		message: `Cancel ${props.id}? This reverses the submitted order.`,
		acceptLabel: "Cancel Document",
		acceptClass: "p-button-danger",
		rejectLabel: "Keep",
		accept: async () => {
			acting.value = "cancel"
			try {
				await docState.cancel(props.id)
				toast.success("Cancelled", `${props.id} cancelled`)
				await load()
			} catch (e) {
				toast.error("Cancel failed", e.message)
			} finally {
				acting.value = null
			}
		},
	})
}

// ════════════════ AUTOCOMPLETE QUERIES ════════════════
async function searchItem(e) {
	itemSuggestions.value = await searchNames("Item", e.query)
}
async function searchTerm(e) {
	// Production Term filtered to submitted (mirrors the Desk set_query docstatus 1).
	try {
		const rows = await callMethod("frappe.client.get_list", {
			doctype: "Production Term",
			filters: { docstatus: 1, name: ["like", `%${e.query || ""}%`] },
			fields: ["name"],
			limit_page_length: 20,
			order_by: "name asc",
		})
		termSuggestions.value = (rows || []).map((r) => r.name)
	} catch (_) {
		termSuggestions.value = []
	}
}
async function searchNames(doctype, txt) {
	try {
		const rows = await searchLink(doctype, txt || "")
		return rows.map((r) => r.name)
	} catch (_) {
		return []
	}
}

// ── navigation ──
function goHome() {
	router.push("/home")
}
function goList() {
	router.push("/production-order")
}

// ── date / number helpers (form ↔ Frappe string) — mirror DocDetail ──
function toDateObj(val) {
	if (!val) return null
	const s = String(val).trim()
	const [datePart] = s.split(/[ T]/)
	const [y, m, d] = (datePart || "").split("-").map(Number)
	if (!y || !m || !d) return null
	const obj = new Date(y, m - 1, d)
	return Number.isNaN(obj.getTime()) ? null : obj
}
function fromDateObj(d) {
	if (!d) return ""
	const pad = (n) => String(n).padStart(2, "0")
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function todayStr() {
	return fromDateObj(new Date())
}
function dateDiffDays(to, from) {
	const start = toDateObj(from)
	const end = toDateObj(to)
	if (!start || !end) return null
	const startUtc = Date.UTC(start.getFullYear(), start.getMonth(), start.getDate())
	const endUtc = Date.UTC(end.getFullYear(), end.getMonth(), end.getDate())
	return Math.round((endUtc - startUtc) / 86400000)
}
function formatDate(val) {
	if (!val) return ""
	const datePart = String(val).split(" ")[0]
	const [y, m, d] = datePart.split("-")
	return y && m && d ? `${d}-${m}-${y}` : val
}
function formatNumber(val) {
	const n = Number(val)
	if (Number.isNaN(n)) return String(val)
	return n.toLocaleString("en-IN")
}
</script>

<style scoped>
.po-view {
	display: flex;
	flex-direction: column;
	gap: 14px;
}

/* Breadcrumb + header (mirror DocDetail / the R1a views) */
.crumbs {
	display: flex;
	align-items: center;
	gap: 7px;
	font-size: 12.5px;
	color: var(--mgk-muted);
}
.crumbs a {
	cursor: pointer;
	color: var(--mgk-muted);
}
.crumbs a:hover {
	color: var(--mgk-accent-700);
}
.crumbs .sep {
	color: var(--mgk-muted-2);
}
.detail-head {
	display: flex;
	align-items: flex-start;
	gap: 14px;
}
.id-block {
	display: flex;
	flex-direction: column;
	gap: 3px;
}
.doc-id {
	font-size: 18px;
	letter-spacing: -0.01em;
}
.doc-title {
	font-size: 13px;
	color: var(--mgk-muted);
}
.head-status {
	align-self: center;
}
.head-actions {
	margin-left: auto;
	display: flex;
	gap: 8px;
	align-items: center;
	flex-wrap: wrap;
	justify-content: flex-end;
}
.desk-link {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	font-size: 12.5px;
	color: var(--mgk-accent-700);
	padding: 6px 10px;
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius-sm);
}
.desk-link:hover {
	background: var(--mgk-accent-50);
}

.state-block {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 10px;
	padding: 40px 0;
	color: var(--mgk-muted);
}

/* Panels */
.panel {
	background: var(--mgk-card);
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius);
	overflow: visible; /* allow dropdowns to escape the card */
}
/* Section heads share the Bright Workshop band (light tint; mirrors .mgk-card__head). */
.panel-head {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	padding: 10px 16px;
	background: var(--mgk-accent-50); border-bottom: 1px solid var(--mgk-line);
}
.panel-head::before {
	content: "";
	width: 6px;
	height: 6px;
	border-radius: 999px;
	background: var(--mgk-accent-ink);
	opacity: 0.85;
	flex: 0 0 auto;
}
.panel-head h3 {
	margin: 0;
	font-size: 13px;
	font-weight: 700;
	letter-spacing: 0.02em;
	text-transform: uppercase;
	color: var(--mgk-accent-ink);
}

/* Header grid */
.hdr-grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 16px 24px;
	padding: 16px;
}
@media (max-width: 800px) {
	.hdr-grid {
		grid-template-columns: 1fr;
	}
}
.fld-wrap {
	display: flex;
	flex-direction: column;
	gap: 5px;
	min-width: 0;
}
.fld-wrap.wide {
	grid-column: 1 / -1;
}
.fld-wrap label {
	font-size: 11.5px;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--mgk-muted);
	font-weight: 600;
}
.fld-wrap .req {
	color: var(--mgk-danger);
}
.fld-hint {
	font-size: 11px;
	color: var(--mgk-muted-2);
}
.fld-static {
	font-size: 13.5px;
	color: var(--mgk-ink);
	padding: 6px 0;
}

/* Grid meta */
.grid-meta {
	font-size: 12.5px;
	color: var(--mgk-muted);
	padding: 0 2px;
}

/* ── Item card ── */
.po-card {
	padding: 0;
}
.po-card-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 12px 16px;
	border-bottom: 1px solid var(--mgk-line);
	background: var(--mgk-slate-50);
	border-radius: var(--radius) var(--radius) 0 0;
}
.header-left {
	display: flex;
	align-items: center;
	gap: 12px;
	flex: 1;
	min-width: 0;
}
.index-badge {
	width: 26px;
	height: 26px;
	flex-shrink: 0;
	background: var(--mgk-accent);
	color: #fff;
	border-radius: 50%;
	display: grid;
	place-items: center;
	font-size: 13px;
	font-weight: 700;
}
.item-selector {
	min-width: 240px;
	max-width: 380px;
	flex: 1;
}
.header-right {
	display: flex;
	align-items: center;
	gap: 12px;
}
.total-badge {
	background: var(--mgk-accent-50);
	color: var(--mgk-accent-700);
	padding: 5px 12px;
	border-radius: 999px;
	font-size: 13px;
	font-weight: 600;
	display: flex;
	align-items: center;
	gap: 6px;
}
.total-badge .label {
	opacity: 0.8;
	text-transform: uppercase;
	font-size: 10.5px;
	letter-spacing: 0.04em;
}

.po-card-body {
	padding: 0;
}
.table-container {
	padding: 16px;
	overflow-x: auto;
}

/* ── Grid table ── */
.grid-table {
	width: 100%;
	border-collapse: separate;
	border-spacing: 0;
	font-size: 13px;
}
.grid-table th {
	background: var(--mgk-slate-50);
	padding: 10px 12px;
	color: var(--mgk-muted);
	font-weight: 600;
	text-transform: uppercase;
	font-size: 11px;
	letter-spacing: 0.04em;
	border-bottom: 2px solid var(--mgk-line);
	text-align: center;
	white-space: nowrap;
}
.grid-table .th-attr {
	text-align: left;
}
.grid-table .th-total {
	background: var(--mgk-accent-50);
	color: var(--mgk-accent-700);
}
.grid-table .th-action {
	background: transparent;
	border-bottom: none;
	width: 44px;
}
.grid-table td {
	padding: 6px 8px;
	border-bottom: 1px solid var(--mgk-line);
	vertical-align: middle;
}
.td-attr {
	background: var(--mgk-card);
}
.attr-pill {
	display: inline-block;
	padding: 3px 10px;
	background: var(--mgk-accent-50);
	color: var(--mgk-accent-700);
	border-radius: 6px;
	font-weight: 600;
	font-size: 12px;
}
.td-qty {
	padding: 4px;
	min-width: 84px;
}
.cell-num {
	width: 100%;
}
:deep(.qty-input) {
	text-align: center;
	font-weight: 600;
}
.td-total {
	text-align: center;
	font-weight: 700;
	color: var(--mgk-accent-700);
	background: var(--mgk-accent-50);
}
.td-action {
	text-align: center;
	border-bottom: none;
	width: 44px;
}

/* footer */
.footer-row td {
	background: var(--mgk-slate-50);
	padding: 10px 12px;
	border-top: 2px solid var(--mgk-line);
	border-bottom: none;
}
.td-footer-label {
	text-align: right;
	font-weight: 700;
	color: var(--mgk-muted);
}
.td-footer-val {
	text-align: center;
	font-weight: 700;
}
.td-footer-grand {
	text-align: center;
	font-weight: 800;
	color: var(--mgk-accent-700);
	background: var(--mgk-accent-50);
}

/* add combination */
.add-row-section {
	display: flex;
	align-items: flex-end;
	gap: 12px;
	padding: 14px 16px 18px;
	border-top: 1px dashed var(--mgk-line);
	flex-wrap: wrap;
}
.add-row-inputs {
	display: flex;
	gap: 10px;
	flex-wrap: wrap;
}
.add-attr-control {
	width: 170px;
}

/* single qty */
.single-qty-box {
	padding: 18px 16px;
	max-width: 300px;
}
.qty-label {
	font-size: 11.5px;
	font-weight: 600;
	color: var(--mgk-muted);
	text-transform: uppercase;
	letter-spacing: 0.04em;
	margin-bottom: 6px;
	display: block;
}
.single-qty {
	width: 100%;
}

/* empty state */
.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 8px;
	padding: 34px 16px;
	text-align: center;
	color: var(--mgk-muted);
}
.empty-state .pi {
	font-size: 26px;
	color: var(--mgk-muted-2);
}
.empty-state p {
	margin: 0;
	font-size: 13px;
}

/* add item button */
.footer-actions {
	display: flex;
	justify-content: center;
	padding: 4px 0 8px;
}
.btn-add-item {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 12px 26px;
	background: var(--mgk-card);
	border: 2px dashed var(--mgk-line);
	border-radius: var(--radius);
	color: var(--mgk-muted);
	font-weight: 600;
	font-size: 14px;
	cursor: pointer;
	transition: all 0.2s;
}
.btn-add-item:hover {
	border-color: var(--mgk-accent);
	color: var(--mgk-accent-700);
	background: var(--mgk-accent-50);
}
</style>
