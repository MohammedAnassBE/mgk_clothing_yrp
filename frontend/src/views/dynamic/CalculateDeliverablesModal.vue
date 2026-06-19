<!--
  CalculateDeliverablesModal — yarn-mode "Calculate Deliverables" for a draft
  Work Order. Mirrors the desk dialog (work_order_mgk.js): one block per
  mgk_items row showing the (read-only) yarn item, a Select per attribute (its
  options) and an InputNumber for weight. The wastage/excess factor is shown so
  the user understands what scales the receivable.

  The parent (DocDetail.vue) fetches the payload via get_yarn_deliverable_rows
  and opens this modal with the rows. On submit this component assembles the
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
		header="Calculate Deliverables"
		:style="{ width: '720px', maxWidth: '95vw' }"
		@update:visible="$emit('update:visible', $event)"
	>
		<p class="cd-factor">
			Wastage <b>{{ wastagePct }}%</b> · Excess <b>{{ excessPct }}%</b> →
			receivable = weight × <b>{{ factor }}</b>
		</p>

		<div class="cd-rows">
			<div v-for="row in rows" :key="row.idx" class="cd-row">
				<div class="cd-row-head">
					<span class="cd-idx">Row {{ row.idx }}</span>
					<span v-if="row.yarn_item" class="cd-yarn">{{
						row.yarn_item_name || row.yarn_item
					}}</span>
					<span v-else class="cd-item">{{ row.item }}</span>
				</div>

				<!-- No yarn item configured on the IPD — this row is skipped. -->
				<div v-if="!row.yarn_item" class="cd-skip">
					No Yarn Item is configured on Item Production Detail
					<code>{{ row.production_detail || "—" }}</code
					>; this row will be skipped.
				</div>

				<div v-else class="cd-fields">
					<!-- One Select per attribute. A yarn item with no attributes
					     contributes no selectors — just the weight input. -->
					<div
						v-for="attr in row.attributes"
						:key="attr.attribute"
						class="cd-field"
					>
						<label class="cd-label">{{ attr.label || attr.attribute }}</label>
						<Select
							v-model="form[row.idx].attrs[attr.attribute]"
							:options="attr.options"
							:placeholder="attr.label || attr.attribute"
							filter
							showClear
							fluid
						/>
					</div>

					<div class="cd-field cd-field-weight">
						<label class="cd-label">Weight{{ row.uom ? ` (${row.uom})` : "" }}</label>
						<InputNumber
							v-model="form[row.idx].weight"
							:min="0"
							:minFractionDigits="0"
							:maxFractionDigits="3"
							placeholder="0"
							fluid
						/>
					</div>
				</div>
			</div>

			<div v-if="!rows.length" class="cd-empty">
				No rows to calculate. Add Items to this Work Order first.
			</div>
		</div>

		<template #footer>
			<Button label="Cancel" text severity="secondary" @click="close" />
			<Button
				label="Calculate"
				icon="pi pi-calculator"
				:loading="saving"
				:disabled="!hasCalculableRow"
				@click="submit"
			/>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import Dialog from "primevue/dialog"
import Button from "primevue/button"
import Select from "primevue/select"
import InputNumber from "primevue/inputnumber"
import { callMethod } from "@/api/client"
import { useAppToast } from "@/composables/useToast"

const API = "mgk_clothing_yrp.mgk_clothing_yrp.api.work_order"

const props = defineProps({
	visible: { type: Boolean, default: false },
	workOrder: { type: String, required: true },
	// The get_yarn_deliverable_rows payload (rows, default_wastage, default_excess).
	payload: { type: Object, default: () => ({}) },
})

const emit = defineEmits(["update:visible", "calculated"])
const toast = useAppToast()

const saving = ref(false)
// Per-row editable state keyed by row idx: { weight, attrs:{attribute: value} }.
const form = ref({})

const rows = computed(() => props.payload?.rows || [])
const wastagePct = computed(() => num(props.payload?.default_wastage))
const excessPct = computed(() => num(props.payload?.default_excess))
const factor = computed(() =>
	(1 - wastagePct.value / 100 + excessPct.value / 100).toFixed(4),
)
const hasCalculableRow = computed(() => rows.value.some((r) => r.yarn_item))

