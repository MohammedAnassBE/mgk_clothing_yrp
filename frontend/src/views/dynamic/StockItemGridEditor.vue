<!--
  StockItemGridEditor — the stock size-pivot item editor (R3a, the grouped
  `item_details` path). PrimeVue port of
  apps/yrp/yrp/public/js/Stock/components/ItemDimensionFetch.vue.

  WHAT IT IS
  ----------
  A pivot editor for stock-voucher child rows. You pick a PARENT item, the
  server tells us its primary attribute (e.g. Size) + the legal values
  (S/M/L = the COLUMNS), and you type a qty per size cell. We NEVER store a
  variant here — we store the parent item + the attribute values, and the
  server's ungroup_items_from_ui (save_stock_items.py) resolves/creates the
  Item Variant on save. This is the OPPOSITE of DocDetail's flat grid: there
  we sent flat variant rows; here we emit the grouped JSON and leave the flat
  child field empty.

  INTERNAL STATE  ==  the grouped structure from save_stock_items.py
  ------------------------------------------------------------------
  `groups` is exactly the shape group_items_for_ui produces / ungroup_items_from_ui
  consumes (worked example at save_stock_items.py ~147-205):

    [
      {
        attributes: ["Colour"],          // group-level non-primary attr NAMES
        primary_attribute: "Size",
        primary_attribute_values: ["S","M","L"],   // the pivot COLUMNS
        items: [
          {
            name: "T-Shirt",             // PARENT item (never a variant)
            dimensions: { lot: "LOT-1", received_type: "Fresh" },
            attributes: { Colour: "Red" },          // chosen non-primary values
            primary_attribute: "Size",
            default_uom: "Nos",
            values: { S:{qty:10}, M:{qty:20}, L:{qty:0} },   // per-size cells
            ...entry_fields,             // copied through verbatim on edit
          },
        ],
      },
      // an item with NO primary attribute lands in its own group with
      // values: { default: { qty: 5 } }
    ]

  PUBLIC API (defineExpose)
  -------------------------
  - getItems()        → the grouped JSON array (deep clone) for buildPayload.
  - loadData(grouped) → rebuild internal state from a saved grouped payload
                        (DocDetail does NOT call this in v1 — it only feeds the
                        flat field on read — but it's provided per spec so a
                        future onload that returns grouped JSON round-trips).
  - hasItems()        → convenience for the parent to know if anything's entered.

  APIs (reused over HTTP via callMethod — same as the Desk component)
  -------------------------------------------------------------------
  - yrp.yrp.doctype.item.item.get_attribute_details(item_name)
        → { primary_attribute, primary_attribute_values, attributes, default_uom }
  - yrp.stock.api.get_stock_dimensions_for_ui()
        → [ { fieldname, label, options, mandatory } ]  (lot / received_type …)

  We never write Stock Ledger Entries; the server does variant resolution.
