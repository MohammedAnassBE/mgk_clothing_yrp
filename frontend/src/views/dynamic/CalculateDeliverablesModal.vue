<!--
  CalculateDeliverablesModal — draft Work Order calculation for both MGK yarn
  modes: explicit IPD routes compiled to Process Matrices, and the legacy direct
  yarn flow. The Work Order already owns the Item Production Detail; this popup
  asks only for the route attributes and input weight.

	The parent (DocDetail.vue) fetches the selected IPD's process context via
	get_yarn_deliverable_rows. On submit this component assembles
  per-row payload ({production_detail, yarn_item, attribute_values, weight}),
  calls calculate_deliverables, then emits `calculated` (with the counts) so the
  parent can refresh the doc + pivots and toast.

  Usage:
    <CalculateDeliverablesModal
        v-model:visible="calcOpen"
        :work-order="doc.name"
        :payload="calcPayload"
        @calculated="onDeliverablesCalculated" />
-->
<template>
	<Dialog
		:visible="visible"
		modal
		:header="dialogTitle"
		:style="dialogStyle"
		@update:visible="$emit('update:visible', $event)"
	>
		<div v-if="selectedOptions.length" class="cd-factor">
			<template v-if="isTransformation">
				Each route shows its configured input and output. Enter the quantity against the matching route;
				blank quantity rows are ignored.
			</template>
			<template v-else>
				Wastage <b>{{ wastagePct }}%</b> · Excess <b>{{ excessPct }}%</b> →
				receivable = weight × <b>{{ factor }}</b>
			</template>
		</div>

		<div ref="rowsEl" class="cd-rows">
			<section
				v-for="option in selectedOptions"
				:key="option.production_detail"
				class="cd-ipd"
			>
				<header class="cd-ipd-head">
					<div>
						<strong>{{ localizedItem(option.item) }}</strong>
						<small>{{ option.production_detail }}</small>
					</div>
					<span>{{ option.rows.length }} {{ option.rows.length === 1 ? "route" : "routes" }}</span>
				</header>

				<div v-if="option.ipd_attributes?.length" class="cd-ipd-attributes">
					<div class="cd-context-title">
						<span>IPD attribute values</span>
						<small>Only process-applicable attributes are entered below.</small>
					</div>
					<div class="cd-context-list">
						<div
							v-for="attribute in option.ipd_attributes"
							:key="attribute.attribute"
							class="cd-context-attribute"
						>
							<strong>{{ attribute.label || attribute.attribute }}</strong>
							<div v-if="attribute.values?.length" class="cd-value-chips">
								<span v-for="value in attribute.values" :key="value">{{ value }}</span>
							</div>
							<small v-else>No values configured</small>
						</div>
					</div>
				</div>

				<div
					v-for="(row, routeIndex) in option.rows"
					:key="rowKey(row)"
					class="cd-row"
				>
					<div class="cd-row-head">
						<div class="cd-route-main">
							<span class="cd-idx">Route {{ routeIndex + 1 }}</span>
							<template v-if="isTransformation">
								<span class="cd-yarn">{{ localizedItem(row.input_item || row.input_label) }}</span>
								<i class="pi pi-arrow-right cd-arrow" />
								<span class="cd-yarn">{{ localizedItem(row.output_item || row.output_label) }}</span>
							</template>
							<span v-else class="cd-yarn">{{ localizedItem(row.yarn_item || row.yarn_item_name) }}</span>
						</div>
						<span v-if="isTransformation" class="cd-ratio">
							1 → {{ num(row.quantity_ratio) || 1 }}
						</span>
					</div>

					<div v-if="hasColourTransition(row)" class="cd-colour-transition">
						<div class="cd-colour-side">
							<small>Input colour</small>
							<strong>{{ row.from_colour || "Not set" }}</strong>
						</div>
						<i class="pi pi-arrow-right cd-colour-arrow" />
						<div class="cd-colour-side cd-colour-output">
							<small>Output colour</small>
							<strong>{{ row.to_colour || "Not set" }}</strong>
						</div>
					</div>

					<div v-if="canCalculate(row)" class="cd-combinations">
						<div
							v-for="(combination, combinationIndex) in routeState(row).combinations"
							:key="combination.key"
							class="cd-combination"
							:data-route-key="rowKey(row)"
							:data-combination-index="combinationIndex"
						>
							<div class="cd-combination-index">{{ combinationIndex + 1 }}</div>
							<div class="cd-fields">
								<div
									v-for="attr in row.attributes"
									:key="attr.attribute"
									class="cd-field"
									:data-attribute="attr.attribute"
								>
									<label class="cd-label">{{ attr.label || attr.attribute }}</label>
									<Select
										v-model="combination.attrs[attr.attribute]"
										:options="attr.options"
										:placeholder="`Select ${attr.label || attr.attribute}`"
										filter
										showClear
										fluid
									/>
								</div>

								<div class="cd-field cd-field-weight" data-weight>
									<label class="cd-label">
										Input quantity{{ (row.input_uom || row.uom) ? ` (${row.input_uom || row.uom})` : "" }}
									</label>
									<InputNumber
										v-model="combination.weight"
										:min="0"
										:minFractionDigits="0"
										:maxFractionDigits="3"
										placeholder="Leave blank to skip"
										fluid
									/>
								</div>
							</div>
							<Button
								v-if="routeState(row).combinations.length > 1"
								class="cd-remove"
								icon="pi pi-trash"
								text
								rounded
								severity="danger"
								aria-label="Remove combination"
								@click="removeCombination(row, combinationIndex)"
							/>
						</div>
						<Button
							v-if="row.attributes?.length && canAddCombination(row)"
							class="cd-add-combination"
							:label="addCombinationLabel(row)"
							icon="pi pi-plus"
							text
							size="small"
							@click="addCombination(row)"
						/>
					</div>
				</div>
			</section>

			<div v-if="!ipdOptions.length" class="cd-empty">
				<i class="pi pi-info-circle" />
				<strong>No calculation route</strong>
				<span>Configure {{ processName }} on the Work Order's Item Production Detail.</span>
			</div>
		</div>

		<template #footer>
			<Button label="Cancel" text severity="secondary" @click="close" />
			<Button
				label="Calculate"
				icon="pi pi-calculator"
				:loading="saving"
				:disabled="!hasCalculableRow || saving"
				@click="submit"
			/>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed, nextTick, watch } from "vue"