// Rebuild the editable copy each time the modal opens (or the payload changes).
watch(
	() => props.visible,
	(open) => {
		if (open) seedForm()
	},
)

function seedForm() {
	const next = {}
	for (const row of rows.value) {
		const attrs = {}
		for (const attr of row.attributes || []) attrs[attr.attribute] = null
		next[row.idx] = { weight: null, attrs }
	}
	form.value = next
}

function num(v) {
	const n = parseFloat(v)
	return isNaN(n) ? 0 : n
}

function close() {
	emit("update:visible", false)
}

async function submit() {
	// Assemble one payload row per mgk_items row that has a yarn item. Validate
	// client-side (weight > 0, all attributes chosen) before hitting the server;
	// the server re-validates and throws clear messages we surface as toasts.
	const out = []
	for (const row of rows.value) {
		if (!row.yarn_item) continue // skipped — no yarn item on the IPD
		const state = form.value[row.idx] || { weight: null, attrs: {} }
		const weight = num(state.weight)
		if (weight <= 0) {
			toast.warn(
				"Weight required",
				`Enter a weight greater than zero for ${row.yarn_item_name || row.yarn_item} (row ${row.idx}).`,
			)
			return
		}
		const attribute_values = {}
		const missing = []
		for (const attr of row.attributes || []) {
			const val = state.attrs[attr.attribute]
			if (!val) missing.push(attr.label || attr.attribute)
			attribute_values[attr.attribute] = val
		}
		if (missing.length) {
			toast.warn(
				"Attribute required",
				`Select ${missing.join(", ")} for ${row.yarn_item_name || row.yarn_item} (row ${row.idx}).`,
			)
			return
		}
		out.push({
			production_detail: row.production_detail,
			yarn_item: row.yarn_item,
			attribute_values,
			weight,
		})
	}

	if (!out.length) {
		toast.warn("Nothing to calculate", "No rows with a configured Yarn Item.")
		return
	}

	saving.value = true
	try {
		const res = await callMethod(`${API}.calculate_deliverables`, {
			work_order: props.workOrder,
			rows: JSON.stringify(out),
		})
		emit("calculated", res || {})
		emit("update:visible", false)
	} catch (e) {
		toast.error("Calculation failed", e.message)
	} finally {
		saving.value = false
	}
}
</script>

<style scoped>
.cd-factor {
	margin: 0 0 14px;
	font-size: 12.5px;
	color: var(--mgk-muted);
	background: var(--mgk-slate-50);
	border-radius: var(--radius-sm);
	padding: 8px 12px;
}
.cd-rows {
	display: flex;
	flex-direction: column;
	gap: 12px;
	max-height: 60vh;
	overflow-y: auto;
}
.cd-row {
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius-sm);
	padding: 12px 14px;
}
.cd-row-head {
	display: flex;
	align-items: baseline;
	gap: 10px;
	margin-bottom: 10px;
}
.cd-idx {
	font-size: 11px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	color: var(--mgk-muted);
	background: var(--mgk-slate-50);
	padding: 1px 7px;
	border-radius: 6px;
}
.cd-yarn {
	font-size: 13.5px;
	font-weight: 600;
	color: var(--mgk-ink);
}
.cd-item {
	font-size: 13px;
	color: var(--mgk-muted);
}
.cd-skip {
	font-size: 12.5px;
	color: var(--mgk-muted);
	line-height: 1.5;
}
.cd-skip code {
	font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
	font-size: 11.5px;
	background: rgba(0, 0, 0, 0.05);
	padding: 1px 4px;
	border-radius: 3px;
}
.cd-fields {
	display: flex;
	flex-wrap: wrap;
	gap: 12px;
	align-items: flex-end;
}
.cd-field {
	display: flex;
	flex-direction: column;
	gap: 4px;
	min-width: 160px;
	flex: 1 1 160px;
}
.cd-field-weight {
	max-width: 200px;
}
.cd-label {
	font-size: 11.5px;
	font-weight: 600;
	color: var(--mgk-muted);
}
.cd-empty {
	padding: 16px;
	text-align: center;
	color: var(--mgk-muted);
	font-size: 13px;
}
</style>