-->
<template>
	<div ref="editorEl" class="stock-grid-editor">
		<!-- ── Existing logical items (grouped pivot view) ── -->
		<div v-if="groups.length" class="grid-groups">
			<div v-for="(group, gi) in groups" :key="'g-' + gi" class="grid-group">
				<DataTable :value="group.items" class="mgk-table pivot-dt" :rowHover="false" :tableStyle="gridTableStyle(group)">
					<Column header="#" :style="{ width: '40px' }">
						<template #body="{ index }">{{ index + 1 }}</template>
					</Column>
					<Column header="Item" :style="{ minWidth: '160px' }">
						<template #body="{ data }">
							<span class="mgk-mono">{{ localizedItem(data.name) }}</span>
						</template>
					</Column>

					<!-- Dimension columns (only those any row in the group fills) -->
					<Column
						v-for="dim in visibleDimensions(group)"
						:key="'gd-' + dim.fieldname"
						:header="dim.label"
					>
						<template #body="{ data }">
							{{ (data.dimensions || {})[dim.fieldname] || "—" }}
						</template>
					</Column>

					<!-- Non-primary attribute columns -->
					<Column
						v-for="attr in group.attributes"
						:key="'ga-' + attr"
						:header="attr"
					>
						<template #body="{ data }">
							{{ (data.attributes || {})[attr] || "—" }}
						</template>
					</Column>

					<!-- Size (primary-attribute value) columns OR a single Qty column -->
					<template v-if="group.primary_attribute && group.primary_attribute_values.length">
						<Column
							v-for="pv in group.primary_attribute_values"
							:key="'gpv-' + pv"
							:header="pv"
							:style="{ width: '92px' }"
						>
							<template #body="{ data }">
								<InputNumber
									v-if="editable && data.values[pv]"
									:modelValue="data.values[pv].qty"
									@update:modelValue="onExistingQtyInput(data, pv, $event)"
									:min="0"
									:max="existingQtyMax(data, pv)"
									:minFractionDigits="0"
									:maxFractionDigits="3"
									class="cell-num"
									inputClass="cell-num-input"
									fluid
								/>
								<span v-else class="cell-ro">{{ cellQty(data, pv) }}</span>
									<template v-if="data.values[pv] && inlineCellFields.length">
										<span v-for="cf in inlineCellFields" :key="'cf-' + cf.name" class="cell-extra">{{ cf.label }}: {{ fmtCell(data.values[pv][cf.name]) }}</span>
									</template>
									<span
										v-if="hasSecondary(data.values[pv])"
										class="cell-extra"
									>Sec: {{ fmtCell(data.values[pv].secondary_qty) }} {{ data.values[pv].secondary_uom }}</span>
							</template>
						</Column>
					</template>
					<template v-else>
						<Column header="Qty" :style="{ width: '110px' }">
							<template #body="{ data }">
								<InputNumber
									v-if="editable && data.values.default"
									:modelValue="data.values.default.qty"
									@update:modelValue="onExistingQtyInput(data, 'default', $event)"
									:min="0"
									:max="existingQtyMax(data, 'default')"
									:minFractionDigits="0"
									:maxFractionDigits="3"
									class="cell-num"
									inputClass="cell-num-input"
									fluid
								/>
								<span v-else class="cell-ro">{{ (data.values.default && data.values.default.qty) || 0 }}</span>
									<template v-if="data.values.default && inlineCellFields.length">
										<span v-for="cf in inlineCellFields" :key="'cf-' + cf.name" class="cell-extra">{{ cf.label }}: {{ fmtCell(data.values.default[cf.name]) }}</span>
									</template>
									<span
										v-if="hasSecondary(data.values.default)"
										class="cell-extra"
									>Sec: {{ fmtCell(data.values.default.secondary_qty) }} {{ data.values.default.secondary_uom }}</span>
							</template>
						</Column>
					</template>

					<Column
						v-for="cf in separateColumnFields"
						:key="'separate-' + cf.name"
						:header="cf.label"
						:style="{ width: isCurrencyCellField(cf) ? '132px' : '112px' }"
					>
						<template #body="{ data }">
							<span class="separate-cell-value" :class="{ money: isCurrencyCellField(cf) }">
								{{ formatSeparateCell(data, cf) }}
							</span>
						</template>
					</Column>

					<Column header="UOM" :style="{ width: '84px' }">
						<template #body="{ data }">{{ data.default_uom || "—" }}</template>
					</Column>

					<Column v-if="showPreviousPrice" header="Previous Price" :style="{ width: '138px' }">
						<template #body="{ data, index }">
							<div v-if="previousPriceLoading" class="previous-price loading">
								<i class="pi pi-spin pi-spinner" />
							</div>
							<div v-else class="previous-price">
								<span
									v-for="line in previousPriceLines(gi, index, data, group)"
									:key="line.key"
									v-tooltip.bottom="line.tooltip"
									:class="{ empty: line.rate === null }"
								>
									<small v-if="line.label">{{ line.label }}</small>
									{{ line.rate === null ? "No history" : `₹ ${fmtPrice(line.rate)}` }}
								</span>
							</div>
						</template>
					</Column>

					<Column v-if="editable && !lockedItems" :style="{ width: '88px' }" bodyStyle="text-align:center">
						<template #body="{ index }">
							<Button
								icon="pi pi-pencil"
								text
								rounded
								severity="secondary"
								size="small"
								@click="startEdit(gi, index)"
								v-tooltip.left="'Edit item'"
							/>
							<Button
								icon="pi pi-trash"
								text
								rounded
								severity="danger"
								size="small"
								@click="removeItem(gi, index)"
								v-tooltip.left="'Remove item'"
							/>
						</template>
					</Column>

					<template #empty>
						<div class="grid-empty">No items in this group.</div>
					</template>
				</DataTable>
			</div>
		</div>
		<div v-else class="grid-empty-state">
			No items yet. {{ editable && !lockedItems ? "Add a parent item below to enter quantities per size." : "" }}
		</div>

		<!-- ── Add-item form ── -->
		<section v-if="editable && !lockedItems" ref="addFormEl" class="add-form">
			<div class="add-head">
				<h4>{{ draft.editing ? "Edit item" : (draft.parentItem ? `Configure ${localizedItem(draft.parentItem)}` : "Add item") }}</h4>
				<span v-if="loadingAttrs" class="add-loading">
					<i class="pi pi-spin pi-spinner" /> resolving attributes…
				</span>
			</div>

			<!-- Dimensions + item picker -->
			<div class="add-row">
				<div
					v-for="dim in entryDimensions"
					:key="'dimctl-' + dim.fieldname"
					class="add-fld"
					:data-focus-key="`dimension:${dim.fieldname}`"
				>
					<label>
						{{ dim.label }}<span v-if="dim.mandatory" class="req"> *</span>
					</label>
					<AutoComplete
						v-model="draft.dimensions[dim.fieldname]"
						:suggestions="dimSuggestions[dim.fieldname] || []"
						@complete="searchDimension(dim, $event)"
						:placeholder="dim.label"
						dropdown
						completeOnFocus
						fluid
					/>
				</div>

				<div class="add-fld item-fld" data-focus-key="item">
					<label>Item <span class="req">*</span></label>
					<LinkField
						v-model="draft.parentItem"
						target-doctype="Item"
						:filters="itemFilters"
						@item-select="onParentItemSelected"
						@change="onParentItemMaybeCleared"
						placeholder="Parent item"
					/>
				</div>
			</div>

			<!-- Once a parent item is resolved: its attributes + the qty pivot -->
			<template v-if="draft.parentItem && draft.resolved">
				<!-- Dependent attribute (e.g. Stage) selector — pick a stage first -->
				<div v-if="draft.dependentAttribute" class="add-row attr-row">
					<div class="add-fld" data-focus-key="dependent">
						<label>{{ draft.dependentAttribute }} <span class="req">*</span></label>
						<Select
							v-model="draft.dependentValue"
							:options="dependentOptions"
							@change="onStageChange"
							:placeholder="'Select ' + draft.dependentAttribute"
							showClear
							fluid
						/>
					</div>
				</div>

				<!-- Attributes + qty: for a dependent item, only after a stage is chosen -->
				<template v-if="!draft.dependentAttribute || draft.dependentValue">
				<!-- Non-primary attribute selects (must be set to identify the variant) -->
				<div v-if="draft.attributes.length" class="add-row attr-row">
					<div
						v-for="attr in draft.attributes"
						:key="'attrctl-' + attr"
						class="add-fld"
						:data-focus-key="`attribute:${attr}`"
					>
						<label>{{ attr }} <span class="req">*</span></label>
						<AutoComplete
							v-model="draft.attributeValues[attr]"
							:suggestions="attrValueSuggestions[attr] || []"
							@complete="searchAttributeValue(attr, $event)"
							:placeholder="attr"
							dropdown
							completeOnFocus
							fluid
						/>
					</div>
				</div>

				<!-- Opt-in "Update Secondary" toggle. On flip ON, the editor fetches
				     the Item's secondary_unit_of_measure (one UOM per row, shown as
				     a label) and Secondary Qty becomes an editable per-cell input.
				     Hidden entirely when the parent doctype doesn't carry secondary
				     fields (showSecondaryToggle=false). -->
				<div v-if="showSecondaryToggle" class="add-row sec-row">
					<div class="add-fld toggle-fld">
						<label>Update Secondary</label>
						<ToggleSwitch
							:modelValue="!!draft.updateSecondary"
							@update:modelValue="onUpdateSecondaryToggle($event)"
						/>
					</div>
					<div v-if="draft.updateSecondary && draft.secondaryUom" class="add-fld">
						<label>Secondary UOM</label>
						<div class="sec-uom-display">{{ draft.secondaryUom }}</div>
					</div>
					<div v-else-if="draft.updateSecondary && !draft.secondaryUom" class="add-fld">
						<label>&nbsp;</label>
						<div class="sec-uom-display muted">No Secondary UOM on this item</div>
					</div>
				</div>

				<!-- Qty pivot — one cell per primary-attribute value (the sizes).
				     Each cell renders the qty input + a numeric input per cellFields
				     entry tagged `editable: true` (rate / …) + an optional Secondary
				     Qty input when Update Secondary is on. Mirrors the Desk
				     ItemDimensionFetch.vue per-primary-value loop AND the production_api
				     DC deliverable_items.vue per-cell secondary_qty input. -->
				<div v-if="draft.primaryAttribute && draft.primaryValues.length" class="qty-pivot">
					<div
						v-for="pv in draft.primaryValues"
						:key="'qty-' + pv"
						class="qty-cell"
						:data-focus-key="`quantity:${pv}`"
					>
						<label>{{ pv }}</label>
						<span class="qty-uom">{{ draft.defaultUom || "" }}</span>
						<InputNumber
							v-model="draft.values[pv].qty"
							:min="0"
							:minFractionDigits="0"
							:maxFractionDigits="3"
							class="cell-num"
							fluid
						/>
						<template v-for="cf in editableCellFields" :key="'cf-' + pv + '-' + cf.name">
							<label class="cell-sub">{{ cf.label }}</label>
							<InputNumber
								v-model="draft.values[pv][cf.name]"
								:min="0"
								:minFractionDigits="0"
								:maxFractionDigits="3"
								class="cell-num"
								fluid
							/>
						</template>
						<template v-if="draft.updateSecondary && draft.secondaryUom">
							<label class="cell-sub">Sec Qty</label>
							<InputNumber
								v-model="draft.values[pv].secondary_qty"
								:min="0"
								:minFractionDigits="0"
								:maxFractionDigits="3"
								class="cell-num"
								fluid
							/>
						</template>
					</div>
				</div>
				<!-- No primary attribute → a single qty + the same editable cell fields -->
				<div v-else class="qty-single" data-focus-key="quantity:default">
					<label>{{ draft.defaultUom || "Qty" }} <span class="req">*</span></label>
					<InputNumber
						v-model="draft.values.default.qty"
						:min="0"
						:minFractionDigits="0"
						:maxFractionDigits="3"
						class="cell-num qty-single-input"
						fluid
					/>
					<template v-for="cf in editableCellFields" :key="'cfs-' + cf.name">
						<label class="cell-sub">{{ cf.label }}</label>
						<InputNumber
							v-model="draft.values.default[cf.name]"
							:min="0"
							:minFractionDigits="0"
							:maxFractionDigits="3"
							class="cell-num qty-single-input"
							fluid
						/>
					</template>
					<template v-if="draft.updateSecondary && draft.secondaryUom">
						<label class="cell-sub">Sec Qty ({{ draft.secondaryUom }})</label>
						<InputNumber
							v-model="draft.values.default.secondary_qty"
							:min="0"
							:minFractionDigits="0"
							:maxFractionDigits="3"
							class="cell-num qty-single-input"
							fluid
						/>
					</template>
				</div>

				<!-- Per-row Allow Zero Valuation Rate toggle (mirrors the Desk
				     otherInputs for Stock Reconciliation). -->
				<div v-if="showAllowZeroRate" class="add-row rate-row">
					<div class="add-fld toggle-fld">
						<label>Allow Zero Valuation Rate</label>
						<ToggleSwitch
							:modelValue="!!draft.allow_zero_valuation_rate"
							@update:modelValue="draft.allow_zero_valuation_rate = $event ? 1 : 0"
						/>
					</div>
				</div>

				<div class="add-actions">
					<Button
						:label="draft.editing ? 'Update Item' : 'Add Item'"
						icon="pi pi-plus"
						size="small"
						:loading="pricing"
						:disabled="pricing"
						@click="commitDraft"
					/>
					<Button
						label="Clear"
						icon="pi pi-times"
						size="small"
						severity="secondary"
						text
						@click="resetDraft({ focus: true })"
					/>
				</div>
				</template>
			</template>
		</section>

		<div v-if="editable && groups.length" class="grid-foot">
			{{ totalLogicalItems }} item(s) · {{ totalQty }} total qty
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from "vue"
import DataTable from "primevue/datatable"
import Column from "primevue/column"
import Button from "primevue/button"
import InputNumber from "primevue/inputnumber"
import AutoComplete from "primevue/autocomplete"
import Select from "primevue/select"
import ToggleSwitch from "primevue/toggleswitch"
import Tooltip from "primevue/tooltip"
import { callMethod, searchLink } from "@/api/client"
import { useAppToast } from "@/composables/useToast"
import { useLinkTitles } from "@/composables/useLinkTitles"
import LinkField from "@/components/LinkField.vue"
import { focusFirstControl } from "@/utils/focusControl"

