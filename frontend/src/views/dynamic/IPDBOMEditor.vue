<!--
  IPDBOMEditor — focused Item BOM entry for the MGK Item Production Detail.

  The base YRP data model remains authoritative: this component edits the
  Item Production Detail.item_bom child rows and leaves Item BOM Attribute
  Mapping documents to the separate combinations popup.  A user first records
  the consumed Item and quantity ratio here, saves the IPD, then opens
  "Manage combinations" from the saved view when variant-specific quantities
  are needed.
-->
<template>
	<div class="ipd-bom-editor">
		<div v-if="rows.length" class="bom-table-wrap">
			<table class="bom-table">
				<thead>
					<tr>
						<th>#</th>
						<th>BOM Item</th>
						<th>Consumption</th>
						<th>UOM</th>
						<th>Process</th>
						<th v-if="dependentAttribute">{{ dependentAttribute }}</th>
						<th>Wastage</th>
						<th>Combinations</th>
						<th v-if="!readonly" aria-label="Row actions" />
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, index) in rows" :key="row.name || `bom-${index}`">
						<td class="row-number">{{ index + 1 }}</td>
						<td class="bom-item" data-label="BOM Item"><strong>{{ localizedItem(row.item) }}</strong></td>
						<td data-label="Consumption">
							<strong>{{ formatNumber(row.qty_of_bom_item) }}</strong>
							<small>for {{ formatNumber(row.qty_of_product) }} finished item</small>
						</td>
						<td data-label="UOM">{{ row.uom || "—" }}</td>
						<td data-label="Process">{{ row.process_name || "Any process" }}</td>
						<td v-if="dependentAttribute" :data-label="dependentAttribute">{{ row.dependent_attribute_value || "Any" }}</td>
						<td data-label="Wastage">{{ Number(row.wastage_pct || 0) ? `${formatNumber(row.wastage_pct)}%` : "—" }}</td>
						<td class="mapping-cell" data-label="Combinations">
							<button
								v-if="readonly && canManageMappings"
								class="mapping-button"
								type="button"
								:disabled="!row.name || !productionDetail"
								@click="$emit('manage-mapping', row)"
							>
								<i :class="row.attribute_mapping ? 'pi pi-table' : 'pi pi-plus-circle'" />
								{{ row.attribute_mapping ? "Edit combinations" : "Manage combinations" }}
							</button>
							<span v-else-if="row.attribute_mapping" class="mapping-state configured">
								<i class="pi pi-check-circle" /> Configured
							</span>
							<span v-else class="mapping-state">After saving</span>
						</td>
						<td v-if="!readonly" class="row-action-cell">
							<div class="row-actions">
								<Button icon="pi pi-pencil" text rounded severity="secondary" size="small" aria-label="Edit BOM row" @click="editRow(index)" />
								<Button icon="pi pi-trash" text rounded severity="danger" size="small" aria-label="Delete BOM row" @click="removeRow(index)" />
							</div>
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<div v-else class="bom-empty">
			<span class="empty-icon"><i class="pi pi-box" /></span>
			<div>
				<strong>No BOM Items yet</strong>
				<small>Add the yarn, packing material, or other Item consumed to produce this finished Item.</small>
			</div>
		</div>

		<div v-if="!readonly && editorOpen" ref="editorEl" class="bom-form">
			<div class="bom-form-title">
				<div><small>{{ editingIndex >= 0 ? "UPDATE BOM ITEM" : "NEW BOM ITEM" }}</small><strong>{{ editingIndex >= 0 ? `Edit row ${editingIndex + 1}` : "Define consumption" }}</strong></div>
				<Button icon="pi pi-times" text rounded severity="secondary" aria-label="Close BOM editor" @click="closeEditor" />
			</div>
			<div class="bom-form-grid">
				<div class="bom-field bom-field-wide" data-focus-key="item">
					<label>BOM Item <span>*</span></label>
					<LinkField
						:model-value="draft.item"
						@update:model-value="draft.item = $event"
						target-doctype="Item"
						placeholder="Search the consumed Item…"
						@item-select="onBomItemChanged"
						@change="onBomItemChanged"
					/>
				</div>
				<div class="bom-field" data-focus-key="finished-qty">
					<label>Finished Qty <span>*</span></label>
					<InputNumber v-model="draft.qty_of_product" :min="0.000001" :maxFractionDigits="6" fluid />
					<small>Usually 1 finished item.</small>
				</div>
				<div class="bom-field" data-focus-key="bom-qty">
					<label>BOM Qty <span>*</span></label>
					<InputNumber v-model="draft.qty_of_bom_item" :min="0.000001" :maxFractionDigits="6" fluid />
					<small>Quantity consumed for the finished qty.</small>
				</div>
				<div class="bom-field">
					<label>UOM</label>
					<InputText v-model="draft.uom" readonly placeholder="From the BOM Item" fluid />
				</div>
				<div class="bom-field">
					<label>Process</label>
					<LinkField v-model="draft.process_name" target-doctype="Process" placeholder="Optional process…" />
				</div>
				<div v-if="dependentAttribute" class="bom-field">
					<label>{{ dependentAttribute }}</label>
					<LinkField
						v-model="draft.dependent_attribute_value"
						target-doctype="Item Attribute Value"
						:filters="{ attribute_name: dependentAttribute }"
						:placeholder="`Optional ${dependentAttribute}…`"
					/>
				</div>
				<div class="bom-field">
					<label>Wastage %</label>
					<InputNumber v-model="draft.wastage_pct" :min="0" :maxFractionDigits="3" suffix=" %" fluid />
				</div>
			</div>
			<div class="bom-form-actions">
				<Button label="Cancel" icon="pi pi-times" severity="secondary" outlined @click="closeEditor" />
				<Button :label="editingIndex >= 0 ? 'Update BOM Item' : 'Add BOM Item'" icon="pi pi-check" @click="saveDraft" />
			</div>
		</div>

		<button v-else-if="!readonly" ref="addButtonEl" class="add-bom-button" type="button" @click="openAdd">
			<i class="pi pi-plus" /> Add BOM Item
		</button>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch, nextTick } from "vue"