import Dialog from "primevue/dialog"
import Button from "primevue/button"
import Select from "primevue/select"
import InputNumber from "primevue/inputnumber"
import { callMethod } from "@/api/client"
import { useAppToast } from "@/composables/useToast"
import { useLinkTitles } from "@/composables/useLinkTitles"
import { focusFirstControl } from "@/utils/focusControl"

const linkTitles = useLinkTitles()

function localizedItem(value) {
	if (!value) return "—"
	return linkTitles.titleFor("Item", value) || String(value)
}

const API = "mgk_clothing_yrp.mgk_clothing_yrp.api.work_order"

const props = defineProps({
	visible: { type: Boolean, default: false },
	workOrder: { type: String, required: true },
	// Loaded `modified` timestamp — forwarded to calculate_deliverables so the
	// backend's stale-write guard (_guard_not_modified) rejects a concurrent edit.
	modified: { type: String, default: null },
	// The get_yarn_deliverable_rows payload (options, rows and process defaults).
	payload: { type: Object, default: () => ({}) },
})

const emit = defineEmits(["update:visible", "calculating", "calculated", "calculation-failed"])
const toast = useAppToast()

const saving = ref(false)
// Per-route editable state: { combinations:[{ key, weight, attrs }] }.
const form = ref({})
const rowsEl = ref(null)
let dialogOpener = null
let combinationSequence = 0

