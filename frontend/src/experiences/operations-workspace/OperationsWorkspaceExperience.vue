<template>
	<div class="ops-shell">
		<header class="ops-topbar">
			<button class="brand" type="button" aria-label="Go to all books" @click="go('/')">
				<span class="brand-mark">MGK</span>
				<span class="brand-copy"><strong>MGK Clothing</strong><small>Operations Workspace</small></span>
			</button>
			<span class="topbar-divider" />
			<div class="topbar-context"><strong>{{ pageTitle }}</strong><span>· Operations workspace</span></div>
			<div class="topbar-actions">
				<span class="live-chip">LIVE VIEW</span>
				<span class="avatar" :title="userName">{{ userInitials }}</span>
				<button class="icon-button" type="button" title="Log out" aria-label="Log out" @click="signOut">
					<i class="pi pi-sign-out" />
				</button>
			</div>
		</header>

		<main class="ops-main">
			<!-- Home: the six familiar digital book groups. -->
			<section v-if="page.kind === 'home'" class="page">
				<div class="home-heading">
					<div>
						<div class="eyebrow">MGK daily work</div>
						<h1>Your Digital Books</h1>
					</div>
					<button v-if="visibleMasters.length" class="button secondary" type="button" @click="go('/manage')">
						<i class="pi pi-sliders-h" /> Manage Masters & Access
					</button>
				</div>

				<div v-if="visibleGroups.length" class="group-grid">
					<button
						v-for="group in visibleGroups"
						:key="group.key"
						class="group-card"
						type="button"
						@click="go(`/group/${group.key}`)"
					>
						<span class="group-card-head">
							<span class="group-code" :class="`cover-${group.cover}`">{{ group.code }}</span>
							<span class="group-copy"><strong>{{ group.label }}</strong><small>{{ group.description }}</small></span>
						</span>
						<span class="book-shelf" aria-hidden="true">
							<span
								v-for="(book, index) in group.books"
								:key="book.key"
								class="mini-book"
								:class="`cover-${group.cover}`"
								:style="{ height: `${58 + (index % 2) * 8}px` }"
							>{{ book.short }}</span>
						</span>
						<span class="group-card-foot">
							<span>{{ countLabel(groupCounts[group.key]) }}</span>
							<strong>Open · {{ group.books.length }} {{ group.books.length === 1 ? 'book' : 'books' }} ›</strong>
						</span>
					</button>
				</div>
				<div v-else class="empty-state"><i class="pi pi-lock" /><h2>No books available</h2><p>Your roles do not currently provide read access to these documents.</p></div>
			</section>

			<!-- One document group and its familiar books. -->
			<section v-else-if="page.kind === 'group' && selectedGroup" class="page">
				<Breadcrumbs :items="[{ label: 'All Books', path: '/' }, { label: selectedGroup.label }]" @navigate="go" />
				<div class="page-heading">
					<span class="book-identity" :class="`cover-${selectedGroup.cover}`">{{ selectedGroup.code }}</span>
					<div class="heading-copy"><div class="eyebrow">Digital books</div><h1>{{ selectedGroup.label }}</h1><p>Choose the familiar working book to view its records.</p></div>
					<button class="button secondary heading-action" type="button" @click="go('/')">← All Books</button>
				</div>
				<div class="book-grid">
					<button v-for="book in selectedGroup.books" :key="book.key" class="book-card" type="button" @click="openBook(selectedGroup, book)">
						<span class="book-cover" :class="`cover-${selectedGroup.cover}`">
							<span class="book-spine" />
							<small>{{ selectedGroup.code }}</small>
							<strong>{{ book.short }}</strong>
						</span>
						<span class="book-meta"><strong>{{ book.label }}</strong><small>{{ book.note }}</small></span>
						<span class="book-open"><span>{{ countLabel(bookCounts[book.key]) }}</span><strong>Open book ›</strong></span>
					</button>
				</div>
			</section>

			<!-- Shared transaction or master list. -->
			<section v-else-if="(page.kind === 'list' && selectedGroup && selectedBook) || (page.kind === 'master-list' && selectedMaster)" class="page">
				<Breadcrumbs :items="listBreadcrumbs" @navigate="go" />
				<div class="page-heading">
					<span class="book-identity" :class="listIdentityClass">{{ listIdentityCode }}</span>
					<div class="heading-copy">
						<div class="eyebrow">{{ page.kind === 'master-list' ? 'Master records' : selectedGroup.label }}</div>
						<h1>{{ listTitle }}</h1>
						<p>{{ listDescription }}</p>
					</div>
					<div class="heading-actions">
						<button class="button secondary" type="button" @click="go(listBackPath)">← {{ page.kind === 'master-list' ? 'Manage' : selectedGroup.label }}</button>
					</div>
				</div>

				<div class="toolbar">
					<label class="search-box"><i class="pi pi-search" /><input v-model.trim="searchText" type="search" placeholder="Search the loaded records…" /></label>
					<div v-if="statusOptions.length > 1" class="status-filters">
						<button v-for="status in statusOptions" :key="status" type="button" :class="{ active: activeStatus === status }" @click="activeStatus = status">{{ status }}</button>
					</div>
					<span class="record-count">{{ filteredRows.length }} shown · {{ listState.total }} total</span>
				</div>

				<div v-if="listState.loading && !listState.rows.length" class="loading-state"><i class="pi pi-spin pi-spinner" /><span>Loading {{ listTitle }}…</span></div>
				<div v-else-if="listState.error" class="error-state" role="alert"><i class="pi pi-exclamation-triangle" /><div><strong>Unable to load records</strong><span>{{ listState.error }}</span></div><button class="button secondary small" type="button" @click="loadList(false)">Retry</button></div>
				<div v-else-if="!filteredRows.length" class="empty-state compact"><i class="pi pi-inbox" /><h2>No records found</h2><p>There are no readable records in this book for the current filters.</p></div>
				<template v-else>
					<div class="list-card desktop-list">
						<table>
							<thead><tr><th v-for="column in currentListConfig.columns" :key="column.label">{{ column.label }}</th><th /></tr></thead>
							<tbody>
								<tr v-for="row in filteredRows" :key="row.name" tabindex="0" @click="openRow(row)" @keydown.enter="openRow(row)">
									<td v-for="(column, index) in currentListConfig.columns" :key="column.label">
										<span v-if="column.type === 'status' || column.type === 'enabled' || column.type === 'user_enabled'" class="status" :class="statusClass(statusForColumn(row, column))">{{ statusForColumn(row, column) }}</span>
										<span v-else :class="{ 'record-id': index === 0 }">{{ displayColumn(row, column) }}</span>
									</td>
									<td class="row-arrow">›</td>
								</tr>
							</tbody>
						</table>
					</div>
					<div class="mobile-list">
						<button v-for="row in filteredRows" :key="row.name" class="mobile-row" type="button" @click="openRow(row)">
							<span class="mobile-row-head"><strong>{{ displayColumn(row, currentListConfig.columns[0]) }}</strong><span class="status" :class="statusClass(rowStatus(row))">{{ rowStatus(row) }}</span></span>
							<span class="mobile-row-grid"><span v-for="column in currentListConfig.columns.slice(1, 5)" :key="column.label"><small>{{ column.label }}</small><strong>{{ displayColumn(row, column) }}</strong></span></span>
						</button>
					</div>
					<div v-if="listState.hasMore" class="load-more"><button class="button secondary" type="button" :disabled="listState.loading" @click="loadList(true)"><i v-if="listState.loading" class="pi pi-spin pi-spinner" /> Load more records</button></div>
				</template>
				<div class="view-note"><strong>Viewing phase:</strong> this screen reads live Frappe data. Create, edit, submit, approve and cancel actions will be added DocType by DocType in the next phase.</div>
			</section>

			<!-- Permission-aware master/access landing. -->
			<section v-else-if="page.kind === 'manage'" class="page">
				<Breadcrumbs :items="[{ label: 'All Books', path: '/' }, { label: 'Manage' }]" @navigate="go" />
				<div class="page-heading">
					<div class="heading-copy"><div class="eyebrow">Masters and access</div><h1>Manage</h1><p>Review the master data required by purchasing, receiving, billing and production.</p></div>
					<button class="button secondary heading-action" type="button" @click="go('/')">← All Books</button>
				</div>
				<div class="manage-grid">
					<button v-for="master in visibleMasters" :key="master.key" class="manage-card" type="button" @click="go(`/manage/${master.key}`)">
						<span class="manage-icon">{{ master.code }}</span>
						<strong>{{ master.label }}</strong>
						<p>{{ master.description }}</p>
						<span class="usage"><small v-for="item in master.usage" :key="item">{{ item }}</small></span>
						<span class="manage-foot"><span>{{ countLabel(masterCounts[master.key]) }}</span><strong>View list ›</strong></span>
					</button>
				</div>
				<div class="view-note"><strong>Permission rule:</strong> cards appear only when the current user can read that DocType. Users & Access is limited to Administrator/System Manager.</div>
			</section>

			<!-- Read-only live detail shared by transactions and masters. -->
			<section v-else-if="(page.kind === 'detail' && selectedGroup) || (page.kind === 'master-detail' && selectedMaster)" class="page">
				<Breadcrumbs :items="detailBreadcrumbs" @navigate="go" />
				<div v-if="detailState.loading" class="loading-state"><i class="pi pi-spin pi-spinner" /><span>Loading record…</span></div>
				<div v-else-if="detailState.error" class="error-state" role="alert"><i class="pi pi-exclamation-triangle" /><div><strong>Unable to load record</strong><span>{{ detailState.error }}</span></div><button class="button secondary small" type="button" @click="loadDetail">Retry</button></div>
				<template v-else-if="detailState.doc">
					<section class="detail-hero">
						<span class="book-identity" :class="detailIdentityClass">{{ detailIdentityCode }}</span>
						<div><div class="detail-id">{{ detailState.doc.name }}</div><h1>{{ detailTitle }}</h1><p>{{ detailSubtitle }}</p></div>
						<span class="status detail-status" :class="statusClass(detailStatus)">{{ detailStatus }}</span>
					</section>

					<section v-if="detailFacts.length" class="fact-grid">
						<div v-for="fact in detailFacts" :key="fact.field" class="fact"><span>{{ fact.label }}</span><strong>{{ fact.value }}</strong></div>
					</section>

					<div class="detail-layout">
						<div>
							<section v-for="section in childSections" :key="section.field" class="section-card">
								<header><h2>{{ section.label }}</h2><span>{{ section.rows.length }} rows</span></header>
								<div class="table-scroll"><table><thead><tr><th v-for="column in section.columns" :key="column">{{ humanize(column) }}</th></tr></thead><tbody><tr v-for="(row, index) in section.rows" :key="row.name || index"><td v-for="column in section.columns" :key="column">{{ displayDetailValue(column, row[column]) }}</td></tr></tbody></table></div>
							</section>
							<section v-if="!childSections.length" class="section-card"><header><h2>Record information</h2></header><div class="section-copy">This document has no visible child rows. Its important fields are shown above.</div></section>
						</div>
						<aside>
							<section v-if="detailAddresses.length" class="section-card"><header><h2>Linked Addresses</h2><span>{{ detailAddresses.length }}</span></header><div class="address-stack"><article v-for="address in detailAddresses" :key="address.name"><strong>{{ address.address_title || address.address_type || 'Address' }}</strong><span>{{ formatAddress(address) }}</span><small v-if="address.phone"><i class="pi pi-phone" /> {{ address.phone }}</small></article></div></section>
							<section class="section-card"><header><h2>Connected records</h2><span>{{ linkedCards.length }}</span></header><div v-if="linkedCards.length" class="linked-stack"><button v-for="card in linkedCards" :key="`${card.doctype}:${card.name}`" type="button" :disabled="!linkedRoute(card)" @click="openLinked(card)"><span>{{ acronym(card.doctype) }}</span><span><strong>{{ card.name }}</strong><small>{{ card.doctype }}</small></span><i class="pi pi-angle-right" /></button></div><div v-else class="section-copy">No connected records were returned for this document.</div></section>
							<button class="button secondary full" type="button" @click="go(detailBackPath)">← Back to {{ detailBackLabel }}</button>
						</aside>
					</div>
					<div class="view-note"><strong>Live read-only view:</strong> this record and its child rows came from Frappe. Data-entry actions are intentionally not part of this phase.</div>
				</template>
			</section>

			<section v-else class="page"><div class="empty-state"><i class="pi pi-compass" /><h2>Page not found</h2><p>Return to the digital books and choose another page.</p><button class="button primary" type="button" @click="go('/')">Go to All Books</button></div></section>
		</main>
	</div>