const vTooltip = Tooltip

const props = defineProps({
	// The grouped-JSON field this editor drives (item_details / deliverable_details / …).
	// Carried for clarity / debugging; the editor itself is field-agnostic.
	groupedField: { type: String, default: "item_details" },
	// Per-cell value fields (rate, secondary_qty…) from PARENT_CHILD_MAP.value_fields.
	// Stored on each size-cell so they round-trip; only `qty` is edited in the UI.
	valueFields: { type: Array, default: () => [] },
	// Per-logical-item fields (PARENT_CHILD_MAP.entry_fields) preserved verbatim.
	entryFields: { type: Array, default: () => [] },
	// Per-size value fields. Each entry: { name, label, editable? }.
	// Without `editable`: shown stacked under the qty in each cell as a
	// read-only label (e.g. Pending / Cost / Amount — the WO/PO use case).
	// With `editable: true`: also renders a numeric INPUT in the add-form
	// inside every size cell, bound to `draft.values[pv][name]` — mirrors
	// the Desk's `ItemDimensionFetch.vue` per-primary-value editable fields
	// (rate, secondary_qty for Stock Entry/Update/Reconciliation).
	cellFields: { type: Array, default: () => [] },
	// Move selected read-only cell fields into their own row-level columns.
	// Useful for compact business tables such as PO Pending and Amount.
	separateCellFields: { type: Array, default: () => [] },
	// Optional item-link query filters (passed to searchLink as Frappe filters).
	itemFilters: { type: Object, default: () => ({}) },
	// false → read-only render (used if ever embedded in a view context).
	editable: { type: Boolean, default: true },
	// false → hide the dimension controls/columns entirely.
	showDimensions: { type: Boolean, default: true },
	// Hide dimensions that are assigned by the server rather than entered by
	// the user. Values already present in loaded rows are retained on save.
	hiddenDimensions: { type: Array, default: () => [] },
	// Optional grouped JSON to load on mount / when it changes (read-only view use).
	initialData: { type: [Array, String, Object], default: null },
	// true → render an "Allow Zero Valuation Rate" toggle in the add-form as a
	// per-row entry field. Persisted on the item entry as
	// `allow_zero_valuation_rate` (Frappe's escape hatch for opening-stock
	// entries with rate 0). Matches the Desk's `otherInputs` for Stock
	// Reconciliation.
	showAllowZeroRate: { type: Boolean, default: false },
	// true → render an opt-in "Update Secondary" toggle in the add-form. On
	// toggle ON, fetch Item.secondary_unit_of_measure (one UOM per row, as a
	// label), and render a Secondary Qty input inside every cell next to its
	// qty. On commit, broadcast the fetched UOM to every cell's
	// `secondary_uom`. Mirrors the production_api Delivery Challan flow
	// (deliverable_items.vue `get_check_value`). Secondary fields are
	// optional — when the toggle is OFF, no secondary_uom / secondary_qty
	// leaves the editor (so the server doesn't reject a `secondary_uom: 0`).
	showSecondaryToggle: { type: Boolean, default: false },
	// true → composition is LOCKED. Hides the row-action column (delete +
	// reload-into-draft Edit) AND the Add Item section, so the user can only
	// edit per-cell qty / rate / Sec Qty of items already in the grid. Used
	// for vouchers whose item set is derived from a parent doc (DC's items
	// come from the WO; the user only adjusts qtys).
	lockedItems: { type: Boolean, default: false },
	// Purchase Order parity with Desk: supplier controls the active Item Price.
	// Opt-in props keep every other stock pivot's behaviour unchanged.
	priceSupplier: { type: String, default: "" },
	applyAvailablePrice: { type: Boolean, default: false },
	// Purchase Order comparison aid. This is derived server-side from the most
	// recent earlier submitted PO and is never written into the child rows.
	showPreviousPrice: { type: Boolean, default: false },
	currentDocument: { type: String, default: "" },
})

const toast = useAppToast()
const linkTitles = useLinkTitles()

// Q6: let the parent (DocDetail) treat grid edits as "unsaved changes". The grid
// keeps its own state (not in the parent `form`), so without this a quantity/rate
// edit wouldn't trip the parent's dirty guard. We emit `change` on genuine user
// edits to `groups` (cell qty/rate, add/delete row) — armed AFTER loadData/mount
// so the programmatic hydration/seed never false-fires.
const emit = defineEmits(["change", "summary"])
const changeArmed = ref(false)

// ── grouped state (== save_stock_items.py shape) ──
const groups = ref([])

watch(
	groups,
	() => {
		if (changeArmed.value) emit("change")
		emit("summary", buildSummary())
	},
	{ deep: true },
)

// ── dimension config (lot / received_type …) ──
const dimensions = ref([])
const entryDimensions = computed(() => {
	const hidden = new Set(props.hiddenDimensions || [])
	return dimensions.value.filter((dim) => !hidden.has(dim.fieldname))
})