const processName = computed(() => props.payload?.process_name || "this process")
const dialogTitle = computed(() => `Calculate ${processName.value} Deliverables`)
const ipdOptions = computed(() => props.payload?.options || [])
const isTransformation = computed(() => props.payload?.mode === "transformation")
const selectedOptions = computed(() => {
	if (ipdOptions.value.length) return ipdOptions.value
	// Backward-compatible shape for an older cached API response.
	const fallbackRows = props.payload?.rows || []
	if (!fallbackRows.length) return []
	const grouped = new Map()
	for (const row of fallbackRows) {
		const key = row.production_detail || `row-${row.idx}`
		if (!grouped.has(key)) {
			grouped.set(key, {
				label: key,
				item: row.item || row.yarn_item,
				production_detail: key,
				rows: [],
			})
		}
		grouped.get(key).rows.push(row)
	}
	return [...grouped.values()]
})
const rows = computed(() => selectedOptions.value.flatMap((option) => option.rows || []))
const dialogStyle = computed(() => ({
	width: "min(1040px, calc(100vw - 28px))",
	...(selectedOptions.value.length
		? { height: "min(680px, calc(100vh - 28px))" }
		: {}),
}))
const wastagePct = computed(() => num(props.payload?.default_wastage))
const excessPct = computed(() => num(props.payload?.default_excess))
const factor = computed(() =>
	(1 - wastagePct.value / 100 + excessPct.value / 100).toFixed(4),
)
const hasCalculableRow = computed(() => rows.value.some((row) =>
	canCalculate(row) && routeState(row).combinations.some(
		(combination) => num(combination.weight) > 0,
	),
))

// The Work Order already selected the IPD; opening only resets quantity inputs.
watch(
	() => props.visible,
	async (open) => {
		if (!open) return
		dialogOpener = document.activeElement
		form.value = {}
		ensureFormRows()
		await focusFirstCombination()
	},
)

// Adding another IPD must preserve values already typed for existing routes.
watch(rows, ensureFormRows)

function ensureFormRows() {
	const next = {}
	for (const row of rows.value) {
		const key = rowKey(row)
		if (form.value[key]) {
			next[key] = form.value[key]
			continue
		}
		next[key] = { combinations: initialCombinations(row) }
	}
	form.value = next
}

function newCombination(row, preset = {}) {
	const attrs = {}
	for (const attr of row.attributes || []) {
		attrs[attr.attribute] = preset[attr.attribute] || null
	}
	combinationSequence += 1
	return { key: `combination-${combinationSequence}`, weight: null, attrs }
}

function initialCombinations(row) {
	const attributes = row.attributes || []
	const allowed = allowedCombinations(row)
	if (row.chain_constrained && allowed.length) {
		return allowed.map((preset) => newCombination(row, preset))
	}
	if (attributes.length === 1 && attributes[0].options?.length) {
		const attribute = attributes[0]
		return attribute.options.map((value) =>
			newCombination(row, { [attribute.attribute]: value }),
		)
	}
	return [newCombination(row)]
}

function allowedCombinations(row) {
	return Array.isArray(row?.allowed_attribute_combinations)
		? row.allowed_attribute_combinations
		: []
}

function combinationSignature(row, attrs) {
	return (row.attributes || []).map((attribute) => attrs?.[attribute.attribute] || "").join("\u0000")
}

function routeState(row) {
	return form.value[rowKey(row)] || { combinations: [] }
}

async function addCombination(row) {
	const attributes = row.attributes || []
	const allowed = allowedCombinations(row)
	if (row.chain_constrained && allowed.length) {
		const used = new Set(
			routeState(row).combinations.map((combination) => combinationSignature(row, combination.attrs)),
		)
		const nextPreset = allowed.find((preset) => !used.has(combinationSignature(row, preset)))
		if (!nextPreset) return
		routeState(row).combinations.push(newCombination(row, nextPreset))
		await focusCombination(row, routeState(row).combinations.length - 1)
		return
	}
	if (attributes.length === 1) {
		const attribute = attributes[0]
		const used = new Set(
			routeState(row).combinations.map(
				(combination) => combination.attrs[attribute.attribute],
			),
		)
		const nextValue = (attribute.options || []).find((value) => !used.has(value))
		routeState(row).combinations.push(
			newCombination(row, { [attribute.attribute]: nextValue }),
		)
		await focusCombination(row, routeState(row).combinations.length - 1)
		return
	}
	routeState(row).combinations.push(newCombination(row))
	await focusCombination(row, routeState(row).combinations.length - 1)
}

function removeCombination(row, index) {
	const combinations = routeState(row).combinations
	if (combinations.length <= 1) return
	combinations.splice(index, 1)
}

