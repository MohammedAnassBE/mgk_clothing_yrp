<template>
	<div ref="editorEl" class="pi-entry-editor">
		<section class="pi-step">
			<header>
				<span class="step-number">1</span>
				<div><h3>Supplier bill details</h3><p>Identify the supplier bill before selecting received notes.</p></div>
				<span class="against-chip">{{ form.against || "Billing source" }}</span>
			</header>
			<div class="step-body header-grid">
				<div class="field" data-focus-key="supplier">
					<label>Supplier <b>*</b></label>
					<LinkField
						v-model="form.supplier"
						target-doctype="Supplier"
						:filters="{ disabled: 0 }"
						:route-resolver="routeResolver"
						@item-select="onSupplierSelected"
						@change="onSupplierCleared"
					/>
					<small>Only submitted, unbilled GRNs for this supplier will be available.</small>
				</div>
				<div class="field" data-focus-key="billing-supplier">
					<label>Billing supplier <b>*</b></label>
					<LinkField
						ref="billingSupplierFieldEl"
						v-model="form.billing_supplier"
						target-doctype="Supplier"
						:filters="{ disabled: 0 }"
						:route-resolver="routeResolver"
					/>
				</div>
				<div class="field" data-focus-key="bill-number">
					<label>Supplier invoice no <b>*</b></label>
					<InputText v-model="form.bill_no" class="control" />
				</div>
				<div class="field">
					<label>Supplier invoice date <b>*</b></label>
					<DatePicker
						:model-value="toDateValue(form.bill_date)"
						@update:model-value="form.bill_date = fromDateValue($event)"
						date-format="dd-mm-yy"
						show-icon
						icon-display="input"
						show-button-bar
						class="control"
						fluid
					/>
				</div>
				<div class="field">
					<label>Posting date <b>*</b></label>
					<DatePicker
						:model-value="toDateValue(form.posting_date)"
						@update:model-value="form.posting_date = fromDateValue($event)"
						date-format="dd-mm-yy"
						show-icon
						icon-display="input"
						show-button-bar
						class="control"
						fluid
					/>
				</div>
				<div class="field">
					<label>Due date</label>
					<DatePicker
						:model-value="toDateValue(form.due_date)"
						@update:model-value="form.due_date = fromDateValue($event)"
						date-format="dd-mm-yy"
						show-icon
						icon-display="input"
						show-button-bar
						class="control"
						fluid
					/>
				</div>
			</div>
		</section>

		<section class="pi-step">
			<header>
				<span class="step-number">2</span>
				<div><h3>Select Goods Received Notes</h3><p>Select only the GRNs included in this supplier bill.</p></div>
			</header>
			<div class="step-body">
				<div v-if="!canLoad" class="empty-state"><i class="pi pi-user" /><strong>Select the supplier first</strong><span>Then search using the GRN number on the printed document.</span></div>
				<template v-else>
					<div class="table-wrap grn-link-table-wrap">
					<table class="grn-link-table">
						<thead><tr><th class="row-number-col">#</th><th>GRN</th><th class="remove-col"></th></tr></thead>
						<tbody>
							<tr v-for="(row, index) in grnRows" :key="row.key">
								<td class="row-number-col">{{ index + 1 }}</td>
								<td>
									<LinkField
										:ref="(el) => setGrnFieldRef(row.key, el)"
										:model-value="row.grn"
										target-doctype="Goods Received Note"
										placeholder="Search GRN…"
										:dropdown="false"
										:search-delay="350"
										:search-handler="(query) => searchEligibleGrns(query, row)"
										:route-resolver="routeResolver"
										@update:model-value="updateGrnRow(row, $event)"
									/>
								</td>
								<td class="remove-col"><button type="button" aria-label="Remove GRN row" @click="removeGrnRow(index)"><i class="pi pi-trash" /></button></td>
							</tr>
						</tbody>
					</table>
					</div>
					<div class="grn-entry-footer">
						<Button label="Add GRN row" icon="pi pi-plus" size="small" severity="secondary" outlined @click="addGrnRow" />
						<small>Type the printed GRN number and select a suggestion. Only submitted, unbilled {{ sourceLabel }} GRNs for this Supplier are shown.</small>
					</div>
				</template>
				<div v-if="canLoad" class="fetch-row">
					<span v-if="selectionChanged" class="selection-note"><i class="pi pi-info-circle" /> Selection changed. Fetch again to rebuild the billed items.</span>
					<span v-else class="selected-count">{{ selectedGrnNames.length }} GRN{{ selectedGrnNames.length === 1 ? "" : "s" }} selected</span>
					<Button label="Fetch selected GRNs" icon="pi pi-download" :loading="fetching" :disabled="!selectedGrnNames.length" @click="fetchSelected" />
				</div>
			</div>
		</section>

		<section class="pi-step">
			<header>
				<span class="step-number">3</span>
				<div><h3>Billed items</h3><p>Rows with the same item and price are combined. Different prices stay separate.</p></div>
				<span class="item-count">{{ items.length }} item{{ items.length === 1 ? "" : "s" }}</span>
			</header>
			<div class="step-body">
				<div v-if="!items.length" class="empty-state compact"><i class="pi pi-calculator" /><strong>Fetch the selected GRNs</strong><span>Items, quantities, rates and totals will be prepared automatically.</span></div>
				<div v-else class="table-wrap">
					<table class="item-table">
						<thead><tr><th>#</th><th>Item</th><th class="number">Quantity</th><th>UOM</th><th class="rate-col">Rate</th><th>Tax</th><th class="number">Amount</th></tr></thead>
						<tbody>
							<tr v-for="(row, index) in items" :key="row.name || `${row.item}-${index}`">
								<td>{{ index + 1 }}</td>
								<td><strong class="item-name">{{ localizedItem(row.item) }}</strong><small v-if="row.item_group">{{ row.item_group }}</small></td>
								<td class="number">{{ number(row.qty) }}</td>
								<td>{{ row.uom || "—" }}</td>
								<td class="rate-col" :data-rate-index="index"><InputNumber :model-value="row.rate" mode="currency" currency="INR" locale="en-IN" :min="0" :max-fraction-digits="4" fluid @update:model-value="updateRate(row, $event)" /></td>
								<td>{{ row.tax || "No tax" }}</td>
								<td class="number"><strong>₹ {{ number(row.amount) }}</strong></td>
							</tr>
						</tbody>
					</table>
				</div>
			</div>
		</section>

		<section class="pi-step notes-step">
			<header><span class="step-number">4</span><div><h3>Notes</h3><p>Add any billing reference or instruction needed later.</p></div></header>
			<div class="step-body"><Textarea v-model="form.remarks" rows="3" auto-resize class="control" /></div>
		</section>
	</div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue"