// ── add-item draft ──
const blankDraft = () => ({
	parentItem: "",
	resolved: false, // true once get_attribute_details returned
	editing: false, // true while re-editing an existing row (Update vs Add)
	dimensions: {}, // { fieldname: value }
	attributes: [], // non-primary attribute NAMES (stage-filtered when dependent)
	attributeValues: {}, // { attrName: value }
	primaryAttribute: "",
	primaryValues: [], // the size columns
	defaultUom: "",
	itemDefaultUom: "", // item-level default UOM (fallback when a stage has none)
	// Dependent-attribute (e.g. Stage) support: when set, the user first picks a
	// stage, then only that stage's attributes + per-stage primary are shown.
	dependentAttribute: "", // dependent attribute NAME (e.g. "Stage") or ""
	dependentValue: "", // chosen stage value
	dependentDetails: null, // { attribute, attr_list: { stage: {attributes, uom, primary_attribute, primary_attribute_values} } }
	values: { default: { qty: 0 } }, // { sizeVal: {qty, ...cellFields}, … } or { default: {qty} }
	// Per-row Allow-Zero-Valuation toggle. Stored on the item entry as
	// allow_zero_valuation_rate (Frappe's entry field for the no-rate path).
	allow_zero_valuation_rate: 0,
	// Per-row "Update Secondary" opt-in: when on, the editor renders a
	// Secondary Qty input inside every cell and stamps secondary_uom on each
	// cell from the item's Item.secondary_unit_of_measure (auto-fetched).
	updateSecondary: false,
	secondaryUom: "", // fetched from Item once the user picks one and toggles on
})
const draft = reactive(blankDraft())
const loadingAttrs = ref(false)
const pricing = ref(false)
const previousPriceLoading = ref(false)
const previousPrices = ref({})
const editorEl = ref(null)
const addFormEl = ref(null)
let previousPriceRequest = 0

// ── autocomplete buffers ──
const attrValueSuggestions = reactive({}) // { attrName: [values] }
const dimSuggestions = reactive({}) // { fieldname: [values] }

// ════════════════ MOUNT ════════════════
onMounted(async () => {
	if (props.showDimensions) await loadDimensions()
	if (props.initialData != null) loadData(props.initialData)
	// Arm change-emit after the initial (programmatic) state settles. A later
	// external loadData() (parent hydrate/autofill) re-disarms then re-arms.
	nextTick(() => { changeArmed.value = true })
})

// Read-only view use: (re)load when the grouped data arrives/changes.
watch(
	() => props.initialData,
	(v) => {
		if (v != null) loadData(v)
	},
)

async function loadDimensions() {
	try {
		const dims = await callMethod("yrp.stock.api.get_stock_dimensions_for_ui")
		dimensions.value = Array.isArray(dims) ? dims : []
	} catch (_) {
		dimensions.value = []
	}
}

// ════════════════ DERIVED ════════════════
const totalLogicalItems = computed(() =>
	groups.value.reduce((n, g) => n + (g.items?.length || 0), 0),
)
const totalQty = computed(() => {
	let t = 0
	for (const g of groups.value) {
		for (const it of g.items || []) {
			for (const v of Object.values(it.values || {})) t += Number(v?.qty) || 0
		}
	}
	return t
})

const previousPriceSignature = computed(() => JSON.stringify(
	groups.value.map((group) => ({
		items: (group.items || []).map((item) => ({
			name: item.name,
			attributes: item.attributes || {},
			primary_attribute: item.primary_attribute || "",
			values: Object.fromEntries(
				Object.entries(item.values || {})
					.filter(([, value]) => Number(value?.qty) > 0)
					.map(([key]) => [key, 1]),
			),
		})),
	})),
))

watch(
	[
		() => props.showPreviousPrice,
		() => props.priceSupplier,
		() => props.currentDocument,
		previousPriceSignature,
	],
	loadPreviousPrices,
	{ immediate: true },
)

async function loadPreviousPrices() {
	const request = ++previousPriceRequest
	if (!props.showPreviousPrice || !props.priceSupplier || !groups.value.length) {
		previousPrices.value = {}
		previousPriceLoading.value = false
		return
	}
	previousPriceLoading.value = true
	try {
		const prices = await callMethod(
			"mgk_clothing_yrp.mgk_clothing_yrp.api.purchase_order.get_previous_purchase_prices",
			{
				item_details: JSON.stringify(groups.value),
				supplier: props.priceSupplier,
				current_purchase_order: props.currentDocument || null,
			},
		)
		if (request === previousPriceRequest) previousPrices.value = prices || {}
	} catch (_) {
		if (request === previousPriceRequest) previousPrices.value = {}
	} finally {
		if (request === previousPriceRequest) previousPriceLoading.value = false
	}
}

function previousPriceLines(groupIndex, itemIndex, item, group) {
	const keys = group.primary_attribute && group.primary_attribute_values?.length
		? group.primary_attribute_values.filter((key) => Number(item.values?.[key]?.qty) > 0)
		: ["default"]
	if (!keys.length) return [{ key: "empty", label: "", rate: null, tooltip: "No earlier submitted Purchase Order" }]
	return keys.map((key) => {
		const history = previousPrices.value[`${groupIndex}:${itemIndex}:${key}`]
		return {
			key,
			label: keys.length > 1 ? key : "",
			rate: history?.rate === undefined ? null : Number(history.rate),
			tooltip: history
				? `${history.purchase_order} · ${history.po_date || "date unavailable"}`
				: "No earlier submitted Purchase Order",
		}
	})
}

function fmtPrice(value) {
	const number = Number(value)
	return Number.isNaN(number)
		? String(value)
		: number.toLocaleString("en-IN", { maximumFractionDigits: 3 })
}

function buildSummary() {
	let itemCount = 0
	let qty = 0
	let pendingQty = 0
	let grandTotal = 0
	for (const group of groups.value) {
		itemCount += group.items?.length || 0
		for (const item of group.items || []) {
			for (const value of Object.values(item.values || {})) {
				const received = Number(value?.qty) || 0
				qty += received
				pendingQty += Number(value?.pending_quantity) || 0
				grandTotal += Number(value?.total_amount ?? value?.amount) || received * (Number(value?.rate) || 0)
			}
		}
	}
	return { itemCount, totalQty: qty, pendingQty, grandTotal }
}

// cellFields entries flagged `editable: true` get a per-cell numeric input in
// the add-form (rate, secondary_qty…). A host may promote selected read-only
// values into dedicated columns; the remaining values stay beneath Quantity.
const editableCellFields = computed(() => (props.cellFields || []).filter((cf) => cf?.editable))
const separateColumnFields = computed(() => {
	const names = new Set(props.separateCellFields || [])
	return (props.cellFields || []).filter((cf) => names.has(cf?.name))
})
const inlineCellFields = computed(() => {
	const names = new Set(props.separateCellFields || [])
	return (props.cellFields || []).filter((cf) => !names.has(cf?.name))
})

// True when this cell holds a populated Secondary entry (a positive
// secondary_qty AND a UOM stamped on it). Used by the cell-display template
// to surface "Sec: 50 Kattu" only when relevant — mirrors the
// production_api DC `attr.secondary_qty > 0 && attr.secondary_uom` rule.
function hasSecondary(cell) {
	return !!cell && Number(cell.secondary_qty) > 0 && !!cell.secondary_uom
}

// Toggle handler for "Update Secondary": ON → fetch the picked item's
// secondary_unit_of_measure (mirrors production_api DC `get_check_value`);
// OFF → drop the fetched UOM and zero out any per-cell secondary_qty already
// entered so the payload stays clean.
async function onUpdateSecondaryToggle(value) {
	draft.updateSecondary = value ? true : false
	if (!value) {
		draft.secondaryUom = ""
		for (const cell of Object.values(draft.values)) {
			delete cell.secondary_qty
			delete cell.secondary_uom
		}
		return
	}
	if (!draft.parentItem) {
		toast.warn("Pick an item first", "Choose a parent item before enabling secondary.")
		draft.updateSecondary = false
		return
	}
	try {
		const r = await callMethod("frappe.client.get_value", {
			doctype: "Item",
			filters: draft.parentItem,
			fieldname: "secondary_unit_of_measure",
		})
		draft.secondaryUom = (r && r.secondary_unit_of_measure) || ""
		if (!draft.secondaryUom) {
			toast.warn("No Secondary UOM", "This item has no secondary_unit_of_measure configured.")
		}
	} catch (e) {
		toast.error("UOM fetch failed", e.message)
		draft.secondaryUom = ""
	}
}