</template>

<script setup>
import { computed, defineComponent, h, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { getList, getListView, getCount, getDoc, getLinkedDocs, getAddressList } from "@/api/client"
import { logout } from "@/api/auth"
import { usePermissions } from "@/composables/usePermissions"
import {
	TRANSACTION_GROUPS,
	MASTER_GROUPS,
	getTransactionGroup,
	getMasterGroup,
	getBook,
	hasChildTableFilters,
	slugify,
} from "./config"

const PAGE_SIZE = 25
const route = useRoute()
const router = useRouter()
const { canRead, isAdmin, hasRole } = usePermissions()

const Breadcrumbs = defineComponent({
	props: { items: { type: Array, default: () => [] } },
	emits: ["navigate"],
	setup(props, { emit }) {
		return () => h("nav", { class: "breadcrumbs", "aria-label": "Breadcrumb" },
			props.items.flatMap((item, index) => {
				const nodes = []
				if (index) nodes.push(h("span", { class: "breadcrumb-separator" }, "›"))
				nodes.push(item.path
					? h("button", { type: "button", onClick: () => emit("navigate", item.path) }, item.label)
					: h("span", item.label))
				return nodes
			})
		)
	},
})

const page = computed(() => {
	const parts = route.path.split("/").filter(Boolean).map(decodeURIComponent)
	if (!parts.length || parts[0] === "home") return { kind: "home" }
	if (parts[0] === "group" && parts[1]) return { kind: "group", groupKey: parts[1] }
	if (parts[0] === "list" && parts[1] && parts[2]) return { kind: "list", groupKey: parts[1], bookKey: parts[2] }
	if (parts[0] === "detail" && parts[1] && parts[2]) return { kind: "detail", groupKey: parts[1], name: parts.slice(2).join("/") }
	if (parts[0] === "manage" && parts[1]) return { kind: "master-list", masterKey: parts[1] }
	if (parts[0] === "manage") return { kind: "manage" }
	if (parts[0] === "master" && parts[1] && parts[2]) return { kind: "master-detail", masterKey: parts[1], name: parts.slice(2).join("/") }
	return { kind: "not-found" }
})

const selectedGroup = computed(() => getTransactionGroup(page.value.groupKey))
const selectedBook = computed(() => getBook(page.value.groupKey, page.value.bookKey))
const selectedMaster = computed(() => getMasterGroup(page.value.masterKey))
const visibleGroups = computed(() => TRANSACTION_GROUPS.filter((group) => canRead(group.doctype)))
const visibleMasters = computed(() => MASTER_GROUPS.filter((master) =>
	canRead(master.doctype) && (!master.adminOnly || isAdmin.value || hasRole("System Manager"))
))

const groupCounts = reactive({})
const bookCounts = reactive({})
const masterCounts = reactive({})
const listState = reactive({ rows: [], loading: false, error: "", page: 0, total: 0, hasMore: false })
const detailState = reactive({ doc: null, linked: {}, loading: false, error: "" })
const detailAddresses = ref([])
const searchText = ref("")
const activeStatus = ref("All")
let loadSequence = 0

const bootUser = window.frappe?.boot?.user || {}
const userName = computed(() => bootUser.full_name || bootUser.name || "User")
const userInitials = computed(() => userName.value.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "U")

const currentListConfig = computed(() => page.value.kind === "master-list" ? selectedMaster.value : selectedGroup.value)
const listTitle = computed(() => page.value.kind === "master-list" ? selectedMaster.value?.label || "Records" : selectedBook.value?.label || "Records")
const listDescription = computed(() => page.value.kind === "master-list" ? selectedMaster.value?.description || "" : `${selectedBook.value?.note || ""} Select any row to review the complete live document.`)
const listIdentityCode = computed(() => page.value.kind === "master-list" ? selectedMaster.value?.code : selectedGroup.value?.code)
const listIdentityClass = computed(() => page.value.kind === "master-list" ? "master-identity" : `cover-${selectedGroup.value?.cover}`)
const listBackPath = computed(() => page.value.kind === "master-list" ? "/manage" : `/group/${selectedGroup.value?.key}`)
const listBreadcrumbs = computed(() => page.value.kind === "master-list"
	? [{ label: "All Books", path: "/" }, { label: "Manage", path: "/manage" }, { label: selectedMaster.value?.label || "Records" }]
	: [{ label: "All Books", path: "/" }, { label: selectedGroup.value?.label || "Group", path: `/group/${selectedGroup.value?.key}` }, { label: selectedBook.value?.label || "Book" }]
)

const pageTitle = computed(() => {
	if (page.value.kind === "home") return "All Books"
	if (page.value.kind === "manage") return "Manage"
	if (page.value.kind === "group") return selectedGroup.value?.label || "Books"
	if (page.value.kind === "list" || page.value.kind === "master-list") return listTitle.value
	if (page.value.kind === "detail" || page.value.kind === "master-detail") return detailState.doc?.name || "Record"
	return "Operations"
})

const statusOptions = computed(() => {
	const statuses = [...new Set(listState.rows.map(rowStatus).filter(Boolean))]
	return ["All", ...statuses]
})

const filteredRows = computed(() => {
	const query = searchText.value.toLowerCase()
	return listState.rows.filter((row) => {
		const statusMatches = activeStatus.value === "All" || rowStatus(row) === activeStatus.value
		const searchMatches = !query || Object.values(row).some((value) =>
			!value || typeof value === "object" ? false : String(value).toLowerCase().includes(query)
		)
		return statusMatches && searchMatches
	})
})

const detailConfig = computed(() => page.value.kind === "master-detail" ? selectedMaster.value : selectedGroup.value)
const detailStatus = computed(() => rowStatus(detailState.doc || {}))
const detailIdentityCode = computed(() => detailConfig.value?.code || "DOC")
const detailIdentityClass = computed(() => page.value.kind === "master-detail" ? "master-identity" : `cover-${selectedGroup.value?.cover}`)
const detailTitle = computed(() => {
	const doc = detailState.doc || {}
	if (["wo", "ipd", "dc", "grn"].includes(selectedGroup.value?.key) && doc.item) return doc.item
	return doc.supplier_name || doc.name1 || doc.full_name || doc.agent_name || doc.item || doc.supplier || doc.name
})
const detailSubtitle = computed(() => {
	const doc = detailState.doc || {}
	if (doc.process_name) return `${doc.process_name}${doc.supplier ? ` · ${doc.supplier}` : ""}`
	if (doc.supplier && doc.supplier !== detailTitle.value) return doc.supplier
	return detailConfig.value?.doctype || "Document"
})
const detailBackPath = computed(() => page.value.kind === "master-detail"
	? `/manage/${selectedMaster.value?.key}`
	: `/list/${selectedGroup.value?.key}/${route.query.book || selectedGroup.value?.books[0]?.key}`
)
const detailBackLabel = computed(() => page.value.kind === "master-detail" ? selectedMaster.value?.label : (getBook(selectedGroup.value?.key, route.query.book)?.label || selectedGroup.value?.label))
const detailBreadcrumbs = computed(() => page.value.kind === "master-detail"
	? [{ label: "All Books", path: "/" }, { label: "Manage", path: "/manage" }, { label: selectedMaster.value?.label || "Master", path: `/manage/${selectedMaster.value?.key}` }, { label: page.value.name }]
	: [{ label: "All Books", path: "/" }, { label: selectedGroup.value?.label || "Group", path: `/group/${selectedGroup.value?.key}` }, { label: detailBackLabel.value, path: detailBackPath.value }, { label: page.value.name }]
)

const detailFacts = computed(() => {
	const doc = detailState.doc || {}
	const preferred = detailConfig.value?.detailFields || detailConfig.value?.fields || []
	return preferred
		.filter((field) => field !== "name" && doc[field] !== undefined && doc[field] !== null && doc[field] !== "" && !Array.isArray(doc[field]) && typeof doc[field] !== "object")
		.slice(0, 16)
		.map((field) => ({ field, label: humanize(field), value: displayDetailValue(field, doc[field]) }))
})

const childSections = computed(() => {
	const doc = detailState.doc || {}
	return Object.entries(doc)
		.filter(([, value]) => Array.isArray(value) && value.length && typeof value[0] === "object")
		.map(([field, rows]) => {
			const columns = [...new Set(rows.slice(0, 10).flatMap((row) => Object.keys(row)))]
				.filter((key) => !INTERNAL_FIELDS.has(key) && !Array.isArray(rows[0]?.[key]) && typeof rows[0]?.[key] !== "object")
				.slice(0, 8)
			return { field, label: humanize(field), rows, columns }
		})
		.filter((section) => section.columns.length)
		.sort((a, b) => childPriority(a.field) - childPriority(b.field))
})

const linkedCards = computed(() => Object.entries(detailState.linked || {}).flatMap(([doctype, rows]) =>
	(Array.isArray(rows) ? rows : []).slice(0, 20).map((row) => ({ doctype, name: row.name || row }))
))

const INTERNAL_FIELDS = new Set([
	"doctype", "parent", "parentfield", "parenttype", "idx", "docstatus", "owner", "creation",
	"modified", "modified_by", "name", "__islocal", "__unsaved", "_user_tags", "_comments",
	"_assign", "_liked_by", "item_details", "deliverable_details", "receivable_details",
	"table_index", "row_index",
])

watch(() => route.fullPath, async () => {
	searchText.value = ""
	activeStatus.value = "All"
	if (page.value.kind === "home") await loadHomeCounts()
	else if (page.value.kind === "manage") await loadMasterCounts()
	else if (page.value.kind === "group") await loadBookCounts()
	else if (page.value.kind === "list" || page.value.kind === "master-list") await loadList(false)
	else if (page.value.kind === "detail" || page.value.kind === "master-detail") await loadDetail()
}, { immediate: true })

function go(path) {
	router.push(path)
}

function openBook(group, book) {
	go(`/list/${group.key}/${book.key}`)
}

function openRow(row) {
	if (page.value.kind === "master-list") go(`/master/${selectedMaster.value.key}/${encodeURIComponent(row.name)}`)
	else router.push({ path: `/detail/${selectedGroup.value.key}/${encodeURIComponent(row.name)}`, query: { book: selectedBook.value.key } })
}

async function signOut() {
	try { await logout() } catch { window.location.href = "/login" }
}

async function loadHomeCounts() {
	await Promise.all(visibleGroups.value.map(async (group) => {
		try { groupCounts[group.key] = await getCount(group.doctype, {}) }
		catch { groupCounts[group.key] = null }
	}))
}

async function loadMasterCounts() {
	await Promise.all(visibleMasters.value.map(async (master) => {
		try { masterCounts[master.key] = await getCount(master.doctype, {}) }
		catch { masterCounts[master.key] = null }
	}))
}

async function loadBookCounts() {
	if (!selectedGroup.value) return
	for (const key of Object.keys(bookCounts)) delete bookCounts[key]
	await Promise.all(selectedGroup.value.books.map(async (book) => {
		try {
			bookCounts[book.key] = await getCount(
				selectedGroup.value.doctype,
				book.filters?.length ? book.filters : {},
				null,
				hasChildTableFilters(selectedGroup.value.doctype, book.filters),
			)
		} catch { bookCounts[book.key] = null }
	}))
}

async function loadList(append = false) {
	const config = currentListConfig.value
	if (!config) return
	const sequence = ++loadSequence
	if (!append) {
		listState.rows = []
		listState.page = 0
		listState.total = 0
		listState.hasMore = false
	}
	listState.loading = true
	listState.error = ""
	const filters = page.value.kind === "list" ? (selectedBook.value?.filters || []) : []
	const needsDistinct = hasChildTableFilters(config.doctype, filters)
	try {
		const params = {
			fields: config.fields,
			filters: filters.length ? filters : {},
			order_by: "modified desc",
			limit_start: listState.page * PAGE_SIZE,
			limit_page_length: PAGE_SIZE,
		}
		const result = needsDistinct
			? await getListView(config.doctype, params)
			: await getList(config.doctype, params)
		let rows = result.data || []
		if (page.value.kind === "master-list" && config.key === "suppliers") rows = await enrichSuppliers(rows)
		if (page.value.kind === "master-list" && config.key === "warehouses") rows = rows.map((row) => ({ ...row, warehouse_type: row.supplier ? "Supplier Warehouse" : "Company Warehouse" }))
		let total = result.total_count
		try { total = await getCount(config.doctype, filters.length ? filters : {}, null, needsDistinct) }
		catch { total = append ? listState.total : rows.length }
		if (sequence !== loadSequence) return
		listState.rows = append ? [...listState.rows, ...rows] : rows
		listState.page += 1
		listState.total = Number(total ?? listState.rows.length)
		listState.hasMore = listState.rows.length < listState.total && rows.length === PAGE_SIZE
	} catch (error) {
		if (sequence === loadSequence) listState.error = error?.message || "Failed to load records"
	} finally {
		if (sequence === loadSequence) listState.loading = false
	}
}

async function enrichSuppliers(rows) {
	return Promise.all(rows.map(async (row) => {
		try {
			const addresses = await getAddressList("Supplier", row.name)
			const primary = addresses.find((address) => address.is_primary_address) || addresses[0]
			return { ...row, primary_address: primary ? formatAddress(primary) : "—", phone: primary?.phone || "—" }
		} catch { return { ...row, primary_address: "—", phone: "—" } }
	}))
}

async function loadDetail() {
	const config = detailConfig.value
	if (!config || !page.value.name) return
	const sequence = ++loadSequence
	detailState.doc = null
	detailState.linked = {}
	detailState.error = ""
	detailAddresses.value = []
	detailState.loading = true
	try {
		const doc = await getDoc(config.doctype, page.value.name)
		const [linked, addresses] = await Promise.all([
			getLinkedDocs(config.doctype, page.value.name).catch(() => ({})),
			["Supplier", "MGK Agent"].includes(config.doctype)
				? getAddressList(config.doctype, page.value.name).catch(() => [])
				: Promise.resolve([]),
		])
		if (sequence !== loadSequence) return
		detailState.doc = doc
		detailState.linked = linked
		detailAddresses.value = addresses
	} catch (error) {
		if (sequence === loadSequence) detailState.error = error?.message || "Failed to load record"
	} finally {
		if (sequence === loadSequence) detailState.loading = false
	}
}

function getRawValue(row, column) {
	const value = row?.[column.field]
	if ((value === undefined || value === null || value === "") && column.fallback) return row?.[column.fallback]
	return value
}

function displayColumn(row, column) {
	const value = getRawValue(row, column)
	if (column.type === "status" || column.type === "enabled" || column.type === "user_enabled") return statusForColumn(row, column)
	if (column.type === "date" || column.type === "datetime") return formatDate(value, column.type === "datetime")
	if (column.type === "currency") return formatCurrency(value)
	if (column.type === "quantity") return formatQuantity(value)
	return value === undefined || value === null || value === "" ? "—" : String(value)
}

function statusForColumn(row, column) {
	const value = getRawValue(row, column)
	if (column.type === "enabled") return Number(value) ? "Disabled" : "Active"
	if (column.type === "user_enabled") return Number(value) ? "Active" : "Disabled"
	if (column.field === "docstatus") return docstatusLabel(value)
	return value || rowStatus(row)
}

function rowStatus(row = {}) {
	if (row.status) return row.status
	if (row.approval_status) return row.approval_status
	if (row.open_status) return row.open_status
	if (row.enabled !== undefined) return Number(row.enabled) ? "Active" : "Disabled"
	if (row.disabled !== undefined) return Number(row.disabled) ? "Disabled" : "Active"
	return docstatusLabel(row.docstatus)
}

function docstatusLabel(value) {
	if (Number(value) === 1) return "Submitted"
	if (Number(value) === 2) return "Cancelled"
	return "Draft"
}

function statusClass(value) {
	return `status-${slugify(value || "draft")}`
}

function formatDate(value, includeTime = false) {
	if (!value) return "—"
	const parsed = new Date(String(value).replace(" ", "T"))
	if (Number.isNaN(parsed.getTime())) return String(value)
	return new Intl.DateTimeFormat("en-IN", includeTime
		? { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }
		: { day: "2-digit", month: "short", year: "numeric" }
	).format(parsed)
}

function formatCurrency(value) {
	if (value === undefined || value === null || value === "") return "—"
	return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value || 0))
}

