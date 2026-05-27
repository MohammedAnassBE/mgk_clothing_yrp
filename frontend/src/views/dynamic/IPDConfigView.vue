<!--
  IPDConfigView — dedicated detail view for Item Production Detail (R1a).

  Richer than the generic DocDetail: it surfaces the production-config flow the
  Desk IPD drives. Three working sections:

    1. Item BOM        — the bill-of-materials rows. Rows flagged
                         `based_on_attribute_mapping` link out to the Item BOM
                         Attribute Mapping editor (R1b — route exists, view lands
                         later; the link guards a null mapping).
    2. IPD Processes   — process rows (process_name / in_stage / out_stage). Each
                         row has "Configure combinations" → the synthesized
                         redirect into the IPD Process Matrix editor (find-or-new).
    3. Process Matrices — the existing IPD Process Matrices for THIS IPD, with
                         "Open" into the editor.

  Reads only (this view does not write the IPD itself — edits go through the
  generic DocDetail at /web/item-production-detail/:id in edit mode is NOT wired
  here; this is the rich config surface). Loads via getDoc (frappe.client.get)
  so child arrays (item_bom, ipd_processes) come back inline.

  The "Configure combinations" redirect mirrors the Desk's 3-doctype split:
  yrp ships no auto-redirect, so we synthesize it (RICH_FLOWS_PLAN.md). We look
  for an existing matrix for {ipd, process_name}; found → open it; else → create
  route (`/ipd-process-matrix/new?ipd=&process=`) where the editor seeds via
  generate_cross_product.