import Button from "primevue/button"
import InputNumber from "primevue/inputnumber"
import InputText from "primevue/inputtext"
import LinkField from "@/components/LinkField.vue"
import { callMethod } from "@/api/client"
import { useLinkTitles } from "@/composables/useLinkTitles"
import { useAppToast } from "@/composables/useToast"
import { focusFirstControl } from "@/utils/focusControl"

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	productionDetail: { type: String, default: "" },
	dependentAttribute: { type: String, default: "" },
	readonly: { type: Boolean, default: false },
	canManageMappings: { type: Boolean, default: false },
})

const emit = defineEmits(["update:modelValue", "change", "manage-mapping", "summary"])
const toast = useAppToast()
const linkTitles = useLinkTitles()
const editorOpen = ref(false)
const editingIndex = ref(-1)
const editorEl = ref(null)
const addButtonEl = ref(null)

function emptyDraft() {
	return {
		item: "",
		qty_of_product: 1,
		qty_of_bom_item: 1,
		uom: "",
		process_name: "",
		dependent_attribute_value: "",
		based_on_attribute_mapping: 0,
		attribute_mapping: "",
		wastage_pct: 0,
	}
}

const draft = reactive(emptyDraft())
const rows = computed(() => Array.isArray(props.modelValue) ? props.modelValue : [])

function localizedItem(value) {
	return linkTitles.titleFor("Item", value) || value || "—"
}

watch(rows, (value) => {
	emit("summary", {
		itemCount: value.length,
		mappedCount: value.filter((row) => row.attribute_mapping).length,
	})
}, { deep: true, immediate: true })

function resetDraft(value = {}) {
	Object.assign(draft, emptyDraft(), value)
}

async function openAdd() {
	editingIndex.value = -1
	resetDraft()
	editorOpen.value = true
	await focusBomField("item")
}

async function editRow(index) {
	editingIndex.value = index
	resetDraft(rows.value[index] || {})
	editorOpen.value = true
	await focusBomField("item")
}

async function closeEditor() {
	editorOpen.value = false
	editingIndex.value = -1
	resetDraft()
	await nextTick()
	addButtonEl.value?.focus?.()
}

function emitRows(next) {
	emit("update:modelValue", next)
	emit("change", next)
}

async function saveDraft() {
	if (!String(draft.item || "").trim()) {
		toast.warn("BOM Item required", "Select the Item consumed by this production detail.")
		focusBomField("item")
		return
	}
	if (!(Number(draft.qty_of_product) > 0) || !(Number(draft.qty_of_bom_item) > 0)) {
		toast.warn("Quantity required", "Finished Qty and BOM Qty must both be greater than zero.")
		focusBomField(!(Number(draft.qty_of_product) > 0) ? "finished-qty" : "bom-qty")
		return
	}
	const next = rows.value.map((row) => ({ ...row }))
	const patch = {
		item: draft.item,
		qty_of_product: Number(draft.qty_of_product),
		qty_of_bom_item: Number(draft.qty_of_bom_item),
		uom: draft.uom || "",
		process_name: draft.process_name || "",
		dependent_attribute_value: draft.dependent_attribute_value || "",
		based_on_attribute_mapping: draft.based_on_attribute_mapping ? 1 : 0,
		attribute_mapping: draft.attribute_mapping || "",
		wastage_pct: Number(draft.wastage_pct || 0),
	}
	const wasEditing = editingIndex.value >= 0
	if (wasEditing) next[editingIndex.value] = { ...next[editingIndex.value], ...patch }
	else next.push({ doctype: "Item BOM", ...patch })
	emitRows(next)
	if (wasEditing) await closeEditor()
	else {
		resetDraft()
		await focusBomField("item")
	}
}

function removeRow(index) {
	const next = rows.value.map((row) => ({ ...row }))
	next.splice(index, 1)
	emitRows(next)
	if (editingIndex.value === index) closeEditor()
}

