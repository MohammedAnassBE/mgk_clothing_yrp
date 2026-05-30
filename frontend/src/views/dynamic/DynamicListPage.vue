<template>
	<div class="list-page">
		<!-- Header -->
		<div class="page-head">
			<div>
				<h1 class="page-title">{{ registry?.label || docRoute }}</h1>
				<p v-if="!doctype" class="page-sub">unknown route</p>
			</div>
			<div class="head-actions">
				<IconField v-if="!accessDenied">
					<InputIcon class="pi pi-search" />
					<InputText
						v-model="searchQuery"
						placeholder="Search…"
						@keyup.enter="onSearch"
					/>
				</IconField>
				<Button
					v-if="doctype && !accessDenied && eligibleColumns.length"
					label="Columns"
					icon="pi pi-sliders-h"
					severity="secondary"
					outlined
					size="small"
					@click="showColumnsModal = true"
				/>
				<Button
					v-if="doctype && !accessDenied"
					:label="advFilters.length ? `Filter (${advFilters.length})` : 'Filter'"
					icon="pi pi-filter"
					severity="secondary"
					outlined
					size="small"
					@click="showFilterPanel = true"
				/>
				<Button
					v-if="isAdmin || hasRole('System Manager')"
					label="Open in Desk"
					icon="pi pi-external-link"
					severity="secondary"
					outlined
					size="small"
					@click="openListInDesk"
				/>
				<Button
					v-if="doctype && canCreate(doctype)"
					label="New"
					icon="pi pi-plus"
					size="small"
					@click="onNew"
				/>
			</div>
		</div>

		<!-- Tab strip (meta-derived: status mode / docstatus mode / none — see CUSTOM_UI §6.3) -->
		<Tabs v-if="tabMode" :value="activeTab" @update:value="onTabChange">
			<TabList>
				<Tab
					v-for="t in statusTabs"
					:key="tabValueKey(t.value)"
					:value="tabValueKey(t.value)"
				>
					{{ t.label }}
					<span class="tab-count">{{ t.count }}</span>
				</Tab>
			</TabList>
		</Tabs>

		<!-- Date tabs -->
		<div v-if="dateTabField" class="date-tabs">
			<button
				v-for="t in dateTabOptions"
				:key="t.value"
				class="date-tab"
				:class="{ active: activeDateTab === t.value }"
				@click="onDateTabChange(t.value)"
			>
				{{ t.label }}
			</button>
		</div>

		<!-- Active base filter (implicit URL filter, CUSTOM_UI §6.4). Read-only
		     chip + clear — NOT the deferred interactive Filter popover. -->
		<div v-if="hasBaseFilter" class="base-filter-row">
			<span class="base-filter-chip">
				<i class="pi pi-filter" />
				{{ baseFilterLabel }}
				<button
					class="chip-clear"
					type="button"
					aria-label="Clear filter"
					@click="clearBaseFilter"
				>
					<i class="pi pi-times" />
				</button>
			</span>
		</div>

		<!-- Active interactive filters (Filter popover) — each chip clears one. -->
		<div v-if="filterChips.length" class="adv-filter-row">
			<span v-for="(chip, i) in filterChips" :key="i" class="adv-filter-chip">
				{{ chip }}
				<button class="chip-clear" type="button" aria-label="Remove filter" @click="removeAdvFilter(i)">
					<i class="pi pi-times" />
				</button>
			</span>
			<button class="adv-filter-clear" type="button" @click="clearAdvFilters">Clear all</button>
		</div>

		<!-- Error -->
		<Message v-if="errorMsg" severity="error" :closable="false" class="list-error">
			{{ accessDenied ? `You don’t have access to ${registry?.label || doctype}. Ask an administrator if you need it.` : errorMsg }}
			<template #icon><i class="pi pi-exclamation-triangle" /></template>
		</Message>

		<!-- Table -->
		<DataTable
			:value="rows"
			:loading="loading"
			dataKey="name"
			class="mgk-table"
			:rowHover="true"
			@row-click="onRowClick"
		>
			<Column field="name" header="Name" :sortable="true">
				<template #body="{ data }">
					<span class="mgk-mono">{{ data.name }}</span>
				</template>
			</Column>

			<Column
				v-for="col in listColumns"
				:key="col.field"
				:field="col.field"
				:header="col.label"
				:sortable="true"
			>
				<template #body="{ data }">
					<span v-if="col.type === 'Date'">{{ formatDate(data[col.field]) }}</span>
					<span v-else-if="col.type === 'Datetime'">{{ formatDate(data[col.field]) }}</span>
					<span v-else-if="col.type === 'Currency'">{{ formatNumber(data[col.field]) }}</span>
					<span v-else>{{ data[col.field] ?? "—" }}</span>
				</template>
			</Column>

			<Column v-if="isSubmittable || isWorkflow" header="Status" :style="{ width: '130px' }">
				<template #body="{ data }">
					<Tag
						:value="statusLabel(data)"
						:severity="rowSeverity(data)"
						rounded
					/>
				</template>
			</Column>

			<template #empty>
				<div class="mgk-empty">
					<i class="pi pi-inbox" />
					<p class="mgk-empty__text">No records found</p>
				</div>
			</template>
		</DataTable>

		<!-- Paginator -->
		<Paginator
			v-if="totalCount > pageSize"
			:rows="pageSize"
			:totalRecords="totalCount"
			:first="(page - 1) * pageSize"
			@page="onPage"
		/>

		<ColumnCustomizerModal
			v-model:visible="showColumnsModal"
			:doctype="doctype"
			:columns="modalColumns"
			@saved="onColumnsSaved"
		/>

		<FilterPanel
			v-model:visible="showFilterPanel"
			:doctype="doctype"
			:model-value="advFilters"
			@apply="onApplyFilters"
		/>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, shallowRef, watch } from "vue"