import Button from "primevue/button"
import DatePicker from "primevue/datepicker"
import InputNumber from "primevue/inputnumber"
import InputText from "primevue/inputtext"
import Textarea from "primevue/textarea"
import LinkField from "@/components/LinkField.vue"
import { callMethod } from "@/api/client"
import { useAppToast } from "@/composables/useToast"
import { useLinkTitles } from "@/composables/useLinkTitles"
import { focusFirstControl } from "@/utils/focusControl"

const props = defineProps({
	form: { type: Object, required: true },
	documentName: { type: String, default: "" },
	routeResolver: { type: Function, default: null },
})
const emit = defineEmits(["summary"])
const toast = useAppToast()
const linkTitles = useLinkTitles()
const fetching = ref(false)
const grnRows = ref([])
const fetchedSignature = ref("")
const taxRates = ref({})
const editorEl = ref(null)
const billingSupplierFieldEl = ref(null)
const grnFieldRefs = new Map()
let grnRowSequence = 0

const form = props.form
const canLoad = computed(() => !!form.supplier && ["Purchase Order", "Work Order"].includes(form.against))
const sourceLabel = computed(() => form.against || "source")
const items = computed(() => Array.isArray(form.items) ? form.items : [])
const selectedGrnNames = computed(() => [...new Set(grnRows.value.map((row) => row.grn).filter(Boolean))].sort())
const selectionSignature = computed(() => selectedGrnNames.value.join("|"))
const selectionChanged = computed(() => !!items.value.length && fetchedSignature.value !== selectionSignature.value)