function visibleDimensions(group) {
	if (!props.showDimensions || !entryDimensions.value.length) return []
	return entryDimensions.value.filter((dim) => {
		for (const it of group.items || []) {
			const v = (it.dimensions || {})[dim.fieldname]
			if (v !== undefined && v !== null && v !== "") return true
		}
		return false
	})
}

function gridTableStyle(group) {
	const dimensionWidth = visibleDimensions(group).length * 110
	const attributeWidth = (group.attributes || []).length * 110
	const qtyWidth = group.primary_attribute && group.primary_attribute_values?.length
		? group.primary_attribute_values.length * 92
		: 110
	const separateWidth = separateColumnFields.value.reduce(
		(total, field) => total + (isCurrencyCellField(field) ? 132 : 112),
		0,
	)
	const optionalWidth = (props.showPreviousPrice ? 138 : 0) + (props.editable && !props.lockedItems ? 88 : 0)
	const minWidth = Math.max(
		620,
		40 + 160 + dimensionWidth + attributeWidth + qtyWidth + separateWidth + 84 + optionalWidth,
	)
	return { tableLayout: "fixed", minWidth: `${minWidth}px` }
}

function cellQty(item, pv) {
	const cell = (item.values || {})[pv]
	return cell && cell.qty ? cell.qty : 0
}

function existingQtyMax(item, key) {
	const max = Number(item?.values?.[key]?.max_receivable_quantity)
	return Number.isFinite(max) && max >= 0 ? max : undefined
}

function onExistingQtyInput(item, key, rawValue) {
	const value = item?.values?.[key]
	if (!value) return
	const qtyValue = Number(rawValue) || 0
	value.qty = qtyValue
	if (value.rate === undefined || value.rate === null || value.rate === "") return
	const rate = Number(value.rate) || 0
	const discountPercentage = Number(item.discount_percentage) || 0
	const taxRate = Number(item.tax) || 0
	value.amount = qtyValue * rate
	value.discount_amount = value.amount * discountPercentage / 100
	value.tax_amount = (value.amount - value.discount_amount) * taxRate / 100
	value.total_amount = value.amount - value.discount_amount + value.tax_amount
}

// Format a per-cell display value (round floats; blank → "0").
function fmtCell(v) {
	if (v === null || v === undefined || v === "") return "0"
	const n = Number(v)
	return Number.isNaN(n) ? v : Math.round(n * 1000) / 1000
}

function formatSeparateCell(item, field) {
	if (field?.source === "entry") {
		const value = item?.[field.name]
		if (value === null || value === undefined || value === "") {
			return field.format === "percentage" ? "0%" : "—"
		}
		const numeric = Number(value)
		const formatted = Number.isFinite(numeric)
			? numeric.toLocaleString("en-IN", { maximumFractionDigits: 3 })
			: String(value)
		return field.format === "percentage" ? `${formatted}%` : formatted
	}
	const cells = Object.values(item?.values || {})
	let value
	if (field.name === "pending_quantity" && cells.every((cell) => cell?.[field.name] == null)) {
		value = cells.reduce((total, cell) => total + (Number(cell?.qty) || 0), 0)
	} else if (field.name === "amount") {
		// Draft GRN onload rows are rebuilt from their PO/WO source so they carry
		// quantity and rate but may not carry the already-derived amount. Keep the
		// saved view useful before submit by deriving the same qty × rate value.
		value = cells.reduce((total, cell) => {
			const stored = Number(cell?.amount) || 0
			const derived = (Number(cell?.qty) || 0) * (Number(cell?.rate) || 0)
			return total + (stored || derived)
		}, 0)
	} else {
		value = cells.reduce((total, cell) => total + (Number(cell?.[field.name]) || 0), 0)
	}
	const formatted = value.toLocaleString("en-IN", { maximumFractionDigits: 3 })
	return isCurrencyCellField(field) ? `₹ ${formatted}` : formatted
}

function isCurrencyCellField(field) {
	return ["rate", "amount", "total_amount"].includes(field?.name)
}

// ════════════════ ITEM RESOLUTION (get_attribute_details) ════════════════
async function onParentItemSelected() {
	if (!draft.parentItem) return
	await fetchAttributeDetails(draft.parentItem)
	await focusNextDraftControl()
}

function onParentItemMaybeCleared() {
	// AutoComplete @change fires on free-text/clear. If emptied, reset the draft body.
	if (!draft.parentItem) {
		draft.resolved = false
		draft.attributes = []
		draft.attributeValues = {}
		draft.primaryAttribute = ""
		draft.primaryValues = []
		draft.defaultUom = ""
		draft.dependentAttribute = ""
		draft.dependentValue = ""
		draft.dependentDetails = null
		draft.values = { default: { qty: 0 } }
	}
}

async function fetchAttributeDetails(itemName) {
	loadingAttrs.value = true
	draft.resolved = false
	try {
		const r = await callMethod("yrp.yrp.doctype.item.item.get_attribute_details", {
			item_name: itemName,
		})
		if (!r) {
			toast.warn("No attributes", `Could not resolve attributes for ${itemName}.`)
			return
		}
		draft.itemDefaultUom = r.default_uom || ""
		draft.dependentAttribute = r.dependent_attribute || ""
		draft.dependentDetails = r.dependent_attribute_details || null
		draft.dependentValue = ""

		// Item with a dependent attribute (e.g. Stage): defer attributes + qty until
		// the user picks a stage — applyStage() then fills the stage's attributes +
		// per-stage primary. (Mirrors the Desk ItemDimensionFetch flow.)
		if (draft.dependentAttribute && draft.dependentDetails?.attr_list) {
			draft.attributes = []
			draft.attributeValues = {}
			draft.primaryAttribute = ""
			draft.primaryValues = []
			draft.defaultUom = ""
			draft.values = { default: blankCell() }
			draft.resolved = true
			return
		}

		// No dependent attribute → the item's own non-primary attributes + primary.
		const nonPrimary = Array.isArray(r.attributes) ? r.attributes : []
		const primary = r.primary_attribute || ""
		const primaryValues = Array.isArray(r.primary_attribute_values)
			? r.primary_attribute_values
			: []

		draft.attributes = nonPrimary
		draft.attributeValues = {}
		for (const a of nonPrimary) draft.attributeValues[a] = ""

		draft.primaryAttribute = primary
		draft.primaryValues = primary ? primaryValues : []
		draft.defaultUom = r.default_uom || ""

		if (primary && primaryValues.length) {
			draft.values = {}
			for (const pv of primaryValues) draft.values[pv] = blankCell()
		} else {
			draft.values = { default: blankCell() }
		}
		draft.resolved = true
	} catch (e) {
		toast.error("Attribute lookup failed", e.message)
	} finally {
		loadingAttrs.value = false
	}
}

// A blank size-cell: just qty. Other valueFields (rate / secondary_qty /
// secondary_uom / …) are NOT pre-initialised here — pre-init to 0 leaks
// `secondary_uom: 0` into the payload (Link → UOM, server rejects with
// "Could not find Row #N: Secondary UOM: 0"). Editable numeric inputs set
// their cell field as the user types; auto-broadcast fields (secondary_uom)
// land in commitDraft. Empty fields are skipped on commit.
function blankCell() {
	return { qty: 0 }
}