function addCombinationLabel(row) {
	return (row.attributes || []).length === 1 && row.attributes[0].attribute === "Colour"
		? "Add another colour"
		: "Add another combination"
}

function canAddCombination(row) {
	const attributes = row.attributes || []
	const allowed = allowedCombinations(row)
	if (row.chain_constrained && allowed.length) {
		const used = new Set(
			routeState(row).combinations.map((combination) => combinationSignature(row, combination.attrs)),
		)
		return allowed.some((preset) => !used.has(combinationSignature(row, preset)))
	}
	if (attributes.length !== 1) return true
	const attribute = attributes[0]
	const used = new Set(
		routeState(row).combinations.map(
			(combination) => combination.attrs[attribute.attribute],
		),
	)
	return (attribute.options || []).some((value) => !used.has(value))
}

function num(v) {
	const n = parseFloat(v)
	return isNaN(n) ? 0 : n
}

function hasColourTransition(row) {
	return isTransformation.value && Boolean(row?.from_colour || row?.to_colour)
}

function canCalculate(row) {
	return isTransformation.value ? Boolean(row?.route_name) : Boolean(row?.yarn_item)
}

function rowKey(row) {
	return `${row?.production_detail || "row"}:${row?.route_name || row?.yarn_item || row?.idx}`
}

async function close() {
	const opener = dialogOpener
	emit("update:visible", false)
	dialogOpener = null
	await nextTick()
	if (opener && opener.isConnected && !opener.disabled) opener.focus()
}

async function submit() {
	// The Work Order is the source of the Item/IPD context. Only routes with a
	// positive quantity are sent; blank routes are intentionally skipped.
	const out = []
	const seen = new Set()
	for (const row of rows.value) {
		if (!canCalculate(row)) continue
		for (const [combinationIndex, state] of routeState(row).combinations.entries()) {
			const weight = num(state.weight)
			const rowLabel = isTransformation.value
				? (row.input_label || row.input_item)
				: (row.yarn_item_name || row.yarn_item)
			if (weight <= 0) continue
			const attribute_values = {}
			const missing = []
			for (const attr of row.attributes || []) {
				const val = state.attrs[attr.attribute]
				if (!val) missing.push({ key: attr.attribute, label: attr.label || attr.attribute })
				attribute_values[attr.attribute] = val
			}
			if (missing.length) {
				toast.warn(
					"Attribute required",
					`Select ${missing.map((entry) => entry.label).join(", ")} for ${rowLabel}.`,
				)
				await focusCombination(row, combinationIndex, missing[0].key)
				return
			}
			const allowed = allowedCombinations(row)
			if (
				row.chain_constrained
				&& allowed.length
				&& !allowed.some((preset) => (
					combinationSignature(row, preset) === combinationSignature(row, attribute_values)
				))
			) {
				toast.warn(
					"Combination unavailable",
					"Choose an attribute combination produced by the previous Process.",
				)
				await focusCombination(row, combinationIndex)
				return
			}
			const signature = `${rowKey(row)}:${JSON.stringify(attribute_values)}`
			if (seen.has(signature)) {
				toast.warn(
					"Duplicate combination",
					`Enter each attribute combination only once for ${rowLabel}.`,
				)
				return
			}
			seen.add(signature)
			out.push({
				production_detail: row.production_detail,
				...(isTransformation.value
					? { route_name: row.route_name }
					: { yarn_item: row.yarn_item }),
				attribute_values,
				weight,
			})
		}
	}

	if (!out.length) {
		toast.warn("Quantity required", "Enter an input quantity for at least one route.")
		await focusFirstCombination("weight")
		return
	}

	saving.value = true
	try {
		emit("calculating")
		const res = await callMethod(`${API}.calculate_deliverables`, {
			work_order: props.workOrder,
			rows: JSON.stringify(out),
			modified: props.modified,
		})
		emit("calculated", res || {})
		await close()
	} catch (e) {
		emit("calculation-failed")
		toast.error("Calculation failed", e.message)
	} finally {
		saving.value = false
	}
}

function combinationSelector(row, combinationIndex) {
	return `.cd-combination[data-route-key="${CSS.escape(rowKey(row))}"][data-combination-index="${combinationIndex}"]`
}