-->
<template>
	<div class="ipd-config">
		<!-- Breadcrumb -->
		<nav class="crumbs">
			<a @click="goHome">Home</a>
			<span class="sep">/</span>
			<a @click="goList">Item Production Detail</a>
			<span class="sep">/</span>
			<span class="crumb-cur mgk-mono">{{ id }}</span>
		</nav>

		<!-- Header -->
		<div class="detail-head">
			<div class="id-block">
				<div class="doc-id mgk-mono">{{ id }}</div>
				<div v-if="headerLine" class="doc-title">{{ headerLine }}</div>
			</div>
			<Tag
				v-if="doc"
				class="head-status"
				:value="doc.approval_status || 'Draft'"
				:severity="approvalSeverity"
				rounded
			/>
			<div class="head-actions">
				<Button
					label="Edit fields"
					icon="pi pi-pencil"
					size="small"
					severity="secondary"
					outlined
					@click="openGenericEdit"
				/>
				<a class="desk-link" :href="deskUrl" target="_blank" rel="noopener">
					<i class="pi pi-external-link" /> Open in Desk
				</a>
			</div>
		</div>

		<!-- Loading -->
		<div v-if="loading" class="state-block">
			<i class="pi pi-spin pi-spinner" style="font-size: 1.5rem" />
			<span>Loading…</span>
		</div>

		<!-- Error -->
		<Message v-else-if="error && !doc" severity="error" :closable="false">
			{{ error }}
		</Message>

		<template v-else-if="doc">
			<!-- Attribute summary strip -->
			<div class="attr-strip">
				<div class="attr-cell">
					<span class="al">Item</span>
					<a class="av mgk-mono" @click="navigateDoc('Item', doc.item)">{{ doc.item || "—" }}</a>
				</div>
				<div class="attr-cell">
					<span class="al">Primary Attribute</span>
					<span class="av">{{ doc.primary_item_attribute || "—" }}</span>
				</div>
				<div class="attr-cell">
					<span class="al">Dependent Attribute</span>
					<span class="av">
						{{ doc.dependent_attribute || "—" }}
						<i
							v-if="doc.dependent_attribute"
							class="pi pi-info-circle dep-hint"
							v-tooltip.bottom="'Stamped onto matrix combinations by the engine from each process in/out stage — it is intentionally NOT an editable matrix column.'"
						/>
					</span>
				</div>
			</div>

			<!-- ── Item BOM ── -->
			<section class="panel">
				<div class="panel-head">
					<h3>Item BOM</h3>
					<span class="panel-meta">{{ (doc.item_bom || []).length }} row(s)</span>
				</div>
				<DataTable :value="doc.item_bom || []" class="mgk-table cfg-dt" :rowHover="false" dataKey="name">
					<Column field="item" header="Item">
						<template #body="{ data }">
							<a class="cell-link mgk-mono" @click="navigateDoc('Item', data.item)">{{ data.item || "—" }}</a>
						</template>
					</Column>
					<Column field="qty_of_product" header="Qty of Product">
						<template #body="{ data }">{{ fmtNum(data.qty_of_product) }}</template>
					</Column>
					<Column field="qty_of_bom_item" header="Qty of BOM Item">
						<template #body="{ data }">{{ fmtNum(data.qty_of_bom_item) }}</template>
					</Column>
					<Column field="uom" header="UOM">
						<template #body="{ data }">{{ data.uom || "—" }}</template>
					</Column>
					<Column field="process_name" header="Process">
						<template #body="{ data }">{{ data.process_name || "—" }}</template>
					</Column>
					<Column header="Mapping">
						<template #body="{ data }">
							<Tag
								v-if="data.based_on_attribute_mapping"
								value="Attribute-mapped"
								severity="info"
								icon="pi pi-sitemap"
								rounded
							/>
							<span v-else class="muted-dash">Flat qty</span>
						</template>
					</Column>
					<Column header="" :style="{ width: '150px' }">
						<template #body="{ data }">
							<Button
								v-if="data.based_on_attribute_mapping"
								label="Open mapping"
								icon="pi pi-arrow-up-right"
								size="small"
								text
								:disabled="!data.attribute_mapping"
								v-tooltip.left="data.attribute_mapping ? '' : 'No mapping document linked yet'"
								@click="openMapping(data)"
							/>
						</template>
					</Column>
					<template #empty>
						<div class="table-empty">No BOM rows.</div>
					</template>
				</DataTable>
			</section>

			<!-- ── IPD Processes ── -->
			<section class="panel">
				<div class="panel-head">
					<h3>IPD Processes</h3>
					<span class="panel-meta">{{ (doc.ipd_processes || []).length }} process(es)</span>
				</div>
				<DataTable :value="doc.ipd_processes || []" class="mgk-table cfg-dt" :rowHover="false" dataKey="name">
					<Column field="process_name" header="Process">
						<template #body="{ data }">
							<span class="strong">{{ data.process_name || "—" }}</span>
						</template>
					</Column>
					<Column field="in_stage" header="In Stage">
						<template #body="{ data }">{{ data.in_stage || "—" }}</template>
					</Column>
					<Column field="out_stage" header="Out Stage">
						<template #body="{ data }">{{ data.out_stage || "—" }}</template>
					</Column>
					<Column header="" :style="{ width: '230px' }">
						<template #body="{ data }">
							<Button
								label="Configure combinations"
								icon="pi pi-sliders-h"
								size="small"
								:loading="configuring === data.process_name"
								:disabled="!data.process_name || !!configuring"
								@click="configureCombinations(data)"
							/>
						</template>
					</Column>
					<template #empty>
						<div class="table-empty">No processes defined.</div>
					</template>
				</DataTable>
			</section>

			<!-- ── Process Matrices ── -->
			<section class="panel">
				<div class="panel-head">
					<h3>Process Matrices</h3>
					<span class="panel-meta">
						<i v-if="matricesLoading" class="pi pi-spin pi-spinner" />
						<template v-else>{{ matrices.length }} matri{{ matrices.length === 1 ? "x" : "ces" }}</template>
					</span>
				</div>
				<DataTable :value="matrices" class="mgk-table cfg-dt" :rowHover="false" dataKey="name" :loading="matricesLoading">
					<Column field="name" header="Matrix">
						<template #body="{ data }"><span class="mgk-mono">{{ data.name }}</span></template>
					</Column>
					<Column field="process_name" header="Process">
						<template #body="{ data }">{{ data.process_name || "—" }}</template>
					</Column>
					<Column field="reference_item_variant" header="Reference Variant">
						<template #body="{ data }">
							<span class="mgk-mono" v-if="data.reference_item_variant">{{ data.reference_item_variant }}</span>
							<span v-else class="muted-dash">Generic</span>
						</template>
					</Column>
					<Column header="" :style="{ width: '110px' }">
						<template #body="{ data }">
							<Button label="Open" icon="pi pi-arrow-right" iconPos="right" size="small" text @click="openMatrix(data.name)" />
						</template>
					</Column>
					<template #empty>
						<div class="table-empty">No process matrices for this IPD yet. Use “Configure combinations” above.</div>
					</template>
				</DataTable>
			</section>
		</template>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { useRouter } from "vue-router"