// ════════════════ DEPENDENT ATTRIBUTE (e.g. Stage) ════════════════
// Stage values offered in the selector (keys of the dependent attr_list).
const dependentOptions = computed(() => {
	const al = draft.dependentDetails?.attr_list
	return al ? Object.keys(al) : []
})

// Configure the draft for the chosen stage: only that stage's attributes + its
// per-stage primary/values/uom are shown. preserveValues keeps the entered qtys +
// attribute values (used when re-editing an existing row).
function applyStage(stageValue, preserveValues = false) {
	const info = draft.dependentDetails?.attr_list?.[stageValue]
	if (!info) return
	const primary = info.primary_attribute || ""
	const primaryValues = Array.isArray(info.primary_attribute_values)
		? info.primary_attribute_values
		: []
	// Stage attributes minus the primary and minus the dependent attribute itself
	// (the dependent attr is captured by the stage selector, not a plain select).
	const stageAttrs = (info.attributes || []).filter(
		(a) => a !== primary && a !== draft.dependentAttribute,
	)
	draft.attributes = stageAttrs
	if (!preserveValues) {
		draft.attributeValues = {}
		for (const a of stageAttrs) draft.attributeValues[a] = ""
	}
	draft.primaryAttribute = primary
	draft.primaryValues = primary ? primaryValues : []
	draft.defaultUom = info.uom || draft.itemDefaultUom || ""
	if (!preserveValues) {
		if (primary && primaryValues.length) {
			draft.values = {}
			for (const pv of primaryValues) draft.values[pv] = blankCell()
		} else {
			draft.values = { default: blankCell() }
		}
	}
}

// Stage selector changed (user interaction): apply the stage, or clear the
// attributes/qty when the stage is cleared.
function onStageChange() {
	const v = draft.dependentValue
	if (v && draft.dependentDetails?.attr_list?.[v]) {
		applyStage(v, false)
	} else {
		draft.attributes = []
		draft.attributeValues = {}
		draft.primaryAttribute = ""
		draft.primaryValues = []
		draft.values = { default: blankCell() }
	}
	focusNextDraftControl()
}

// ════════════════ COMMIT DRAFT → groups ════════════════
async function commitDraft() {
	if (!draft.parentItem || !draft.resolved) {
		toast.warn("Pick an item", "Choose a parent item first.")
		focusDraftControl("item")
		return
	}
	if (draft.dependentAttribute && !draft.dependentValue) {
		toast.warn("Pick a stage", `Select a ${draft.dependentAttribute} first.`)
		focusDraftControl("dependent")
		return
	}
	// Mandatory dimensions.
	for (const dim of entryDimensions.value) {
		if (dim.mandatory && !draft.dimensions[dim.fieldname]) {
			toast.warn("Missing dimension", `${dim.label} is required.`)
			focusDraftControl(`dimension:${dim.fieldname}`)
			return
		}
	}
	// Non-primary attributes must all be chosen (they identify the variant).
	for (const a of draft.attributes) {
		if (!draft.attributeValues[a]) {
			toast.warn("Missing attribute", `Select a value for ${a}.`)
			focusDraftControl(`attribute:${a}`)
			return
		}
	}
	// At least one positive qty.
	const total = Object.values(draft.values).reduce((n, v) => n + (Number(v?.qty) || 0), 0)
	if (!total) {
		toast.warn("Quantity required", "Enter a quantity in at least one cell.")
		focusDraftControl(`quantity:${draft.primaryValues[0] || "default"}`)
		return
	}

	// Build the per-item entry (the shape ungroup_items_from_ui reads).
	const dimensionsOut = {}
	for (const dim of dimensions.value) {
		const v = draft.dimensions[dim.fieldname]
		if (v) dimensionsOut[dim.fieldname] = v
	}
	const attributesOut = {}
	// The dependent attribute (e.g. Stage) is a real variant attribute — store its
	// chosen value alongside the stage's other attributes.
	if (draft.dependentAttribute) attributesOut[draft.dependentAttribute] = draft.dependentValue
	for (const a of draft.attributes) attributesOut[a] = draft.attributeValues[a] || ""

	const valuesOut = {}
	for (const [k, cell] of Object.entries(draft.values)) {
		const out = { qty: Number(cell.qty) || 0 }
		for (const f of props.valueFields) {
			if (cell[f] !== undefined && cell[f] !== null && cell[f] !== "") out[f] = cell[f]
		}
		valuesOut[k] = out
	}

	// Broadcast secondary_uom from the fetched item value to every cell when
	// the user opted in. Cell-level secondary_qty is already in valuesOut from
	// the per-cell input (via the loop above). When the toggle is OFF, no
	// secondary_uom / secondary_qty leaves the editor at all (matches user
	// preference 2026-05-29 — "those are not mandatory").
	if (props.showSecondaryToggle && draft.updateSecondary && draft.secondaryUom) {
		for (const cell of Object.values(valuesOut)) {
			cell.secondary_uom = draft.secondaryUom
		}
	}

	const itemEntry = {
		name: draft.parentItem,
		dimensions: dimensionsOut,
		attributes: attributesOut,
		primary_attribute: draft.primaryAttribute || "",
		default_uom: draft.defaultUom || "",
		values: valuesOut,
	}
	// Per-row entry fields land at the item level so ungroup_items_from_ui
	// copies them onto each generated child row.
	if (props.showAllowZeroRate) {
		itemEntry.allow_zero_valuation_rate = draft.allow_zero_valuation_rate ? 1 : 0
	}

	// Purchase Orders use supplier-specific Item Prices. Apply one when it is
	// available, but never block a draft item here: base YRP warns during draft
	// validation and enforces the active price only during submit.
	if (props.applyAvailablePrice) {
		if (!props.priceSupplier) {
			toast.warn("Select supplier", "Choose the supplier before adding Purchase Order items.")
			return
		}
		pricing.value = true
		try {
			const price = await callMethod(
				"yrp.yrp.doctype.purchase_order.purchase_order.get_item_price_for_ui",
				{
					item_detail: JSON.stringify(itemEntry),
					supplier: props.priceSupplier,
				},
			)
			if (price) applyPurchaseOrderPrice(itemEntry, price)
		} catch (e) {
			toast.warn("Price lookup unavailable", "The item was added without a price. It will be checked again when you save.")
		} finally {
			pricing.value = false
		}
	}

	// Group attribute NAMES include the dependent attribute (it's a real attribute
	// of the variant, just entered via the stage selector).
	const groupAttrNames = draft.dependentAttribute
		? [draft.dependentAttribute, ...draft.attributes]
		: [...draft.attributes]
	// Find or create the matching attribute-group (mirror _get_item_group_index).
	const gi = findGroupIndex(groupAttrNames, draft.primaryAttribute, draft.primaryValues)
	if (gi === -1) {
		groups.value.push({
			attributes: groupAttrNames,
			primary_attribute: draft.primaryAttribute || "",
			primary_attribute_values: [...draft.primaryValues],
			items: [itemEntry],
		})
	} else {
		groups.value[gi].items.push(itemEntry)
	}

	resetDraft({ focus: true })
}