import { useRouter, useRoute } from "vue-router"
import DataTable from "primevue/datatable"
import Column from "primevue/column"
import Button from "primevue/button"
import InputText from "primevue/inputtext"
import IconField from "primevue/iconfield"
import InputIcon from "primevue/inputicon"
import Tabs from "primevue/tabs"
import TabList from "primevue/tablist"
import Tab from "primevue/tab"
import Tag from "primevue/tag"
import Paginator from "primevue/paginator"
import Message from "primevue/message"
import { useDocList } from "@/composables/useDocList"
import { usePermissions } from "@/composables/usePermissions"
import { getRegistryByRoute, WORKFLOW_SEVERITY } from "@/config/doctypes"
import { getMeta, getCount, callMethod } from "@/api/client"
import ColumnCustomizerModal from "@/components/ColumnCustomizerModal.vue"
import FilterPanel from "@/components/FilterPanel.vue"

const props = defineProps({
	docRoute: { type: String, required: true },
})

const router = useRouter()
const route = useRoute()
const { canCreate, isAdmin, hasRole } = usePermissions()

const registry = computed(() => getRegistryByRoute(props.docRoute))
const doctype = computed(() => registry.value?.doctype || "")
const isSubmittable = computed(() => registry.value?.isSubmittable || false)
const isWorkflow = computed(() => registry.value?.isWorkflow || false)
const workflowStates = computed(() => registry.value?.workflowStates || [])
const dateTabField = computed(() => registry.value?.dateTabs || null)

// ── Columns: meta-driven, overlaid with the user's saved per-user choice (#2) ──
// No hardcoded listFields: defaults come from the DocType meta (`in_list_view`),
// the user can pick + reorder via the Customize Columns modal, and the choice is
// stored in the `User Listview` doctype (base yrp).
const NON_LISTABLE = new Set([
	"Table", "Table MultiSelect", "Text Editor", "Long Text", "Small Text", "Text",
	"HTML", "HTML Editor", "Code", "Markdown Editor", "Section Break", "Column Break",
	"Tab Break", "Fold", "Heading", "Button", "Image", "Geolocation", "Signature",
])
const userColumns = ref(null) // saved [{fieldname, enabled, …}] for this user+doctype, or null
const showColumnsModal = ref(false)
const showFilterPanel = ref(false)
const advFilters = ref([]) // active interactive filters (Frappe tuples)
const filterChips = ref([]) // display labels aligned 1:1 with advFilters

function colType(ft) {
	if (ft === "Date") return "Date"
	if (ft === "Datetime") return "Datetime"
	if (ft === "Currency") return "Currency"
	return undefined
}

// Every field a user could pick as a column (from meta, minus name + non-listable).
const eligibleColumns = computed(() => {
	const out = []
	for (const f of meta.value?.fields || []) {
		if (f.fieldname === "name" || f.hidden) continue
		if (NON_LISTABLE.has(f.fieldtype)) continue
		out.push({
			field: f.fieldname,
			label: f.label || f.fieldname,
			type: colType(f.fieldtype),
			fieldtype: f.fieldtype,
			in_list_view: !!f.in_list_view,
		})
	}
	return out
})