async function onBomItemChanged() {
	if (!draft.item) {
		draft.uom = ""
		return
	}
	try {
		const value = await callMethod("frappe.client.get_value", {
			doctype: "Item",
			filters: draft.item,
			fieldname: "default_unit_of_measure",
		})
		draft.uom = value?.default_unit_of_measure || ""
	} catch (error) {
		draft.uom = ""
		toast.warn("Could not fetch UOM", error.message)
	}
	if (draft.item) await focusBomField("finished-qty")
}

function focusBomField(key) {
	return focusFirstControl(editorEl, { selector: `[data-focus-key="${key}"]` })
}

function formatNumber(value) {
	const number = Number(value || 0)
	return Number.isFinite(number)
		? number.toLocaleString("en-IN", { maximumFractionDigits: 6 })
		: "0"
}
</script>

<style scoped>
.ipd-bom-editor { display: grid; gap: 14px; }
.bom-table-wrap { overflow-x: auto; border: 1px solid #e3d8c7; border-radius: 12px; }
.bom-table { width: 100%; min-width: 940px; border-collapse: collapse; color: #1c273a; font-size: 12.5px; }
.bom-table th { padding: 10px 12px; background: #14233c; color: #fff; font-size: 10px; letter-spacing: .045em; text-align: left; text-transform: uppercase; white-space: nowrap; }
.bom-table td { padding: 11px 12px; border-top: 1px solid #ece4d8; vertical-align: middle; }
.bom-table tbody tr:first-child td { border-top: 0; }
.bom-table tbody tr:hover { background: #fbf8f3; }
.bom-table td small { display: block; margin-top: 2px; color: #667085; font-size: 10px; white-space: nowrap; }
.row-number { width: 34px; color: #667085; }
.bom-item strong { color: #087f72; white-space: nowrap; }
.row-actions { display: flex; justify-content: flex-end; }
.mapping-button { display: inline-flex; align-items: center; gap: 6px; padding: 7px 10px; border: 1px solid #b8dcd5; border-radius: 8px; background: #edf8f5; color: #087f72; font: inherit; font-weight: 700; white-space: nowrap; cursor: pointer; }
.mapping-button:hover { background: #dff2ed; }
.mapping-button:disabled { cursor: not-allowed; opacity: .5; }
.mapping-state { color: #8a7762; font-size: 11px; white-space: nowrap; }
.mapping-state.configured { color: #087f72; }
.bom-empty { display: flex; align-items: center; gap: 12px; min-height: 86px; padding: 16px; border: 1px dashed #d9cbb8; border-radius: 12px; background: #fcfaf6; }
.empty-icon { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 11px; background: #f2e8d6; color: #a66f20; }
.bom-empty strong, .bom-empty small { display: block; }
.bom-empty small { margin-top: 3px; color: #667085; }
.add-bom-button { display: inline-flex; align-items: center; justify-content: center; gap: 7px; width: max-content; padding: 9px 14px; border: 1px solid #d0c3b2; border-radius: 9px; background: #fff; color: #14233c; font: inherit; font-weight: 700; cursor: pointer; }
.add-bom-button:hover { border-color: #087f72; color: #087f72; }
.bom-form { overflow: hidden; border: 1px solid #d9c7aa; border-radius: 13px; background: #fffcf6; }
.bom-form-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 13px 16px; border-bottom: 1px solid #eadfce; background: #f8f1e6; }
.bom-form-title small, .bom-form-title strong { display: block; }
.bom-form-title small { color: #9b3d2e; font-size: 9px; font-weight: 800; letter-spacing: .08em; }
.bom-form-title strong { margin-top: 2px; font-size: 14px; }
.bom-form-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; padding: 16px; }
.bom-field { min-width: 0; }
.bom-field-wide { grid-column: span 2; }
.bom-field label { display: block; margin-bottom: 6px; color: #56647a; font-size: 10px; font-weight: 800; letter-spacing: .045em; text-transform: uppercase; }
.bom-field label span { color: #b94d3d; }
.bom-field > small { display: block; margin-top: 4px; color: #778197; font-size: 10px; }
.bom-form-actions { display: flex; justify-content: flex-end; gap: 8px; padding: 0 16px 16px; }
@media (max-width: 760px) {
	.bom-form-grid { grid-template-columns: 1fr; }
	.bom-field-wide { grid-column: auto; }
	.add-bom-button { width: 100%; }
	.bom-table-wrap { overflow: visible; border: 0; }
	.bom-table { display: block; min-width: 0; }
	.bom-table thead { display: none; }
	.bom-table tbody { display: grid; gap: 10px; }
	.bom-table tr { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0; padding: 8px; border: 1px solid #e3d8c7; border-radius: 11px; background: #fff; }
	.bom-table td { display: grid; gap: 3px; min-width: 0; padding: 8px; border: 0 !important; }
	.bom-table td[data-label]::before { content: attr(data-label); color: #667085; font-size: 9px; font-weight: 800; letter-spacing: .045em; text-transform: uppercase; }
	.bom-table .row-number { display: none; }
	.bom-table .bom-item,
	.bom-table .mapping-cell,
	.bom-table .row-action-cell { grid-column: 1 / -1; }
	.mapping-button { justify-content: center; width: 100%; }
	.row-actions { justify-content: flex-start; }
}
</style>