// Exact calculation used by the existing Purchase Order Desk item editor. Item
// Price can return one common rate or a rate per primary attribute value (size).
function applyPurchaseOrderPrice(itemEntry, price) {
	const values = itemEntry.values || {}
	const taxRate = Number(price.tax_rate) || 0
	const discountPercentage = Number(itemEntry.discount_percentage) || 0
	const missing = []

	itemEntry.tax = price.tax || ""
	for (const [key, value] of Object.entries(values)) {
		const qty = Number(value.qty) || 0
		const rate = price.rates ? price.rates[key] : price.rate
		if (qty > 0 && (rate === undefined || rate === null || rate === "")) {
			missing.push(key)
			continue
		}
		value.rate = Number(rate) || 0
		value.amount = qty * value.rate
		value.discount_amount = value.amount * discountPercentage / 100
		value.tax_amount = (value.amount - value.discount_amount) * taxRate / 100
		value.total_amount = value.amount - value.discount_amount + value.tax_amount
	}

	if (missing.length) {
		return false
	}
	return true
}

// Match a group by attribute structure (same rule as save_stock_items._get_item_group_index).
function findGroupIndex(attrNames, primary, primaryValues) {
	const sortedEq = (a, b) =>
		JSON.stringify([...(a || [])].sort()) === JSON.stringify([...(b || [])].sort())
	for (let i = 0; i < groups.value.length; i++) {
		const g = groups.value[i]
		if (!sortedEq(g.attributes, attrNames)) continue
		if ((g.primary_attribute || "") !== (primary || "")) continue
		if (!sortedEq(g.primary_attribute_values, primaryValues)) continue
		return i
	}
	return -1
}

function firstDraftFocusKey() {
	const firstDimension = entryDimensions.value[0]?.fieldname
	return firstDimension ? `dimension:${firstDimension}` : "item"
}

function focusDraftControl(key = firstDraftFocusKey()) {
	return focusFirstControl(addFormEl, {
		selector: `[data-focus-key="${CSS.escape(String(key))}"]`,
	})
}

function focusNextDraftControl() {
	if (draft.dependentAttribute && !draft.dependentValue) return focusDraftControl("dependent")
	if (draft.attributes.length) return focusDraftControl(`attribute:${draft.attributes[0]}`)
	return focusDraftControl(`quantity:${draft.primaryValues[0] || "default"}`)
}

function resetDraft({ focus = false } = {}) {
	Object.assign(draft, blankDraft())
	if (focus) focusDraftControl()
}

function removeItem(gi, index) {
	const g = groups.value[gi]
	if (!g) return
	if (g.items.length === 1) {
		groups.value.splice(gi, 1)
	} else {
		g.items.splice(index, 1)
	}
}

// Pull an existing row back into the draft for editing, then remove it from the
// table. Editing in the add-form + "Update Item" re-commits it via commitDraft —
// so the user can change item / dimensions / attributes / qtys of an added row.
async function startEdit(gi, index) {
	const g = groups.value[gi]
	const it = g?.items?.[index]
	if (!it) return
	const vals = cloneValues(it.values)
	for (const pv of g.primary_attribute_values || []) {
		if (!vals[pv]) vals[pv] = blankCell()
	}
	resetDraft()
	draft.editing = true
	draft.parentItem = it.name
	draft.dimensions = { ...(it.dimensions || {}) }
	// Re-resolve the item config — the dependent-attribute attr_list isn't stored
	// on the row, so we need it to rebuild the stage flow on edit.
	let r = null
	try {
		r = await callMethod("yrp.yrp.doctype.item.item.get_attribute_details", { item_name: it.name })
	} catch (_) {
		toast.warn("Could not reload item config", "Re-pick the item if the attributes look wrong.")
	}
	draft.itemDefaultUom = r?.default_uom || it.default_uom || ""
	draft.dependentAttribute = r?.dependent_attribute || ""
	draft.dependentDetails = r?.dependent_attribute_details || null

	if (draft.dependentAttribute && draft.dependentDetails?.attr_list) {
		// Dependent (stage) row: set the stage, let applyStage derive its attribute
		// list + primary (preserve=true so it doesn't wipe the values we restore).
		draft.dependentValue = (it.attributes || {})[draft.dependentAttribute] || ""
		applyStage(draft.dependentValue, true)
	} else {
		// Plain row: the group's attribute names are the editable selects.
		draft.attributes = [...(g.attributes || [])]
		draft.primaryAttribute = it.primary_attribute || g.primary_attribute || ""
		draft.primaryValues = [...(g.primary_attribute_values || [])]
	}
	// Restore the row's chosen attribute values + entered qtys (+ uom).
	draft.attributeValues = { ...(it.attributes || {}) }
	draft.defaultUom = it.default_uom || draft.defaultUom || ""
	draft.values = vals
	if (props.showAllowZeroRate) {
		draft.allow_zero_valuation_rate = Number(it.allow_zero_valuation_rate) || 0
	}
	// Re-derive Update Secondary state from the saved cells: if any cell
	// carried a secondary_uom, the row was committed with secondary on.
	if (props.showSecondaryToggle) {
		const firstUom = Object.values(vals).find((c) => c?.secondary_uom)?.secondary_uom || ""
		draft.updateSecondary = !!firstUom
		draft.secondaryUom = firstUom
	}
	draft.resolved = true
	removeItem(gi, index)
	await focusDraftControl(firstDraftFocusKey())
}

// ════════════════ AUTOCOMPLETE QUERIES ════════════════
async function searchDimension(dim, e) {
	if (!dim.options) {
		dimSuggestions[dim.fieldname] = []
		return
	}
	dimSuggestions[dim.fieldname] = await searchNames(dim.options, e.query)
}

// Legal values for a non-primary attribute, scoped to the chosen item — mirrors
// the Desk get_item_attribute_values query (item + attribute filters). Over HTTP
// we use the plain Item Attribute Value list to avoid the Desk query's positional
// searchfield/start/page_len signature; the server re-validates on save.
async function searchAttributeValue(attr, e) {
	try {
		const rows = await callMethod("frappe.client.get_list", {
			doctype: "Item Attribute Value",
			filters: {
				attribute_name: attr,
				attribute_value: ["like", `%${e.query || ""}%`],
			},
			fields: ["attribute_value"],
			limit_page_length: 50,
			order_by: "idx asc",
		})
		attrValueSuggestions[attr] = (rows || []).map((x) => x.attribute_value)
	} catch (_) {
		attrValueSuggestions[attr] = []
	}
}

async function searchNames(doctype, txt, filters = {}) {
	try {
		const rows = await searchLink(doctype, txt || "", filters)
		return rows.map((r) => r.name)
	} catch (_) {
		return []
	}
}

function localizedItem(value) {
	if (!value) return ""
	return linkTitles.titleFor("Item", value) || String(value)
}

// ════════════════ PUBLIC API ════════════════
// Deep-cloned grouped JSON for buildPayload. Strips empty groups defensively.
function getItems() {
	return JSON.parse(
		JSON.stringify(groups.value.filter((g) => (g.items || []).length > 0)),
	)
}

function hasItems() {
	return totalLogicalItems.value > 0
}

function focusFirstQuantity() {
	if (props.lockedItems) return focusFirstControl(editorEl, { selector: ".grid-groups" })
	return focusDraftControl(`quantity:${draft.primaryValues[0] || "default"}`)
}

function focusFirstEntry() {
	return focusDraftControl(firstDraftFocusKey())
}