// Columns rendered in the table: per-user saved (enabled, in saved order) → meta
// `in_list_view` defaults → none (only the always-present Name column).
const listColumns = computed(() => {
	const byField = new Map(eligibleColumns.value.map((c) => [c.field, c]))
	if (Array.isArray(userColumns.value) && userColumns.value.length) {
		const cols = []
		for (const uc of userColumns.value) {
			if (!uc.enabled || uc.fieldname === "name") continue
			const e = byField.get(uc.fieldname)
			if (e) cols.push(e)
		}
		return cols
	}
	return eligibleColumns.value.filter((c) => c.in_list_view)
})

// Fields offered in the Customize Columns modal: every eligible field, marked
// enabled + ordered per the saved config (else meta `in_list_view` defaults).
const modalColumns = computed(() => {
	const eligible = eligibleColumns.value
	if (Array.isArray(userColumns.value) && userColumns.value.length) {
		const byField = new Map(eligible.map((c) => [c.field, c]))
		const ordered = []
		const seen = new Set()
		for (const uc of userColumns.value) {
			const e = byField.get(uc.fieldname)
			if (!e) continue
			ordered.push({ fieldname: e.field, label: e.label, fieldtype: e.fieldtype, enabled: !!uc.enabled })
			seen.add(e.field)
		}
		for (const e of eligible) {
			if (!seen.has(e.field)) {
				ordered.push({ fieldname: e.field, label: e.label, fieldtype: e.fieldtype, enabled: false })
			}
		}
		return ordered
	}
	return eligible.map((e) => ({ fieldname: e.field, label: e.label, fieldtype: e.fieldtype, enabled: !!e.in_list_view }))
})

async function getUserColumns(dt) {
	try {
		const r = await callMethod(
			"yrp.yrp.doctype.user_listview.user_listview.get_user_listview",
			{ doctype_name: dt },
		)
		return Array.isArray(r) ? r : null
	} catch (_) {
		return null
	}
}

// After the user saves/reset columns: reload the saved config and re-create the
// list query (fields changed) while preserving the active tab/date/search filters.
async function onColumnsSaved() {
	showColumnsModal.value = false
	const dt = doctype.value
	if (!dt || !listState.value) return
	userColumns.value = await getUserColumns(dt)
	const prev = listState.value
	const next = useDocList(dt, {
		fields: fetchFields.value,
		defaultFilters: { ...prev.filters },
		orderBy: prev.currentOrderBy.value,
		pageSize,
		immediate: false,
	})
	if (prev.orFilters.value) next.setOrFilters(prev.orFilters.value)
	next.page.value = prev.page.value
	listState.value = next
	next.fetch()
}

const fetchFields = computed(() => {
	const fields = ["name"]
	for (const c of listColumns.value) {
		if (!fields.includes(c.field)) fields.push(c.field)
	}
	if (isSubmittable.value && !fields.includes("docstatus")) fields.push("docstatus")
	if (isWorkflow.value && !fields.includes("workflow_state")) fields.push("workflow_state")
	return fields
})

const searchableFields = computed(() => {
	// name + any non-date column is a reasonable search target
	const f = ["name"]
	for (const c of listColumns.value) {
		if (c.type !== "Date" && c.type !== "Datetime" && c.type !== "Currency") {
			f.push(c.field)
		}
	}
	return f
})

// ── Route-query base filter (CUSTOM_UI §6.4 — implicit filter via URL) ──
// Queue cards / cross-doc links deep-link here with `?filters=<json>` where the
// JSON is an array of [field, op, value] triples. We parse it into a base
// filter that ANDs with EVERYTHING: it seeds the row query (via the list's
// defaultFilters) and is folded into baseFilters() so the per-tab counts also
// reflect the deep-linked context. It composes with — never replaces — the
// date-tab and status/docstatus-tab logic below.
//
// `routeBaseFilters` is a {field: value} object ready for getCount / setFilter,
// where value is either a scalar or an [op, value] pair. `routeBaseFields`
// tracks which keys we own so a query change can cleanly retract the old ones.
const routeBaseFilters = ref({})
const routeBaseFields = ref([])
const hasBaseFilter = computed(() => routeBaseFields.value.length > 0)

// Parse route.query.filters (a JSON array of [field, op, value]) into the
// {field: value} object form. Tolerant of junk: anything unparseable yields {}.
function parseRouteFilters() {
	const raw = route.query.filters
	if (!raw || typeof raw !== "string") return {}
	let arr
	try {
		arr = JSON.parse(raw)
	} catch (_) {
		return {}
	}
	if (!Array.isArray(arr)) return {}
	const obj = {}
	for (const t of arr) {
		if (!Array.isArray(t) || t.length < 2) continue
		const [field, op, value] = t
		if (typeof field !== "string" || !field) continue
		// 2-element triple [field, value] means equality; 3-element carries op.
		obj[field] = t.length >= 3 ? [op, value] : op
	}
	return obj
}