function focusCombination(row, combinationIndex, attribute = "") {
	const base = combinationSelector(row, combinationIndex)
	const selector = attribute
		? `${base} [data-attribute="${CSS.escape(attribute)}"]`
		: `${base} ${(row.attributes || []).length > 1 ? "[data-attribute]" : "[data-weight]"}`
	return focusFirstControl(rowsEl, { selector })
}

function focusFirstCombination(preference = "") {
	const row = rows.value.find(canCalculate)
	if (!row) return false
	if (preference === "weight") {
		return focusFirstControl(rowsEl, { selector: `${combinationSelector(row, 0)} [data-weight]` })
	}
	return focusCombination(row, 0)
}
</script>

<style scoped>
.cd-selection {
	display: grid;
	grid-template-columns: minmax(220px, .7fr) minmax(320px, 1.3fr);
	gap: 18px;
	align-items: center;
	margin-bottom: 14px;
	padding: 14px 16px;
	border: 1px solid var(--mgk-line);
	border-radius: 12px;
	background: #fbfaf7;
}
.cd-selection-copy {
	display: grid;
	gap: 4px;
}
.cd-selection-copy span {
	color: var(--mgk-ink);
	font-size: 13px;
	font-weight: 700;
}
.cd-selection-copy small {
	color: var(--mgk-muted);
	font-size: 11.5px;
	line-height: 1.4;
}
.cd-factor {
	margin: 0 0 14px;
	padding: 9px 12px;
	border-left: 3px solid #149184;
	border-radius: 4px 9px 9px 4px;
	background: #eef8f6;
	color: var(--mgk-muted);
	font-size: 12.5px;
}
.cd-rows {
	display: flex;
	flex-direction: column;
	gap: 14px;
	max-height: 58vh;
	padding-right: 2px;
	overflow-y: auto;
}
.cd-ipd {
	overflow: hidden;
	border: 1px solid var(--mgk-line);
	border-radius: 12px;
	background: #fff;
}
.cd-ipd-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 14px;
	padding: 12px 14px;
	border-bottom: 1px solid var(--mgk-line);
	background: #f7f3ec;
}
.cd-ipd-head > div {
	display: grid;
	gap: 3px;
	min-width: 0;
}
.cd-ipd-head strong {
	overflow: hidden;
	color: var(--mgk-ink);
	font-size: 14px;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.cd-ipd-head small {
	overflow: hidden;
	color: var(--mgk-muted);
	font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
	font-size: 10.5px;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.cd-ipd-head > span {
	flex: 0 0 auto;
	padding: 4px 8px;
	border-radius: 999px;
	background: #ece4d8;
	color: #76533c;
	font-size: 10.5px;
	font-weight: 700;
}
.cd-ipd-attributes {
	display: grid;
	gap: 10px;
	padding: 12px 14px;
	border-bottom: 1px solid var(--mgk-line);
	background: #fcfbf8;
}
.cd-context-title {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: 12px;
}
.cd-context-title span {
	color: var(--mgk-ink);
	font-size: 11px;
	font-weight: 800;
	letter-spacing: .045em;
	text-transform: uppercase;
}
.cd-context-title small,
.cd-context-attribute > small {
	color: var(--mgk-muted);
	font-size: 10.5px;
}
.cd-context-list {
	display: flex;
	flex-wrap: wrap;
	gap: 8px 18px;
}
.cd-context-attribute {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 6px;
}
.cd-context-attribute > strong {
	color: var(--mgk-muted);
	font-size: 11px;
}
.cd-value-chips {
	display: flex;
	flex-wrap: wrap;
	gap: 5px;
}
.cd-value-chips span {
	padding: 3px 8px;
	border-radius: 999px;
	background: #e4f3ef;
	color: #087c71;
	font-size: 10.5px;
	font-weight: 700;
}
.cd-row {
	padding: 13px 14px 14px;
}
.cd-row + .cd-row {
	border-top: 1px solid var(--mgk-line);
}
.cd-row-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	flex-wrap: wrap;
	gap: 10px;
	margin-bottom: 10px;
}
.cd-route-main {
	display: flex;
	align-items: baseline;
	flex-wrap: wrap;
	gap: 10px;
}
.cd-idx {
	padding: 2px 7px;
	border-radius: 6px;
	background: #eef1f5;
	color: var(--mgk-muted);
	font-size: 10.5px;
	font-weight: 700;
	letter-spacing: .035em;
	text-transform: uppercase;
}
.cd-yarn {
	color: var(--mgk-ink);
	font-size: 13.5px;
	font-weight: 650;
}
.cd-arrow {
	color: var(--mgk-muted);
	font-size: 11px;
}
.cd-ratio {
	padding: 3px 8px;
	border-radius: 999px;
	background: #e8f5f2;
	color: #087c71;
	font-size: 11px;
	font-weight: 700;
}
.cd-colour-transition {
	display: grid;
	grid-template-columns: minmax(150px, 1fr) 28px minmax(150px, 1fr);
	align-items: center;
	gap: 10px;
	margin-bottom: 10px;
	padding: 10px 12px;
	border: 1px solid #d8e9e5;
	border-radius: 10px;
	background: #f3faf8;
}
.cd-colour-side {
	display: grid;
	gap: 2px;
}
.cd-colour-side small {
	color: var(--mgk-muted);
	font-size: 10px;
	font-weight: 750;
	letter-spacing: .04em;
	text-transform: uppercase;
}
.cd-colour-side strong {
	color: var(--mgk-ink);
	font-size: 14px;
}
.cd-colour-output {
	text-align: right;
}
.cd-colour-output strong {
	color: #087c71;
}
.cd-colour-arrow {
	display: grid;
	place-items: center;
	width: 28px;
	height: 28px;
	border-radius: 50%;
	background: #dff1ed;
	color: #087c71;
	font-size: 11px;
}
.cd-combinations {
	display: grid;
	gap: 8px;
}
.cd-combination {
	display: grid;
	grid-template-columns: 26px minmax(0, 1fr) 34px;
	align-items: end;
	gap: 10px;
	padding: 10px;
	border: 1px solid #e3e6eb;
	border-radius: 10px;
	background: #fafbfc;
}
.cd-combination-index {
	display: grid;
	place-items: center;
	align-self: center;
	width: 24px;
	height: 24px;
	border-radius: 7px;
	background: var(--mgk-ink);
	color: #fff;
	font-size: 10.5px;
	font-weight: 800;
}
.cd-fields {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: 12px;
	align-items: flex-end;
}
.cd-field {
	display: flex;
	flex-direction: column;
	gap: 5px;
	min-width: 0;
}
.cd-field-weight {
	max-width: 240px;
}
.cd-remove {
	align-self: center;
}
.cd-add-combination {
	justify-self: start;
}
.cd-label {
	color: var(--mgk-muted);
	font-size: 11px;
	font-weight: 700;
	letter-spacing: .025em;
	text-transform: uppercase;
}
.cd-empty {
	display: grid;
	justify-items: center;
	gap: 6px;
	padding: 34px 18px;
	border: 1px dashed var(--mgk-line);
	border-radius: 12px;
	background: #fbfaf8;
	color: var(--mgk-muted);
	text-align: center;
}
.cd-empty i {
	display: grid;
	place-items: center;
	width: 34px;
	height: 34px;
	margin-bottom: 2px;
	border-radius: 50%;
	background: #e9f4f1;
	color: #108879;
}
.cd-empty strong {
	color: var(--mgk-ink);
	font-size: 13.5px;
}
.cd-empty span {
	max-width: 520px;
	font-size: 12px;
	line-height: 1.5;
}
@media (max-width: 680px) {
	.cd-selection {
		grid-template-columns: 1fr;
		gap: 10px;
	}
	.cd-ipd-head {
		align-items: flex-start;
	}
	.cd-context-title {
		align-items: flex-start;
		flex-direction: column;
		gap: 3px;
	}
	.cd-row-head {
		align-items: center;
	}
	.cd-colour-transition {
		grid-template-columns: minmax(0, 1fr) 28px minmax(0, 1fr);
	}
	.cd-fields {
		grid-template-columns: 1fr;
	}
	.cd-combination {
		grid-template-columns: 24px minmax(0, 1fr) 32px;
		align-items: start;
	}
	.cd-field-weight {
		max-width: none;
	}
}
</style>