import DataTable from "primevue/datatable"
import Column from "primevue/column"
import Button from "primevue/button"
import Tag from "primevue/tag"
import Message from "primevue/message"
import Tooltip from "primevue/tooltip"
import { getDoc, getList } from "@/api/client"
import { useAppToast } from "@/composables/useToast"
import { getRegistryByDoctype } from "@/config/doctypes"

// Local directive registration (components import their own deps in this app).
const vTooltip = Tooltip

const props = defineProps({
	id: { type: String, required: true },
})

const router = useRouter()
const toast = useAppToast()

const doc = ref(null)
const loading = ref(false)
const error = ref(null)
const matrices = ref([])
const matricesLoading = ref(false)
const configuring = ref(null) // process_name currently resolving its redirect

const headerLine = computed(() => {
	const d = doc.value
	if (!d) return ""
	const bits = []
	if (d.item) bits.push(d.item)
	if (d.tech_pack_version) bits.push("Tech " + d.tech_pack_version)
	if (d.pattern_version) bits.push("Pattern " + d.pattern_version)
	return bits.join(" · ")
})

const approvalSeverity = computed(() => {
	const s = doc.value?.approval_status
	if (s === "Approved") return "success"
	if (s === "Cutting Approved") return "info"
	return "warn"
})

const deskUrl = computed(
	() => `/app/item-production-detail/${encodeURIComponent(props.id)}`,
)

async function load() {
	// This rich view configures an EXISTING IPD. Creating a new IPD is a heavy
	// master-data task (item attributes, dependent-attribute mapping, BOM) that
	// the generic /web form doesn't model — our explicit route also captures
	// `/item-production-detail/new`, so send that to the Desk new-form rather
	// than 404-ing on getDoc("…", "new").
	if (props.id === "new") {
		window.location.href = "/app/item-production-detail/new"
		return
	}
	loading.value = true
	error.value = null
	try {
		doc.value = await getDoc("Item Production Detail", props.id)
		loadMatrices()
	} catch (e) {
		error.value = e.message || "Failed to load Item Production Detail"
	} finally {
		loading.value = false
	}
}

async function loadMatrices() {
	matricesLoading.value = true
	try {
		const { data } = await getList("IPD Process Matrix", {
			filters: { ipd: props.id },
			fields: ["name", "process_name", "reference_item_variant"],
			order_by: "process_name asc, modified desc",
			limit_page_length: 0,
		})
		matrices.value = data
	} catch (e) {
		matrices.value = []
		toast.warn("Matrices", e.message)
	} finally {
		matricesLoading.value = false
	}
}

onMounted(load)

// ── Item BOM mapping link (R1b target) ──
function openMapping(row) {
	if (!row.attribute_mapping) return
	router.push(
		`/item-bom-attribute-mapping/${encodeURIComponent(row.attribute_mapping)}`,
	)
}

// ── The synthesized "Configure combinations" redirect ──
async function configureCombinations(proc) {
	const process = proc.process_name
	if (!process) return
	configuring.value = process
	try {
		// Find an existing matrix for {ipd, process}. Prefer a generic one (no
		// reference variant), but any existing matrix is a valid landing spot.
		const { data } = await getList("IPD Process Matrix", {
			filters: { ipd: props.id, process_name: process },
			fields: ["name", "reference_item_variant"],
			order_by: "reference_item_variant asc, modified desc",
			limit_page_length: 1,
		})
		if (data.length) {
			router.push(`/ipd-process-matrix/${encodeURIComponent(data[0].name)}`)
		} else {
			router.push(
				`/ipd-process-matrix/new?ipd=${encodeURIComponent(props.id)}&process=${encodeURIComponent(process)}`,
			)
		}
	} catch (e) {
		toast.error("Could not open combinations", e.message)
	} finally {
		configuring.value = null
	}
}