function formatQuantity(value) {
	if (value === undefined || value === null || value === "") return "—"
	return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 3 }).format(Number(value || 0))
}

function displayDetailValue(field, value) {
	if (value === undefined || value === null || value === "") return "—"
	if (typeof value === "boolean") return value ? "Yes" : "No"
	if (/date|modified|creation|last_active/.test(field)) return formatDate(value, /time|modified|creation|last_active/.test(field))
	if (/qty|quantity|percentage|percent/.test(field) && typeof value === "number") return formatQuantity(value)
	if (/amount|(^|_)total($|_)|rate|cost|value|charges/.test(field) && typeof value === "number") return formatCurrency(value)
	if (typeof value === "number" && (field.startsWith("is_") || field === "disabled" || field === "enabled")) return value ? "Yes" : "No"
	return String(value)
}

function humanize(value) {
	return String(value || "").replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())
}

function childPriority(field) {
	const order = ["items", "deliverables", "receivables", "grn", "item_bom", "ipd_processes", "mgk_items"]
	const index = order.indexOf(field)
	return index === -1 ? order.length : index
}

function formatAddress(address) {
	return [address.address_line1, address.address_line2, address.city, address.state, address.pincode, address.country].filter(Boolean).join(", ") || address.name || "—"
}

function countLabel(value) {
	if (value === undefined) return "Loading…"
	if (value === null) return "Count unavailable"
	return `${value} ${Number(value) === 1 ? "record" : "records"}`
}