function localizedItem(value) {
	if (!value) return "—"
	return linkTitles.titleFor("Item", value) || String(value)
}

function makeGrnRow(grn = "") {
	return { key: `grn-${++grnRowSequence}`, grn }
}

function syncSelectedFromForm() {
	const existing = (form.grn || []).map((row) => row.grn).filter(Boolean)
	grnRows.value = existing.length ? existing.map(makeGrnRow) : [makeGrnRow()]
	form.grn = existing.map((grn) => ({ grn }))
	fetchedSignature.value = items.value.length ? selectionSignature.value : ""
}

async function searchEligibleGrns(query, currentRow) {
	const text = String(query || "").trim()
	if (!canLoad.value || !text) return []
	const rows = await callMethod(
		"yrp.yrp.doctype.purchase_invoice.purchase_invoice.get_eligible_grns",
		{
			supplier: form.supplier,
			against: form.against,
			search_text: text,
			purchase_invoice: props.documentName || null,
			limit: 20,
		},
	)
	const alreadyUsed = new Set(grnRows.value.filter((row) => row !== currentRow).map((row) => row.grn).filter(Boolean))
	return (Array.isArray(rows) ? rows : [])
		.filter((row) => !alreadyUsed.has(row.name))
		.map((row) => ({ name: row.name, label: row.name }))
}

function clearFetchedRows() {
	form.items = []
	if ("pi_work_order_billed_details" in form) form.pi_work_order_billed_details = []
	for (const field of ["total", "total_tax", "grand_total", "grn_grand_total", "total_quantity"]) {
		if (field in form) form[field] = 0
	}
	fetchedSignature.value = ""
	emitSummary()
}

function updateGrnRow(row, value) {
	const grn = String(value || "")
	if (grn && grnRows.value.some((other) => other !== row && other.grn === grn)) {
		row.grn = ""
		toast.error("GRN already selected", `${grn} is already in this bill.`)
		return
	}
	row.grn = grn
	form.grn = selectedGrnNames.value.map((name) => ({ grn: name }))
	clearFetchedRows()
}

async function addGrnRow() {
	const row = makeGrnRow()
	grnRows.value.push(row)
	await focusGrnRow(row)
}

async function removeGrnRow(index) {
	grnRows.value.splice(index, 1)
	if (!grnRows.value.length) grnRows.value.push(makeGrnRow())
	form.grn = selectedGrnNames.value.map((grn) => ({ grn }))
	clearFetchedRows()
	await focusGrnRow(grnRows.value[Math.min(index, grnRows.value.length - 1)])
}

async function fetchSelected() {
	if (!selectedGrnNames.value.length) return
	fetching.value = true
	try {
		const result = await callMethod(
			"yrp.yrp.doctype.purchase_invoice.purchase_invoice.fetch_grn_details",
			{
				grns: JSON.stringify(selectedGrnNames.value),
				against: form.against,
				supplier: form.supplier,
				purchase_invoice: props.documentName || null,
			},
		)
		form.items = (result?.items || []).map((row) => ({ ...row }))
		if ("pi_work_order_billed_details" in form) form.pi_work_order_billed_details = (result?.wo_items || []).map((row) => ({ ...row }))
		form.allow_to_change_rate = result?.allow_to_change_rate ? 1 : 0
		taxRates.value = result?.tax_rates || {}
		fetchedSignature.value = selectionSignature.value
		recalculate()
		toast.success("GRNs fetched", `${form.items.length} grouped item row(s) prepared.`)
		if (form.items.length) await focusFirstControl(editorEl, { selector: '[data-rate-index="0"]' })
	} catch (error) {
		toast.error("Could not fetch GRNs", error?.message || "Please try again.")
	} finally {
		fetching.value = false
	}
}