// A short, human label for the active base-filter chip. We don't try to render
// every operator — just signal that a context filter is in effect.
const baseFilterLabel = computed(() => {
	const n = routeBaseFields.value.length
	if (n === 0) return ""
	return n === 1 ? "Filtered" : `Filtered (${n})`
})

// ── Tab strip (meta-derived; CUSTOM_UI §6.3) ──
// tabMode is one of: "status", "docstatus", or null (no tab strip).
// statusTabs holds the rendered tabs: [{ label, value, count }]. For status
// mode `value` is the status string (or null for All); for docstatus mode it
// is the docstatus number-as-string ("0"/"1"/"2", or null for All).
const meta = shallowRef(null)            // parent DocType meta (docs[0]), cached per route
const statusOptions = ref([])            // ordered, non-blank Select options of the `status` field
const tabMode = ref(null)
const statusTabs = ref([])
const activeTab = ref("all")
const activeDateTab = ref("all")
const searchQuery = ref("")
// Live-search debounce state (see onSearch + the searchQuery watch below).
let searchTimer = null
let lastSearched = ""
// `?status=<value>` deep-link: a status to preselect once tabs are built.
const pendingStatus = ref(null)

const DOCSTATUS_TABS = [
	{ label: "Draft", value: "0", docstatus: 0 },
	{ label: "Submitted", value: "1", docstatus: 1 },
	{ label: "Cancelled", value: "2", docstatus: 2 },
]

const dateTabOptions = [
	{ label: "Today", value: "today" },
	{ label: "This Week", value: "week" },
	{ label: "This Month", value: "month" },
	{ label: "All", value: "all" },
]