// Rebuild internal state from a saved grouped payload (array or JSON string).
// Tolerant of partial entries (missing dimensions/attributes/values).
function loadData(grouped) {
	changeArmed.value = false // programmatic load — don't emit change
	let data = grouped
	if (typeof data === "string") {
		try {
			data = JSON.parse(data || "[]")
		} catch (_) {
			data = []
		}
	}
	if (!Array.isArray(data)) {
		groups.value = []
		nextTick(() => { changeArmed.value = true })
		return
	}
	groups.value = data.map((g) => ({
		attributes: Array.isArray(g.attributes) ? [...g.attributes] : [],
		primary_attribute: g.primary_attribute || "",
		primary_attribute_values: Array.isArray(g.primary_attribute_values)
			? [...g.primary_attribute_values]
			: [],
		items: (g.items || []).map((it) => {
			const item = {
				name: it.name || "",
				dimensions: { ...(it.dimensions || {}) },
				attributes: { ...(it.attributes || {}) },
				primary_attribute: it.primary_attribute || g.primary_attribute || "",
				default_uom: it.default_uom || "",
				values: cloneValues(it.values),
			}
			// Entry-level fields (for example Purchase Order tax percentage) live
			// beside `values`, not inside each quantity cell. Preserve them when a
			// saved grouped payload is hydrated so dedicated read-only columns can
			// render them and edit/save round-trips do not silently discard them.
			for (const field of props.entryFields || []) {
				if (it[field] !== undefined) item[field] = it[field]
			}
			return item
		}),
	}))
	nextTick(() => { changeArmed.value = true })
}

function cloneValues(values) {
	const out = {}
	for (const [k, v] of Object.entries(values || {})) {
		out[k] = { qty: Number(v?.qty) || 0 }
		for (const f of props.valueFields) {
			if (v && v[f] !== undefined) out[k][f] = v[f]
		}
	}
	if (!Object.keys(out).length) out.default = { qty: 0 }
	return out
}

defineExpose({ getItems, loadData, hasItems, focusFirstEntry, focusFirstQuantity })
</script>

<style scoped>
.stock-grid-editor {
	display: flex;
	flex-direction: column;
	gap: 14px;
}

/* Grouped pivot tables */
.grid-groups {
	display: flex;
	flex-direction: column;
	gap: 12px;
}
.grid-group {
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius-sm);
	overflow-x: auto;
	overflow-y: hidden;
}
.pivot-dt {
	font-size: 13px;
}
:deep(.pivot-dt .p-datatable-thead > tr > th) {
	background: var(--mgk-slate-50);
	font-size: 11.5px;
	letter-spacing: 0.03em;
	text-transform: uppercase;
	color: var(--mgk-muted);
	padding: 6px 8px;
	white-space: nowrap;
	text-align: center;
}
/* PrimeVue renders the header label in a flex wrapper — center it too. */
:deep(.pivot-dt .p-datatable-column-header-content) {
	justify-content: center;
}
:deep(.pivot-dt .p-datatable-tbody > tr > td) {
	padding: 5px 8px;
	vertical-align: middle;
	text-align: center;
}
.cell-num {
	width: 100%;
}
:deep(.cell-num-input) {
	/* fill the cell — PrimeVue's fluid sets the inner input to width:1% which
	   collapses to ~26px on our block-display host; force full width. */
	width: 100%;
	text-align: center;
}
.cell-ro {
	display: block;
	text-align: center;
	color: var(--mgk-ink-2);
}
.cell-extra {
	display: block;
	text-align: center;
	font-size: 10.5px;
	color: var(--mgk-muted);
	white-space: nowrap;
}
.separate-cell-value {
	display: block;
	text-align: center;
	color: var(--mgk-ink-2);
	font-size: 12px;
	font-weight: 650;
	font-variant-numeric: tabular-nums;
}
.separate-cell-value.money {
	color: var(--mgk-accent-dark);
}
.previous-price {
	display: grid;
	justify-items: center;
	gap: 3px;
	color: var(--mgk-ink-2);
	font-size: 12px;
	font-weight: 700;
	font-variant-numeric: tabular-nums;
}
.previous-price.loading {
	color: var(--mgk-muted);
}
.previous-price > span {
	display: inline-flex;
	align-items: center;
	gap: 5px;
}
.previous-price small {
	padding: 1px 4px;
	border-radius: 4px;
	background: var(--mgk-slate-50);
	color: var(--mgk-muted);
	font-size: 9px;
}
.previous-price > span.empty {
	color: var(--mgk-muted);
	font-size: 10.5px;
	font-weight: 500;
}

.grid-empty,
.grid-empty-state {
	text-align: center;
	color: var(--mgk-muted);
	font-size: 13px;
}
.grid-empty {
	padding: 16px 0;
}
.grid-empty-state {
	padding: 22px;
	border: 1px dashed var(--mgk-line);
	border-radius: var(--radius-sm);
	background: var(--mgk-card);
}

/* Add-item form */
.add-form {
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius-sm);
	background: var(--mgk-card);
	padding: 14px 16px;
	display: flex;
	flex-direction: column;
	gap: 12px;
}
.add-head {
	display: flex;
	align-items: center;
	gap: 12px;
}
.add-head h4 {
	margin: 0;
	font-size: 13.5px;
	font-weight: 600;
	color: var(--mgk-ink);
}
.add-loading {
	font-size: 12px;
	color: var(--mgk-muted);
}
.add-row {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: 12px 16px;
}
.attr-row {
	padding-top: 2px;
	border-top: 1px dashed var(--mgk-line);
	margin-top: 2px;
}
.add-fld {
	display: flex;
	flex-direction: column;
	gap: 5px;
	min-width: 0;
}
.add-fld label {
	font-size: 11.5px;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--mgk-muted);
	font-weight: 600;
}
.add-fld .req {
	color: var(--mgk-danger);
}

/* Qty pivot (size cells) */
.qty-pivot {
	display: flex;
	flex-wrap: wrap;
	gap: 10px;
	padding-top: 4px;
}
.qty-cell {
	display: flex;
	flex-direction: column;
	gap: 3px;
	width: 92px;
}
.qty-cell label {
	font-size: 12px;
	font-weight: 600;
	color: var(--mgk-ink-2);
}
.qty-uom {
	font-size: 10.5px;
	color: var(--mgk-muted-2);
}
.qty-single {
	display: flex;
	flex-direction: column;
	gap: 4px;
	max-width: 220px;
}
.qty-single label {
	font-size: 11.5px;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--mgk-muted);
	font-weight: 600;
}
.qty-single .req {
	color: var(--mgk-danger);
}

.rate-row,
.sec-row {
	padding-top: 6px;
	border-top: 1px dashed var(--mgk-line);
	margin-top: 6px;
}
.toggle-fld {
	justify-content: center;
}
.sec-uom-display {
	font-size: 13px;
	color: var(--mgk-ink);
	padding: 6px 0;
}
.sec-uom-display.muted {
	color: var(--mgk-muted);
	font-style: italic;
}
/* Per-cell editable sublabel inside a qty-cell (Rate, Sec Qty under the qty). */
.qty-cell .cell-sub {
	font-size: 11px;
	font-weight: 600;
	color: var(--mgk-muted);
	margin-top: 2px;
}
.qty-single .cell-sub {
	font-size: 11.5px;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--mgk-muted);
	font-weight: 600;
	margin-top: 6px;
}

.add-actions {
	display: flex;
	gap: 8px;
	align-items: center;
}

.grid-foot {
	font-size: 12.5px;
	color: var(--mgk-muted);
	padding: 0 2px;
}

/* Keep dense item grids readable at the registered experience's 110%-equivalent
   type scale without shrinking the columns as CSS/browser zoom would. */
:deep(.pivot-dt .p-datatable-thead > tr > th) {
	font-size: 12.5px;
}
:deep(.pivot-dt .p-datatable-tbody > tr > td) {
	font-size: 14px;
}
.cell-extra { font-size: 11.5px; }
.separate-cell-value { font-size: 13px; }
.previous-price { font-size: 13px; }
</style>