function taxRate(row) {
	if (!row?.tax) return 0
	if (taxRates.value[row.tax] !== undefined) return Number(taxRates.value[row.tax]) || 0
	const numeric = String(row.tax).match(/\d+(?:\.\d+)?/)
	return numeric ? Number(numeric[0]) : 0
}

function updateRate(row, value) {
	row.rate = Number(value) || 0
	recalculate()
}

function recalculate() {
	let subtotal = 0
	let tax = 0
	let quantity = 0
	for (const row of items.value) {
		const qty = Number(row.qty) || 0
		const rate = Number(row.rate) || 0
		row.amount = qty * rate
		subtotal += row.amount
		tax += row.amount * taxRate(row) / 100
		quantity += qty
	}
	form.total = subtotal
	form.total_tax = tax
	form.grand_total = subtotal + tax
	form.total_quantity = quantity
	emitSummary()
}

function emitSummary() {
	const subtotal = items.value.reduce((sum, row) => sum + (Number(row.amount) || (Number(row.qty) || 0) * (Number(row.rate) || 0)), 0)
	const quantity = items.value.reduce((sum, row) => sum + (Number(row.qty) || 0), 0)
	emit("summary", {
		grnCount: selectedGrnNames.value.length,
		itemCount: items.value.length,
		totalQty: quantity,
		subtotal,
		tax: Number(form.total_tax) || 0,
		grandTotal: Number(form.grand_total) || subtotal,
		fetched: !!items.value.length && fetchedSignature.value === selectionSignature.value,
	})
}

function resetForContextChange(previousSupplier = "") {
	if (!form.billing_supplier || form.billing_supplier === previousSupplier) form.billing_supplier = form.supplier || ""
	form.grn = []
	grnRows.value = [makeGrnRow()]
	clearFetchedRows()
}

async function onSupplierSelected() {
	if (!form.billing_supplier) form.billing_supplier = form.supplier
	if (!form.bill_no) await focusFirstControl(editorEl, { selector: '[data-focus-key="bill-number"]' })
	else billingSupplierFieldEl.value?.focus?.()
}
function onSupplierCleared() {
	if (!form.supplier) resetForContextChange()
}

watch(
	() => [form.supplier, form.against],
	([supplier, against], [oldSupplier, oldAgainst] = []) => {
		if (oldSupplier !== undefined && (supplier !== oldSupplier || against !== oldAgainst)) {
			resetForContextChange(oldSupplier)
		}
	},
)
watch(() => [form.total_tax, form.grand_total], emitSummary)

function number(value) {
	return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 3 }).format(Number(value) || 0)
}

function setGrnFieldRef(key, element) {
	if (element) grnFieldRefs.set(key, element)
	else grnFieldRefs.delete(key)
}

async function focusGrnRow(row) {
	if (!row) return false
	await nextTick()
	return grnFieldRefs.get(row.key)?.focus?.() || false
}

function focusFirstGrn() {
	return focusGrnRow(grnRows.value[0])
}

function toDateValue(value) {
	if (!value) return null
	if (value instanceof Date) return value
	const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/)
	if (!match) return null
	return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}

function fromDateValue(value) {
	if (!(value instanceof Date) || Number.isNaN(value.getTime())) return ""
	const pad = (part) => String(part).padStart(2, "0")
	return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
}

onMounted(() => {
	syncSelectedFromForm()
	emitSummary()
})

defineExpose({ focusFirstGrn })
</script>