function getDateRange(tab) {
	const now = new Date()
	const fmt = (d) =>
		`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
	if (tab === "today") {
		const t = fmt(now)
		return [t, t]
	}
	if (tab === "week") {
		const day = now.getDay()
		const monday = new Date(now)
		monday.setDate(now.getDate() - ((day + 6) % 7))
		const sunday = new Date(monday)
		sunday.setDate(monday.getDate() + 6)
		return [fmt(monday), fmt(sunday)]
	}
	if (tab === "month") {
		const first = new Date(now.getFullYear(), now.getMonth(), 1)
		const last = new Date(now.getFullYear(), now.getMonth() + 1, 0)
		return [fmt(first), fmt(last)]
	}
	return null
}

const pageSize = 20
const listState = shallowRef(null)

// The implicit base the tab counts are scoped to, as a plain {field: value}
// object suitable for getCount. It folds together (a) the route-query base
// filter — so counts reflect the deep-linked context — and (b) the date-tab
// window. Search (or_filters) is excluded. Tabs add `status`/`docstatus` on top
// of this, so all three compose with AND.
function baseFilters() {
	const f = { ...routeBaseFilters.value }
	if (dateTabField.value) {
		const range = getDateRange(activeDateTab.value)
		if (range) f[dateTabField.value] = ["between", range]
	}
	return f
}

async function initList() {
	if (!doctype.value) {
		listState.value = null
		meta.value = null
		statusOptions.value = []
		tabMode.value = null
		statusTabs.value = []
		userColumns.value = null
		return
	}
	activeTab.value = "all"
	activeDateTab.value = "all"
	searchQuery.value = ""
	lastSearched = ""
	advFilters.value = []
	filterChips.value = []

	// Parse the route-query base filter up front so the very first fetch carries
	// it — seed it as the list's defaultFilters.
	const base = parseRouteFilters()
	routeBaseFilters.value = base
	routeBaseFields.value = Object.keys(base)

	// `?status=<value>` convenience: preselect that status tab once tabs exist.
	pendingStatus.value =
		typeof route.query.status === "string" ? route.query.status : null

	const dt = doctype.value
	// Load meta + the user's saved columns FIRST, so listColumns (and hence
	// fetchFields) is resolved before the row query runs.
	await loadMetaAndColumns(dt)
	if (dt !== doctype.value) return

	listState.value = useDocList(doctype.value, {
		fields: fetchFields.value,
		defaultFilters: base,
		orderBy: "modified desc",
		pageSize,
		immediate: true,
	})
	await loadTabCounts(dt)
}

// Fetch the DocType meta + the user's saved columns, and decide the tab mode.
// Runs BEFORE the row query so listColumns / fetchFields resolve first.
async function loadMetaAndColumns(dt) {
	meta.value = null
	statusOptions.value = []
	tabMode.value = null
	statusTabs.value = []
	userColumns.value = null
	try {
		const [docs, uc] = await Promise.all([getMeta(dt), getUserColumns(dt)])
		// Route changed while awaiting — abandon this stale result.
		if (dt !== doctype.value) return
		const parent = docs?.[0] || null
		meta.value = parent
		userColumns.value = uc
		const statusField = (parent?.fields || []).find(
			(f) => f.fieldname === "status"
		)
		if (isWorkflow.value) {
			// Workflow-managed → workflow_state tabs (Draft / Approval Pending /
			// Approved / Rejected / Expired). docstatus would collapse the three
			// docstatus-0 states (Draft + Approval Pending + Rejected) into one tab.
			tabMode.value = "workflow"
		} else if (isSubmittable.value) {
			// Submittable → docstatus tabs (All/Draft/Submitted/Cancelled). yrp does
			// NOT advance the `status` field on submit (a submitted PO still reads
			// status="Draft"), so docstatus is the trustworthy Draft/Submitted/Cancelled
			// signal and it matches the row's Status tag. (Status-field option tabs are
			// only for non-submittable doctypes — see below.)
			tabMode.value = "docstatus"
		} else if (statusField && statusField.fieldtype === "Select") {
			tabMode.value = "status"
			statusOptions.value = (statusField.options || "")
				.split("\n")
				.map((o) => o.trim())
				.filter((o) => o.length > 0)
		} else {
			// No status field and not submittable → still show a single All tab.
			tabMode.value = "all"
		}
	} catch (_) {
		// Meta failure must not break the list — degrade to workflow/docstatus tabs
		// (both sourced independently of meta) if applicable, else no tab strip.
		if (dt !== doctype.value) return
		tabMode.value = isWorkflow.value ? "workflow" : isSubmittable.value ? "docstatus" : null
	}
}

// Compute per-tab counts (after the list exists) + apply any ?status= deep-link.
async function loadTabCounts(dt) {
	if (!tabMode.value) return
	try {
		await loadCounts()
		if (dt !== doctype.value) return
		applyPendingStatus()
	} catch (_) {
		if (dt !== doctype.value) return
		if (tabMode.value === "docstatus") statusTabs.value = buildDocstatusTabs({})
		else if (tabMode.value === "workflow") statusTabs.value = buildWorkflowTabs(workflowStates.value, [])
		else if (tabMode.value === "all") statusTabs.value = [{ label: "All", value: null, count: 0 }]
		else {
			tabMode.value = null
			statusTabs.value = []
		}
	}
}

function buildDocstatusTabs(counts) {
	const all = DOCSTATUS_TABS.reduce(
		(sum, t) => sum + (counts[t.value] || 0),
		0
	)
	return [
		{ label: "All", value: null, count: all },
		...DOCSTATUS_TABS.map((t) => ({
			label: t.label,
			value: t.value,
			count: counts[t.value] || 0,
		})),
	]
}

// Workflow tabs: All + one per workflow_state (value === the state string).
// `counts` is positional, aligned 1:1 with `states`.
function buildWorkflowTabs(states, counts) {
	const total = counts.reduce((sum, c) => sum + (c || 0), 0)
	const tabs = [{ label: "All", value: null, count: total }]
	states.forEach((s, i) => {
		tabs.push({ label: s, value: s, count: counts[i] || 0 })
	})
	return tabs
}

// Recompute the per-tab counts via parallel getCount calls, scoped to the
// current date-tab filter. Returns nothing; writes statusTabs.
async function loadCounts() {
	const dt = doctype.value
	const base = baseFilters()
	// tab counts reflect the date-tab scope, not the live search (frappe.client.get_count ignores or_filters)

	if (tabMode.value === "status") {
		const opts = statusOptions.value
		const [allCount, ...optCounts] = await Promise.all([
			getCount(dt, { ...base }),
			...opts.map((opt) => getCount(dt, { ...base, status: opt })),
		])
		if (dt !== doctype.value) return
		const tabs = [{ label: "All", value: null, count: allCount }]
		opts.forEach((opt, i) => {
			// Every status option gets a tab (even count 0), in Select-option order.
			tabs.push({ label: opt, value: opt, count: optCounts[i] || 0 })
		})
		statusTabs.value = tabs
	} else if (tabMode.value === "docstatus") {
		const [d0, d1, d2] = await Promise.all([
			getCount(dt, { ...base, docstatus: 0 }),
			getCount(dt, { ...base, docstatus: 1 }),
			getCount(dt, { ...base, docstatus: 2 }),
		])
		if (dt !== doctype.value) return
		statusTabs.value = buildDocstatusTabs({
			0: d0 || 0,
			1: d1 || 0,
			2: d2 || 0,
		})
	} else if (tabMode.value === "workflow") {
		const states = workflowStates.value
		const counts = await Promise.all(
			states.map((s) => getCount(dt, { ...base, workflow_state: s })),
		)
		if (dt !== doctype.value) return
		statusTabs.value = buildWorkflowTabs(states, counts)
	} else if (tabMode.value === "all") {
		const c = await getCount(dt, { ...base })
		if (dt !== doctype.value) return
		statusTabs.value = [{ label: "All", value: null, count: c || 0 }]
	}
	// If the active tab no longer exists (its count hit 0), fall back to All.
	if (!statusTabs.value.some((t) => tabValueKey(t.value) === activeTab.value)) {
		activeTab.value = "all"
	}
}

// PrimeVue Tab `value` must be a stable primitive; null (the All tab) maps to
// the literal "all" so the active-tab binding round-trips cleanly.
function tabValueKey(value) {
	return value === null ? "all" : String(value)
}

// Apply a `?status=<value>` deep-link by selecting that status tab, but only in
// status mode and only if the value is a real, present status tab. Consumes the
// pending value either way so it fires at most once per load.
function applyPendingStatus() {
	const want = pendingStatus.value
	pendingStatus.value = null
	if (!want || tabMode.value !== "status" || !listState.value) return
	const tab = statusTabs.value.find((t) => t.value === want)
	if (!tab) return
	activeTab.value = tabValueKey(want)
	listState.value.setFilter("status", want)
	listState.value.fetch()
}

watch(() => props.docRoute, () => initList(), { immediate: true })

// Same-path query changes (e.g. one queue card → another, both on /work-order)
// do NOT remount the component or fire the docRoute watch, so re-apply the
// base filter here: retract the old route-base fields from the row query, fold
// the new ones in, recompute the tab counts (baseFilters() reads the new base),
// then refetch. Tabs/date-tabs that the user had picked are preserved.
watch(
	() => [route.query.filters, route.query.status],
	() => {
		if (!doctype.value || !listState.value) return
		const next = parseRouteFilters()
		// Drop the previous route-base fields we own, unless the new base also
		// sets them (setFilter will overwrite those below).
		for (const field of routeBaseFields.value) {
			if (!(field in next)) listState.value.removeFilter(field)
		}
		routeBaseFilters.value = next
		routeBaseFields.value = Object.keys(next)
		for (const [field, value] of Object.entries(next)) {
			listState.value.setFilter(field, value)
		}
		// Honor a same-path `?status=` change too (it re-selects the status tab).
		pendingStatus.value =
			typeof route.query.status === "string" ? route.query.status : null
		// Recompute counts against the new base, then refetch rows. If the active
		// tab's count drops to 0, loadCounts() falls the selection back to All;
		// mirror that into the row filter (same as onDateTabChange) before fetch.
		const apply = async () => {
			const prevActive = activeTab.value
			if (tabMode.value) await loadCounts()
			if (!listState.value) return
			if (tabMode.value && prevActive !== "all" && activeTab.value === "all") {
				// Fall back to the route-query base value (not nothing) so a base
				// constraint on status/docstatus is preserved.
				if (tabMode.value === "status") listState.value.setFilter("status", routeBaseFilters.value?.status ?? null)
				else if (tabMode.value === "workflow") listState.value.setFilter("workflow_state", routeBaseFilters.value?.workflow_state ?? null)
				else listState.value.setFilter("docstatus", routeBaseFilters.value?.docstatus ?? null)
			}
			applyPendingStatus()
			listState.value.fetch()
		}
		apply()
	}
)

const rows = computed(() => listState.value?.data.value || [])
const errorMsg = computed(() => listState.value?.error.value || null)
// U6: detect a permission/access error → show friendly copy + hide the (useless)
// search/Columns/Filter toolbar on a denied list.
const accessDenied = computed(() => {
	const m = String(errorMsg.value || "")
	return /insufficient permission|do not have|does not have|not permitted/i.test(m)
})
const totalCount = computed(() => {
	const c = listState.value?.totalCount.value
	return typeof c === "number" ? c : 0
})
const loading = computed(() => listState.value?.loading.value || false)
const page = computed(() => listState.value?.page.value || 1)

// key is the PrimeVue Tab value ("all" for the All tab, else the status string
// or docstatus number-string). Resolve it back to the real tab descriptor and
// apply the matching row filter.
function onTabChange(key) {
	activeTab.value = key
	if (!listState.value) return
	const tab = statusTabs.value.find((t) => tabValueKey(t.value) === key)
	const value = tab ? tab.value : null
	if (tabMode.value === "status") {
		// Clearing to All (value === null) restores the route-query base constraint
		// on `status` (if any) rather than deleting it — so a deep-link like
		// status:["not in",[...]] survives, keeping the chip truthful.
		listState.value.setFilter("status", value === null ? (routeBaseFilters.value?.status ?? null) : value)
	} else if (tabMode.value === "docstatus") {
		listState.value.setFilter("docstatus", value === null ? (routeBaseFilters.value?.docstatus ?? null) : Number(value))
	} else if (tabMode.value === "workflow") {
		listState.value.setFilter("workflow_state", value === null ? (routeBaseFilters.value?.workflow_state ?? null) : value)
	}
	listState.value.fetch()
}

async function onDateTabChange(value) {
	activeDateTab.value = value
	if (!listState.value) return
	if (dateTabField.value) {
		const range = getDateRange(value)
		if (range) {
			listState.value.setFilter(dateTabField.value, ["between", range])
		} else {
			listState.value.setFilter(dateTabField.value, null)
		}
	}
	// Recompute per-tab counts for the new date window. If the active tab's
	// count drops to 0, loadCounts() falls the selection back to All; mirror
	// that into the row filter before fetching.
	const prevActive = activeTab.value
	if (tabMode.value) await loadCounts()
	if (tabMode.value && prevActive !== "all" && activeTab.value === "all") {
		// Fall back to the route-query base value (not nothing) so a base
		// constraint on status/docstatus/workflow_state is preserved.
		if (tabMode.value === "status") listState.value.setFilter("status", routeBaseFilters.value?.status ?? null)
		else if (tabMode.value === "workflow") listState.value.setFilter("workflow_state", routeBaseFilters.value?.workflow_state ?? null)
		else listState.value.setFilter("docstatus", routeBaseFilters.value?.docstatus ?? null)
	}
	listState.value.fetch()
}

function onSearch() {
	if (searchTimer) {
		clearTimeout(searchTimer)
		searchTimer = null
	}
	if (!listState.value) return
	const q = searchQuery.value.trim()
	if (q === lastSearched) return // unchanged → skip a redundant fetch
	lastSearched = q
	if (q) {
		listState.value.setOrFilters(
			searchableFields.value.map((f) => [f, "like", `%${q}%`])
		)
	} else {
		listState.value.clearOrFilters()
	}
	listState.value.fetch()
}

// Live search: debounce keystrokes (300ms) so the list filters as you type.
// Enter (@keyup.enter) still fires onSearch immediately and cancels the pending
// debounce; a programmatic reset that doesn't change the query is skipped.
watch(searchQuery, () => {
	if (searchTimer) clearTimeout(searchTimer)
	searchTimer = setTimeout(() => {
		searchTimer = null
		onSearch()
	}, 300)
})

onBeforeUnmount(() => {
	if (searchTimer) clearTimeout(searchTimer)
})

// ── Interactive filter popover (FilterPanel) ──────────────────────────────
// FilterPanel emits the active filters as Frappe tuples + 1:1 display labels.
// We push the tuples into listState.advancedFilters and refetch; chips mirror
// the labels so each can be cleared individually.
function applyAdvFilters() {
	if (!listState.value) return
	listState.value.setAdvancedFilters(advFilters.value)
	listState.value.fetch()
}
function onApplyFilters(tuples, labels) {
	advFilters.value = tuples
	filterChips.value = labels
	applyAdvFilters()
}
function removeAdvFilter(i) {
	advFilters.value.splice(i, 1)
	filterChips.value.splice(i, 1)
	applyAdvFilters()
}
function clearAdvFilters() {
	advFilters.value = []
	filterChips.value = []
	applyAdvFilters()
}

function onPage(e) {
	if (listState.value) listState.value.setPage(e.page + 1)
}

function onRowClick(e) {
	const name = e?.data?.name
	if (name) router.push(`/${props.docRoute}/${encodeURIComponent(name)}`)
}

function onNew() {
	router.push(`/${props.docRoute}/new`)
}

// Clear the implicit base filter by navigating to the same list route with no
// query. The query watcher above retracts the base-filter fields and refetches.
function clearBaseFilter() {
	router.push(`/${props.docRoute}`)
}

function openListInDesk() {
	if (doctype.value) {
		window.open(`/app/${encodeURIComponent(doctype.value.toLowerCase().replace(/ /g, "-"))}`, "_blank")
	}
}

// ── formatting + status helpers ──
function formatDate(val) {
	if (!val) return "—"
	const datePart = String(val).split(" ")[0]
	const [y, m, d] = datePart.split("-")
	return y && m && d ? `${d}-${m}-${y}` : val
}

function formatNumber(val) {
	if (val === null || val === undefined || val === "") return "—"
	const n = Number(val)
	return Number.isNaN(n) ? val : n.toLocaleString("en-IN")
}

const DOCSTATUS_LABELS = { 0: "Draft", 1: "Submitted", 2: "Cancelled" }
function statusLabel(row) {
	if (isWorkflow.value && row.workflow_state) return row.workflow_state
	return row.status || DOCSTATUS_LABELS[row.docstatus] || "—"
}
function statusSeverity(ds) {
	if (ds === 1) return "success"
	if (ds === 2) return "danger"
	return "warn"
}
// Row-aware severity: workflow_state for workflow doctypes, else docstatus.
function rowSeverity(row) {
	if (isWorkflow.value && row.workflow_state) return WORKFLOW_SEVERITY[row.workflow_state] || "warn"
	return statusSeverity(row.docstatus)
}
</script>

<style scoped>
.list-page {
	display: flex;
	flex-direction: column;
	gap: 14px;
}

.page-head {
	display: flex;
	align-items: flex-start;
	gap: 16px;
}

.page-title {
	font-size: 24px;
	font-weight: 600;
	letter-spacing: -0.01em;
	margin: 0 0 var(--space-3);
	color: var(--mgk-ink);
}

.page-sub {
	font-size: 12.5px;
	color: var(--mgk-muted);
	margin: 2px 0 0;
}

.head-actions {
	margin-left: auto;
	display: flex;
	gap: 8px;
	align-items: center;
}

.date-tabs {
	display: flex;
	gap: 4px;
}

.date-tab {
	font-size: 12px;
	min-height: 32px;
	padding: 6px 12px;
	border-radius: 999px;
	color: var(--mgk-muted);
	cursor: pointer;
	border: 1px solid transparent;
	background: transparent;
}

.date-tab.active {
	color: var(--mgk-accent-700);
	background: var(--mgk-accent-50);
	border-color: var(--mgk-accent);
	font-weight: 600;
}

/* Per-tab count badge on the status/docstatus tab strip (slate by default,
   emerald accent on the active tab — consistent with the design tokens). */
.tab-count {
	margin-left: 6px;
	background: var(--mgk-slate-50);
	color: var(--mgk-muted);
	font-size: 11px;
	font-weight: 600;
	line-height: 1.4;
	padding: 1px 7px;
	border-radius: 999px;
}

:deep(.p-tab-active) .tab-count {
	background: var(--mgk-accent-50);
	color: var(--mgk-accent-700);
}

.mgk-table {
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius);
	overflow: hidden;
	background: var(--mgk-card);
}

:deep(.mgk-table .p-datatable-tbody > tr) {
	cursor: pointer;
}

/* Taller rows (~40px) for a comfortable touch target. */
:deep(.mgk-table .p-datatable-tbody > tr > td) {
	padding-top: 11px;
	padding-bottom: 11px;
	font-size: 13px;
}

.list-error {
	margin: 0;
}

/* Active base-filter chip (implicit URL filter). Slate pill + a clear ✕. */
.base-filter-row {
	display: flex;
}

.base-filter-chip {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	background: var(--mgk-slate-50);
	border: 1px solid var(--mgk-line);
	border-radius: 999px;
	padding: 3px 6px 3px 12px;
	font-size: 12px;
	font-weight: 600;
	color: var(--mgk-ink-2);
}

.base-filter-chip > i {
	font-size: 11px;
	color: var(--mgk-muted);
}

/* Interactive filter chips (Filter popover) — reuse .chip-clear for the ✕. */
.adv-filter-row {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	align-items: center;
	margin-top: 8px;
}

.adv-filter-chip {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	background: var(--mgk-slate-50);
	border: 1px solid var(--mgk-line);
	border-radius: 999px;
	padding: 3px 6px 3px 12px;
	font-size: 12px;
	font-weight: 600;
	color: var(--mgk-ink-2);
}

.adv-filter-clear {
	border: none;
	background: transparent;
	color: var(--mgk-accent-700);
	font-size: 12px;
	font-weight: 600;
	cursor: pointer;
	padding: 3px 8px;
}

.adv-filter-clear:hover {
	text-decoration: underline;
}

.chip-clear {
	display: grid;
	place-items: center;
	width: 18px;
	height: 18px;
	border: none;
	border-radius: 999px;
	background: transparent;
	color: var(--mgk-muted);
	cursor: pointer;
	transition: background 0.14s, color 0.14s;
}

.chip-clear:hover {
	background: var(--mgk-line);
	color: var(--mgk-ink);
}

.chip-clear i {
	font-size: 10px;
}
</style>