function acronym(value) {
	return String(value || "DOC").split(/\s+/).map((part) => part[0]).join("").slice(0, 4).toUpperCase()
}

function linkedRoute(card) {
	const group = TRANSACTION_GROUPS.find((item) => item.doctype === card.doctype)
	if (group) return `/detail/${group.key}/${encodeURIComponent(card.name)}`
	const master = MASTER_GROUPS.find((item) => item.doctype === card.doctype)
	if (master && canRead(master.doctype)) return `/master/${master.key}/${encodeURIComponent(card.name)}`
	return ""
}

function openLinked(card) {
	const path = linkedRoute(card)
	if (path) go(path)
}
</script>

<style scoped>
.ops-shell {
	--type-page-title: clamp(1.75rem, 2.1vw, 2rem);
	--type-detail-title: clamp(1.5rem, 1.8vw, 1.75rem);
	--type-section-title: 1.375rem;
	--type-card-title: 1.125rem;
	--type-body: .875rem;
	--type-label: .75rem;
	--type-caption: .75rem;
	--color-text: #172033;
	--color-muted: #5f6878;
	min-height: 100vh;
	background: #f7f5f0;
	color: var(--color-text);
	font-size: 1rem;
	line-height: 1.5;
}

button, input { font: inherit; }
button { cursor: pointer; }
button:focus-visible, input:focus-visible, [tabindex="0"]:focus-visible { outline: 3px solid #2869a7; outline-offset: 2px; }

.ops-topbar {
	position: sticky;
	top: 0;
	z-index: 30;
	display: flex;
	align-items: center;
	gap: 18px;
	height: 66px;
	padding: 0 34px;
	border-bottom: 1px solid #e5e0d7;
	background: rgba(255, 255, 255, .96);
	backdrop-filter: blur(12px);
}

.brand { display: flex; align-items: center; gap: 12px; padding: 0; border: 0; background: transparent; color: inherit; text-align: left; }
.brand-mark { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 10px 16px 16px 10px; background: #14233c; color: #fff; box-shadow: inset 6px 0 rgba(0,0,0,.16); font-size: var(--type-label); font-weight: 900; letter-spacing: .08em; }
.brand-copy strong, .brand-copy small { display: block; }
.brand-copy strong { font-size: 1rem; line-height: 1.25; }
.brand-copy small { margin-top: 2px; color: var(--color-muted); font-size: var(--type-label); line-height: 1.35; }
.topbar-divider { width: 1px; height: 32px; background: #e5e0d7; }
.topbar-context { display: flex; gap: 5px; min-width: 0; color: var(--color-muted); font-size: var(--type-body); }
.topbar-context strong { overflow: hidden; color: #1d2739; text-overflow: ellipsis; white-space: nowrap; }
.topbar-actions { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.live-chip { padding: 6px 10px; border-radius: 999px; background: #e6f5ef; color: #14775d; font-size: var(--type-label); font-weight: 800; letter-spacing: .04em; }
.avatar { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 50%; background: #14233c; color: #fff; font-size: var(--type-label); font-weight: 800; }
.icon-button { display: grid; place-items: center; width: 44px; height: 44px; border: 1px solid #e5e0d7; border-radius: 10px; background: #fff; color: #5f6878; }
.icon-button:hover { color: #172033; background: #f7f5f0; }

.ops-main { min-height: calc(100vh - 66px); }
.page { width: min(1440px, 100%); margin: 0 auto; padding: 30px 32px 64px; }
.eyebrow { margin-bottom: 8px; color: #bf4a36; font-size: var(--type-label); font-weight: 800; line-height: 1.35; letter-spacing: .1em; text-transform: uppercase; }
h1, h2, p { margin-top: 0; }
h1 { margin-bottom: 8px; font-size: var(--type-page-title); line-height: 1.25; letter-spacing: -.02em; }
h2 { font-size: var(--type-section-title); line-height: 1.3; }
p { font-size: var(--type-body); line-height: 1.5; }
.home-heading, .page-heading { display: flex; align-items: flex-start; gap: 18px; margin-bottom: 26px; }
.home-heading p, .page-heading p { max-width: 75ch; margin-bottom: 0; color: var(--color-muted); }
.home-heading > .button { margin-left: auto; }
.heading-copy { min-width: 0; }
.heading-action, .heading-actions { margin-left: auto; }
.heading-actions { display: flex; gap: 8px; }

.button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 10px 16px; border: 1px solid transparent; border-radius: 10px; font-size: var(--type-body); font-weight: 700; line-height: 1.4; }
.button.primary { background: #14233c; color: #fff; }
.button.secondary { border-color: #ded9cf; background: #fff; color: #172033; }
.button.secondary:hover { background: #f9f8f5; border-color: #c8c1b5; }
.button.small { min-height: 36px; padding: 7px 12px; font-size: var(--type-label); }
.button.full { width: 100%; }
.button:disabled { opacity: .55; cursor: wait; }

.group-grid, .book-grid, .manage-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.group-card, .book-card, .manage-card { min-width: 0; border: 1px solid #e2ddd4; border-radius: 16px; background: #fff; color: inherit; text-align: left; box-shadow: 0 7px 24px rgba(25,35,53,.04); transition: transform .14s ease, border-color .14s ease, box-shadow .14s ease; }
.group-card:hover, .book-card:hover, .manage-card:hover { transform: translateY(-2px); border-color: #c9c1b5; box-shadow: 0 12px 30px rgba(25,35,53,.08); }
.group-card { display: flex; flex-direction: column; min-height: 272px; padding: 20px; }
.group-card-head { display: flex; align-items: flex-start; gap: 12px; }
.group-code { display: grid; place-items: center; flex: 0 0 auto; width: 42px; height: 48px; border-radius: 6px 10px 10px 6px; color: #fff; box-shadow: inset 5px 0 rgba(0,0,0,.14); font-size: var(--type-label); font-weight: 900; }
.group-copy strong, .group-copy small { display: block; }
.group-copy strong { font-size: var(--type-card-title); line-height: 1.35; }
.group-copy small { margin-top: 6px; color: var(--color-muted); font-size: var(--type-body); line-height: 1.45; }
.book-shelf { display: flex; align-items: flex-end; gap: 6px; min-height: 86px; margin: auto 0 15px; padding: 0 9px 8px; border-bottom: 7px solid #d7c9b8; }
.mini-book { display: flex; align-items: center; justify-content: center; width: 48px; padding: 6px 4px; border-radius: 3px 6px 3px 3px; color: #fff; box-shadow: inset 5px 0 rgba(0,0,0,.14); font-size: .6875rem; font-weight: 800; line-height: 1.2; text-align: center; }
.group-card-foot, .book-open, .manage-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; color: var(--color-muted); font-size: var(--type-body); }
.group-card-foot strong, .book-open strong, .manage-foot strong { color: #2869a7; font-size: var(--type-body); }

.cover-po { background: #b94d3d; }
.cover-grn { background: #267c69; }
.cover-pi { background: #72568e; }
.cover-ipd { background: #b57b28; }
.cover-wo { background: #2869a7; }
.cover-dc { background: #53727c; }

.breadcrumbs { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-height: 32px; margin-bottom: 16px; color: var(--color-muted); font-size: var(--type-body); }
:deep(.breadcrumbs button) { min-height: 32px; padding: 4px 0; border: 0; background: transparent; color: #2869a7; font-weight: 700; }
.book-identity { display: grid; place-items: center; flex: 0 0 auto; width: 56px; height: 66px; border-radius: 6px 12px 12px 6px; color: #fff; box-shadow: inset 7px 0 rgba(0,0,0,.14); font-size: var(--type-label); font-weight: 900; }
.book-identity.master-identity { background: #e8f1f9; color: #2869a7; box-shadow: none; }
.book-card { overflow: hidden; display: grid; grid-template-columns: 118px minmax(0, 1fr); min-height: 205px; }
.book-cover { position: relative; display: flex; flex-direction: column; justify-content: center; min-height: 205px; padding: 18px; color: #fff; box-shadow: inset 10px 0 rgba(0,0,0,.14); }
.book-cover small { margin-bottom: 10px; font-size: var(--type-label); font-weight: 800; letter-spacing: .1em; }
.book-cover strong { font-size: 1rem; line-height: 1.35; }
.book-spine { position: absolute; inset: 0 auto 0 11px; width: 1px; background: rgba(255,255,255,.22); }
.book-meta { padding: 22px 18px 10px; }
.book-meta strong, .book-meta small { display: block; }
.book-meta strong { font-size: 1rem; line-height: 1.4; }
.book-meta small { margin-top: 8px; color: var(--color-muted); font-size: var(--type-body); line-height: 1.5; }
.book-open { grid-column: 2; align-self: end; padding: 0 18px 18px; }

.manage-card { display: flex; flex-direction: column; min-height: 238px; padding: 20px; }
.manage-icon { display: grid; place-items: center; width: 43px; height: 43px; margin-bottom: 15px; border-radius: 11px; background: #e8f1f9; color: #2869a7; font-size: var(--type-label); font-weight: 900; }
.manage-card > strong { font-size: var(--type-card-title); line-height: 1.35; }
.manage-card > p { min-height: 42px; margin: 8px 0 14px; color: var(--color-muted); font-size: var(--type-body); line-height: 1.5; }
.usage { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 16px; }
.usage small { padding: 5px 8px; border-radius: 999px; background: #f3f2ef; color: #5f6878; font-size: var(--type-label); font-weight: 700; line-height: 1.3; }
.manage-foot { margin-top: auto; }

.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; padding: 12px; border: 1px solid #e2ddd4; border-radius: 13px; background: #fff; }
.search-box { position: relative; flex: 1; max-width: 430px; }
.search-box i { position: absolute; top: 15px; left: 13px; color: #5f6878; font-size: var(--type-body); }
.search-box input { width: 100%; height: 44px; padding: 10px 12px 10px 38px; border: 1px solid #ded9cf; border-radius: 9px; background: #faf9f7; color: #172033; font-size: var(--type-body); }
.search-box input:focus { border-color: #2869a7; outline: 3px solid rgba(40,105,167,.12); }
.status-filters { display: flex; gap: 6px; overflow-x: auto; margin-left: auto; }
.status-filters button { min-height: 40px; padding: 8px 12px; border: 1px solid #ded9cf; border-radius: 999px; background: #fff; color: var(--color-muted); font-size: var(--type-label); font-weight: 700; white-space: nowrap; }
.status-filters button.active { border-color: #14233c; background: #14233c; color: #fff; }
.record-count { min-width: 110px; color: var(--color-muted); font-size: var(--type-label); text-align: right; }
.list-card, .section-card { overflow: hidden; border: 1px solid #e2ddd4; border-radius: 15px; background: #fff; box-shadow: 0 5px 20px rgba(23,32,51,.035); }
table { width: 100%; border-collapse: collapse; }
th { padding: 12px 14px; border-bottom: 1px solid #e8e3db; background: #faf9f7; color: var(--color-muted); font-size: var(--type-label); font-weight: 800; line-height: 1.35; letter-spacing: .05em; text-align: left; text-transform: uppercase; white-space: nowrap; }
td { padding: 14px; border-bottom: 1px solid #efebe5; font-size: var(--type-body); line-height: 1.45; vertical-align: middle; }
tbody tr:last-child td { border-bottom: 0; }
.desktop-list tbody tr { cursor: pointer; }
.desktop-list tbody tr:hover { background: #fafcff; }
.record-id { color: #2869a7; font-weight: 800; }
.row-arrow { color: #a39c91; font-size: 18px; text-align: right; }
.status { display: inline-flex; align-items: center; gap: 6px; padding: 5px 9px; border-radius: 999px; background: #eef1f4; color: #5f6878; font-size: var(--type-label); font-weight: 800; line-height: 1.35; white-space: nowrap; }
.status::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.status-active, .status-submitted, .status-approved, .status-received, .status-completed, .status-fully-received, .status-fully-delivered { background: #e6f5ef; color: #14775d; }
.status-draft, .status-pending, .status-approval-pending, .status-partially-received, .status-partially-delivered, .status-partly-received { background: #fff4da; color: #8a550c; }
.status-open, .status-ordered, .status-in-progress, .status-cutting-approved { background: #e8f1f9; color: #2869a7; }
.status-disabled, .status-cancelled, .status-closed { background: #eef0f2; color: #5f6878; }
.mobile-list { display: none; }
.load-more { display: flex; justify-content: center; margin-top: 16px; }
.view-note { margin-top: 18px; padding: 12px 14px; border: 1px dashed #cec7bb; border-radius: 10px; background: #fffdf8; color: var(--color-muted); font-size: var(--type-label); line-height: 1.5; }

.loading-state, .error-state { display: flex; align-items: center; justify-content: center; gap: 10px; min-height: 180px; padding: 28px; border: 1px solid #e2ddd4; border-radius: 15px; background: #fff; color: var(--color-muted); }
.error-state { justify-content: flex-start; color: #9f2e2e; }
.error-state div { display: grid; gap: 3px; }
.error-state span { color: var(--color-muted); font-size: var(--type-body); }
.error-state .button { margin-left: auto; }
.empty-state { display: grid; place-items: center; max-width: 620px; min-height: 300px; margin: 8vh auto 0; padding: 38px; border: 1px solid #e2ddd4; border-radius: 16px; background: #fff; text-align: center; }
.empty-state.compact { max-width: none; min-height: 210px; margin: 0; }
.empty-state i { color: #7c8797; font-size: 27px; }
.empty-state h2 { margin: 13px 0 6px; }
.empty-state p { margin-bottom: 17px; color: var(--color-muted); }

.detail-hero { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 18px; margin-bottom: 16px; padding: 22px; border: 1px solid #e2ddd4; border-radius: 16px; background: #fff; box-shadow: 0 5px 22px rgba(23,32,51,.04); }
.detail-id { margin-bottom: 6px; color: #2869a7; font-size: var(--type-body); font-weight: 800; letter-spacing: .03em; }
.detail-hero h1 { margin-bottom: 6px; font-size: var(--type-detail-title); line-height: 1.3; }
.detail-hero p { margin: 0; color: var(--color-muted); }
.detail-status { align-self: start; }
.fact-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; overflow: hidden; margin-bottom: 16px; border: 1px solid #e2ddd4; border-radius: 14px; background: #e2ddd4; }
.fact { min-height: 88px; padding: 16px; background: #fff; }
.fact span { display: block; color: var(--color-muted); font-size: var(--type-label); font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }
.fact strong { display: block; overflow-wrap: anywhere; margin-top: 7px; font-size: var(--type-body); line-height: 1.45; }
.detail-layout { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(290px, .65fr); gap: 16px; align-items: start; }
.detail-layout > div, .detail-layout > aside, .section-card { min-width: 0; }
.section-card { margin-bottom: 16px; }
.section-card header { display: flex; align-items: center; gap: 9px; padding: 14px 16px; border-bottom: 1px solid #e8e3db; background: #faf9f7; }
.section-card header h2 { margin: 0; font-size: 1rem; line-height: 1.4; }
.section-card header span { margin-left: auto; color: var(--color-muted); font-size: var(--type-label); }
.table-scroll { max-width: 100%; overflow-x: auto; }
.section-copy { padding: 18px; color: var(--color-muted); font-size: var(--type-body); line-height: 1.5; }
.linked-stack, .address-stack { display: grid; gap: 8px; padding: 14px; }
.linked-stack button { display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px; border: 1px solid #e2ddd4; border-radius: 10px; background: #faf9f7; color: #172033; text-align: left; }
.linked-stack button:disabled { cursor: default; opacity: .75; }
.linked-stack button > span:first-child { display: grid; place-items: center; width: 36px; height: 40px; border-radius: 7px; background: #e8f1f9; color: #2869a7; font-size: .6875rem; font-weight: 900; }
.linked-stack button span:nth-child(2) { min-width: 0; }
.linked-stack button strong, .linked-stack button small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.linked-stack button strong { font-size: var(--type-body); }
.linked-stack button small { margin-top: 2px; color: var(--color-muted); font-size: var(--type-label); }
.linked-stack button i { margin-left: auto; color: #929aa7; }
.address-stack article { padding: 11px; border: 1px solid #e2ddd4; border-radius: 10px; background: #faf9f7; }
.address-stack strong, .address-stack span, .address-stack small { display: block; }
.address-stack strong { font-size: var(--type-body); }
.address-stack span { margin-top: 5px; color: var(--color-muted); font-size: var(--type-label); line-height: 1.5; }
.address-stack small { margin-top: 6px; color: #2869a7; font-size: var(--type-label); }

@media (max-width: 1100px) {
	.group-grid, .manage-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	.book-grid { grid-template-columns: 1fr 1fr; }
	.detail-layout { grid-template-columns: 1fr; }
}

@media (max-width: 760px) {
	.ops-topbar { height: 58px; padding: 0 16px; }
	.brand-mark { width: 38px; height: 38px; }
	.topbar-divider, .topbar-context, .live-chip { display: none; }
	.page { padding: 22px 16px 46px; }
	.home-heading, .page-heading { flex-wrap: wrap; }
	.home-heading > .button, .heading-action, .heading-actions { width: 100%; margin-left: 0; }
	.heading-actions .button { flex: 1; }
	.group-grid, .book-grid, .manage-grid { grid-template-columns: 1fr; }
	.group-card { min-height: 245px; }
	.book-card { grid-template-columns: 105px minmax(0, 1fr); }
	.toolbar { align-items: stretch; flex-direction: column; }
	.search-box { max-width: none; }
	.status-filters { margin-left: 0; }
	.record-count { text-align: left; }
	.desktop-list { display: none; }
	.mobile-list { display: grid; gap: 10px; }
	.mobile-row { display: block; width: 100%; padding: 14px; border: 1px solid #e2ddd4; border-radius: 12px; background: #fff; color: #172033; text-align: left; }
	.mobile-row-head { display: flex; align-items: center; gap: 8px; }
	.mobile-row-head > strong { overflow-wrap: anywhere; color: #2869a7; font-size: var(--type-body); }
	.mobile-row-head .status { margin-left: auto; }
	.mobile-row-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 13px; }
	.mobile-row-grid small, .mobile-row-grid strong { display: block; }
	.mobile-row-grid small { color: var(--color-muted); font-size: var(--type-label); line-height: 1.35; text-transform: uppercase; }
	.mobile-row-grid strong { overflow-wrap: anywhere; margin-top: 3px; font-size: var(--type-body); line-height: 1.45; }
	.detail-hero { grid-template-columns: auto minmax(0, 1fr); padding: 17px; }
	.detail-status { grid-column: 1 / -1; }
	.fact-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 480px) {
	.brand-copy strong { font-size: .9375rem; }
	.brand-copy small { font-size: var(--type-label); }
	.avatar { display: none; }
	.group-grid, .book-grid, .manage-grid, .fact-grid { grid-template-columns: 1fr; }
	.book-card { grid-template-columns: 96px minmax(0, 1fr); }
	.book-cover { min-height: 190px; padding: 14px; }
	.book-meta { padding: 18px 14px 8px; }
	.book-open { padding: 0 14px 14px; }
}
</style>