<style scoped>
.pi-entry-editor { display: flex; flex-direction: column; gap: 18px; }
.pi-step { overflow: hidden; border: 1px solid var(--book-line, #ded5c7); border-radius: 16px; background: var(--book-paper, #fffdf9); box-shadow: 0 7px 22px rgba(42,35,27,.045); }
.pi-step > header { display: flex; align-items: center; gap: 11px; min-height: 58px; padding: 12px 18px; border-bottom: 1px solid var(--book-line, #ded5c7); background: linear-gradient(90deg, var(--book-cream, #f7f1e7), #fcfaf5); }
.pi-step > header > div { min-width: 0; }
.pi-step h3 { margin: 0; color: #1d2739; font-size: 16.5px; }
.pi-step header p { margin: 3px 0 0; color: #667085; font-size: 12px; }
.step-number { display: grid; place-items: center; flex: 0 0 28px; width: 28px; height: 28px; border-radius: 8px; background: #14233c; color: #fff; font-size: 12px; font-weight: 800; }
.against-chip, .item-count { margin-left: auto; padding: 6px 10px; border-radius: 999px; background: #f2e5df; color: #873529; font-size: 11px; font-weight: 800; }
.step-body { padding: 16px 18px 18px; }
.header-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px 22px; }
.field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.field label { color: #667085; font-size: 12px; font-weight: 750; letter-spacing: .035em; text-transform: uppercase; }
.field label b { color: #b42318; }
.field small { color: #778197; font-size: 11.5px; }
.control { width: 100%; }
.table-wrap { overflow-x: auto; border: 1px solid #ded7cc; border-radius: 12px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { padding: 10px 12px; background: #14233c; color: #fff; font-size: 11px; letter-spacing: .035em; text-align: left; text-transform: uppercase; white-space: nowrap; }
td { padding: 11px 12px; border-bottom: 1px solid #e7e1d8; color: #253047; vertical-align: middle; }
tbody tr:last-child td { border-bottom: 0; }
.grn-link-table td { padding: 8px 10px; }
.row-number-col { width: 52px; text-align: center; }
.remove-col { width: 52px; text-align: center; }
.remove-col button { display: inline-grid; width: 30px; height: 30px; place-items: center; border: 0; border-radius: 7px; background: transparent; color: #e5483f; cursor: pointer; }
.remove-col button:hover { background: #fff0ee; }
.grn-entry-footer { display: flex; align-items: center; gap: 12px; margin-top: 11px; }
.grn-entry-footer small { color: #667085; font-size: 11.5px; }
.selected-count { margin-right: auto; color: #667085; font-size: 12px; font-weight: 700; }
.number { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.rate-col { width: 180px; }
.item-name { display: block; color: #007f72; }
.item-table td small { display: block; margin-top: 2px; color: #7a8496; }
.fetch-row { display: flex; align-items: center; justify-content: flex-end; gap: 12px; margin-top: 13px; }
.selection-note { margin-right: auto; color: #9a6500; font-size: 12px; }
.empty-state { display: flex; min-height: 128px; flex-direction: column; align-items: center; justify-content: center; gap: 6px; border: 1px dashed #d8d1c5; border-radius: 12px; background: #fbfaf7; color: #667085; text-align: center; }
.empty-state i { color: #8a94a6; font-size: 22px; }
.empty-state strong { color: #253047; }
.empty-state span { font-size: 12px; }
.empty-state.compact { min-height: 112px; }
.empty-state.error i { color: #c77a00; }
.notes-step .step-body { padding-top: 14px; }
@media (max-width: 760px) {
	.header-grid { grid-template-columns: 1fr; }
	.pi-step > header { align-items: flex-start; }
	.against-chip, .item-count { flex: 0 0 auto; }
	.grn-entry-footer, .fetch-row { align-items: stretch; flex-direction: column; }
	.fetch-row :deep(.p-button) { width: 100%; }
}
</style>