function openMatrix(name) {
	router.push(`/ipd-process-matrix/${encodeURIComponent(name)}`)
}

// ── Navigation helpers ──
function goHome() {
	router.push("/home")
}
function goList() {
	router.push("/item-production-detail")
}
function openGenericEdit() {
	// This rich view OWNS /item-production-detail/:id, so we can't delegate field
	// editing to the generic DocDetail (same path → re-enters this component).
	// Full field/child editing of the IPD itself happens in the Desk form; the
	// rich config flow (combinations / mappings) lives here.
	window.open(deskUrl.value, "_blank")
}
function navigateDoc(dt, name) {
	if (!name) return
	const reg = getRegistryByDoctype(dt)
	if (reg) {
		router.push(`/${reg.route}/${encodeURIComponent(name)}`)
	} else {
		const slug = dt.toLowerCase().replace(/ /g, "-")
		window.open(`/app/${encodeURIComponent(slug)}/${encodeURIComponent(name)}`, "_blank")
	}
}

// ── formatting ──
function fmtNum(v) {
	if (v === null || v === undefined || v === "") return "—"
	const n = Number(v)
	return Number.isNaN(n) ? String(v) : n.toLocaleString("en-IN")
}
</script>

<style scoped>
.ipd-config {
	display: flex;
	flex-direction: column;
	gap: 14px;
}

/* Breadcrumb (mirrors DocDetail) */
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

/* Header */
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

/* States */
.state-block {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 10px;
	padding: 40px 0;
	color: var(--mgk-muted);
}

/* Attribute strip */
.attr-strip {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 1px;
	background: var(--mgk-line);
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius);
	overflow: hidden;
}
@media (max-width: 700px) {
	.attr-strip {
		grid-template-columns: 1fr;
	}
}
.attr-cell {
	background: var(--mgk-card);
	padding: 11px 16px;
	display: flex;
	flex-direction: column;
	gap: 3px;
}
.attr-cell .al {
	font-size: 11.5px;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--mgk-muted);
	font-weight: 600;
}
.attr-cell .av {
	font-size: 14px;
	color: var(--mgk-ink);
	display: inline-flex;
	align-items: center;
	gap: 6px;
}
a.av {
	color: var(--mgk-accent-700);
	cursor: pointer;
}
a.av:hover {
	text-decoration: underline;
}
.dep-hint {
	color: var(--mgk-muted-2);
	font-size: 13px;
	cursor: help;
}

/* Panels */
.panel {
	background: var(--mgk-card);
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius);
	overflow: hidden;
}
.panel-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 12px 16px;
	border-bottom: 1px solid var(--mgk-line);
	background: var(--mgk-slate-50);
}
.panel-head h3 {
	margin: 0;
	font-size: 14px;
	font-weight: 600;
	color: var(--mgk-ink);
}
.panel-meta {
	font-size: 12px;
	color: var(--mgk-muted);
}

/* Tables */
.cfg-dt {
	border: 0;
}
.cell-link {
	color: var(--mgk-accent-700);
	cursor: pointer;
}
.cell-link:hover {
	text-decoration: underline;
}
.strong {
	font-weight: 600;
	color: var(--mgk-ink);
}
.muted-dash {
	color: var(--mgk-muted-2);
	font-size: 12.5px;
}
.table-empty {
	text-align: center;
	padding: 22px 0;
	color: var(--mgk-muted);
	font-size: 13px;
}
:deep(.mgk-table .p-datatable-thead > tr > th) {
	background: var(--mgk-card);
	font-size: 11.5px;
	letter-spacing: 0.03em;
	text-transform: uppercase;
	color: var(--mgk-muted);
}
:deep(.mgk-table .p-datatable-tbody > tr > td) {
	font-size: 13px;
}
</style>
