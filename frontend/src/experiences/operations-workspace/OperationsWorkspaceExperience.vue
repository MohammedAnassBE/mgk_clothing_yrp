<template>
	<div class="ops-shell" :class="{ 'is-tamil': isTamil }">
		<header class="ops-topbar">
			<RouterLink class="brand" to="/" aria-label="Go to all books">
				<span class="brand-mark">MGK</span>
				<span class="brand-copy"><strong>MGK Clothing</strong><small>Operations Workspace</small></span>
			</RouterLink>
			<span class="topbar-divider" />
			<div class="topbar-context"><strong>{{ pageTitle }}</strong><span>· Operations workspace</span></div>
			<div class="topbar-actions">
				<div class="language-toggle" role="group" aria-label="Master name language">
					<button type="button" :class="{ active: !isTamil }" :aria-pressed="!isTamil" @click="setLanguage('en')">English</button>
					<button type="button" :class="{ active: isTamil }" :aria-pressed="isTamil" @click="setLanguage('ta')">தமிழ்</button>
				</div>
				<span class="live-chip">LIVE VIEW</span>
				<span class="avatar" :title="userName">{{ userInitials }}</span>
				<button class="icon-button" type="button" title="Log out" aria-label="Log out" @click="signOut">
					<i class="pi pi-sign-out" />
				</button>
			</div>
		</header>

		<main class="ops-main">
			<section v-if="page.kind === 'stock-note'" class="page stock-note-page">
				<StockBalanceView />
			</section>

			<!-- Purchase Order entry reuses the platform's permission-aware document
			     form while the MGK workspace keeps owning the surrounding experience. -->
			<section v-else-if="page.kind === 'purchase-order-document'" class="page po-document-page">
				<DocDetail
					doc-route="purchase-order"
					:id="page.id"
					presentation="book-entry"
					:linked-route-resolver="resolveExperienceDocumentPath"
				/>
			</section>

			<!-- GRN entry keeps the same approved book-form language as Purchase
			     Order, while DocDetail owns the source-aware receipt body. -->
			<section v-else-if="page.kind === 'grn-document'" class="page po-document-page">
				<DocDetail
					doc-route="goods-received-note"
					:id="page.id"
					presentation="grn-book-entry"
					:linked-route-resolver="resolveExperienceDocumentPath"
				/>
			</section>

			<!-- Delivery Challan is a source-driven Work Order dispatch. It gets the
			     same readable book shell as PO/GRN while DocDetail owns the derived
			     movement fields, locked deliverables and stock validation. -->
			<section v-else-if="page.kind === 'dc-document'" class="page po-document-page">
				<DocDetail
					doc-route="delivery-challan"
					:id="page.id"
					presentation="delivery-challan-book-entry"
					:linked-route-resolver="resolveExperienceDocumentPath"
				/>
			</section>

			<!-- Billing is a GRN-driven supplier invoice. The Registered Experience
			     owns the selection/grouping UI; base yrp remains authoritative for
			     eligibility, totals and GRN link lifecycle. -->
			<section v-else-if="page.kind === 'pi-document'" class="page po-document-page">
				<DocDetail
					doc-route="purchase-invoice"
					:id="page.id"
					presentation="purchase-invoice-book-entry"
					:linked-route-resolver="resolveExperienceDocumentPath"
				/>
			</section>

			<!-- Stock movement keeps the same document shell and visual hierarchy as
			     Purchase Order, while the purpose and stock engine remain base-YRP owned. -->
			<section v-else-if="page.kind === 'stock-entry-document'" class="page po-document-page">
				<DocDetail
					doc-route="stock-entry"
					:id="page.id"
					presentation="stock-entry-book-entry"
					:linked-route-resolver="resolveExperienceDocumentPath"
				/>
			</section>

			<!-- MGK inspections are deliberately GRN-based. The source GRN loads the
			     received rows; the operator only classifies their Received Types. -->
			<section v-else-if="page.kind === 'inspection-document'" class="page po-document-page">
				<DocDetail
					doc-route="inspection-entry"
					:id="page.id"
					presentation="inspection-book-entry"
					:linked-route-resolver="resolveExperienceDocumentPath"
				/>
			</section>

			<section v-else-if="page.kind === 'ipd-document'" class="page po-document-page">
				<DocDetail
					doc-route="item-production-detail"
					:id="page.id"
					presentation="ipd-yarn-entry"
					:linked-route-resolver="resolveExperienceDocumentPath"
				/>
			</section>

			<!-- Work Order now uses the shared permission-aware document shell and
			     editable body. The workspace keeps the familiar process books, while
			     DocDetail owns Save/Submit and Calculate Deliverables. -->
			<section v-else-if="page.kind === 'detail' && page.groupKey === 'wo'" class="page po-document-page">
				<DocDetail
					doc-route="work-order"
					:id="page.name"
					presentation="work-order-book-entry"
					:linked-route-resolver="resolveExperienceDocumentPath"
				/>
			</section>

			<!-- Work Order Correction is a direct working collection: select one
			     submitted Work Order, then add manual deliverables/receivables. -->
			<section v-else-if="page.kind === 'woc-document'" class="page po-document-page">
				<DocDetail
					doc-route="work-order-correction"
					:id="page.id"
					presentation="work-order-correction-book-entry"
					:linked-route-resolver="resolveExperienceDocumentPath"
				/>
			</section>

			<!-- Every permitted working master uses the same clean Purchase Order
			     writing language. DocDetail keeps Frappe permissions authoritative. -->
			<section v-else-if="page.kind === 'master-detail' && selectedMasterAllowed" class="page po-document-page">
				<DocDetail
					:doc-route="selectedMaster.route"
					:id="page.name"
					presentation="master-book-entry"
					:presentation-code="selectedMaster.code"
					:presentation-label="selectedMaster.label"
					:presentation-description="selectedMaster.description"
					:linked-route-resolver="resolveExperienceDocumentPath"
				/>
			</section>

			<!-- Home: permission-aware daily digital books. -->
			<section v-else-if="page.kind === 'home'" class="page">
				<div class="home-heading">
					<div>
						<div class="eyebrow">MGK daily work</div>
						<h1>Your Digital Books</h1>
					</div>
					<div class="home-heading-actions">
						<RouterLink v-if="canRead('Stock Ledger Entry')" class="button secondary" to="/stock">
							<i class="pi pi-chart-bar" /> Stock
						</RouterLink>
						<RouterLink v-if="visibleMasters.length" class="button secondary" to="/manage">
							<i class="pi pi-sliders-h" /> Manage Masters & Access
						</RouterLink>
						<RouterLink v-if="visiblePricesAndCosts.length" class="button secondary" to="/prices-costs">
							<i class="pi pi-indian-rupee" /> Manage Prices & Costs
						</RouterLink>
					</div>
				</div>

				<div v-if="visibleGroups.length" class="group-grid">
					<RouterLink
						v-for="group in visibleGroups"
						:key="group.key"
						class="group-card"
						:to="groupRoute(group)"
					>
						<span class="group-card-head">
							<span class="group-code" :class="`cover-${group.cover}`">{{ group.code }}</span>
							<span class="group-copy"><strong>{{ group.label }}</strong><small>{{ group.description }}</small></span>
							<span class="group-record-count">{{ countLabel(groupCounts[group.key]) }}</span>
						</span>
						<span v-if="!group.directList" class="book-shelf" aria-hidden="true">
							<span
								v-for="book in group.books"
								:key="book.key"
								class="mini-book"
								:class="`cover-${group.cover}`"
							>{{ bookText(book, "short") }}</span>
						</span>
						<span v-else class="direct-card-rail" :class="`cover-${group.cover}`" aria-hidden="true"></span>
					</RouterLink>
				</div>
				<div v-else class="empty-state"><i class="pi pi-lock" /><h2>No books available</h2><p>Your roles do not currently provide read access to these documents.</p></div>
			</section>

			<!-- One document group and its familiar books. -->
			<section v-else-if="page.kind === 'group' && selectedGroup" class="page">
				<Breadcrumbs :items="[{ label: 'All Books', path: '/' }, { label: selectedGroup.label }]" />
				<div class="page-heading">
					<span class="book-identity" :class="`cover-${selectedGroup.cover}`">{{ selectedGroup.code }}</span>
					<div class="heading-copy"><div class="eyebrow">Digital books</div><h1>{{ selectedGroup.label }}</h1><p>Choose the familiar working book to view its records.</p></div>
					<div class="heading-actions">
						<RouterLink class="button secondary" to="/">← All Books</RouterLink>
						<RouterLink v-if="selectedGroup.key === 'po' && canCreate('Purchase Order')" class="button primary" :to="purchaseOrderRoute()">
							<i class="pi pi-plus" /> New Purchase Order
						</RouterLink>
						<RouterLink v-if="selectedGroup.key === 'wo' && canCreate('Work Order')" class="button primary" :to="workOrderRoute()">
							<i class="pi pi-plus" /> New Work Order
						</RouterLink>
						<RouterLink v-if="selectedGroup.key === 'dc' && canCreate('Delivery Challan')" class="button primary" :to="deliveryChallanRoute()">
							<i class="pi pi-plus" /> New Delivery Challan
						</RouterLink>
					</div>
				</div>
				<div class="book-grid">
					<RouterLink v-for="book in selectedGroup.books" :key="book.key" class="book-card" :to="bookRoute(selectedGroup, book)">
						<span class="book-cover" :class="`cover-${selectedGroup.cover}`">
							<span class="book-spine" />
							<small>{{ selectedGroup.code }}</small>
							<strong>{{ bookText(book, "short") }}</strong>
						</span>
						<span class="book-meta"><strong>{{ bookText(book, "label") }}</strong><small>{{ book.note }}</small></span>
						<span class="book-open"><span>{{ countLabel(bookCounts[book.key]) }}</span><strong>Open book ›</strong></span>
					</RouterLink>
				</div>
			</section>

			<!-- Shared transaction or master list. -->
			<section v-else-if="(page.kind === 'list' && selectedGroup && selectedBook) || (page.kind === 'master-list' && selectedMasterAllowed)" class="page">
				<Breadcrumbs :items="listBreadcrumbs" />
				<div class="page-heading">
					<span v-if="page.kind !== 'master-list'" class="book-identity" :class="listIdentityClass">{{ listIdentityCode }}</span>
					<div class="heading-copy">
						<div class="eyebrow">{{ page.kind === 'master-list' ? 'Master records' : selectedGroup.label }}</div>
						<h1>{{ listTitle }}</h1>
						<p>{{ listDescription }}</p>
					</div>
					<div class="heading-actions">
						<RouterLink class="button secondary" :to="listBackPath">← {{ listBackLabel }}</RouterLink>
						<RouterLink v-if="page.kind === 'list' && selectedGroup.key === 'po' && canCreate('Purchase Order')" class="button primary" :to="purchaseOrderRoute(selectedBook)">
							<i class="pi pi-plus" /> New Purchase Order
						</RouterLink>
						<RouterLink v-if="page.kind === 'list' && selectedGroup.key === 'grn' && canCreate('Goods Received Note')" class="button primary" :to="grnRoute(selectedBook)">
							<i class="pi pi-plus" /> New {{ selectedBook.key === 'po-grn' ? 'PO GRN' : 'Work Order GRN' }}
						</RouterLink>
						<RouterLink v-if="page.kind === 'list' && selectedGroup.key === 'ipd' && canCreate('Item Production Detail')" class="button primary" to="/item-production-detail/new">
							<i class="pi pi-plus" /> New Production Detail
						</RouterLink>
						<RouterLink v-if="page.kind === 'list' && selectedGroup.key === 'wo' && canCreate('Work Order')" class="button primary" :to="workOrderRoute(selectedBook)">
							<i class="pi pi-plus" /> New Work Order
						</RouterLink>
						<RouterLink v-if="page.kind === 'list' && selectedGroup.key === 'woc' && canCreate('Work Order Correction')" class="button primary" to="/work-order-correction/new">
							<i class="pi pi-plus" /> New Work Order Correction
						</RouterLink>
						<RouterLink v-if="page.kind === 'list' && selectedGroup.key === 'dc' && canCreate('Delivery Challan')" class="button primary" :to="deliveryChallanRoute(selectedBook)">
							<i class="pi pi-plus" /> New Delivery Challan
						</RouterLink>
						<RouterLink v-if="page.kind === 'list' && selectedGroup.key === 'pi' && canCreate('Purchase Invoice')" class="button primary" :to="purchaseInvoiceRoute(selectedBook)">
							<i class="pi pi-plus" /> New {{ selectedBook.key === 'po-billing' ? 'PO Bill' : 'Job Work Bill' }}
						</RouterLink>
						<RouterLink v-if="page.kind === 'list' && selectedGroup.key === 'se' && canCreate('Stock Entry')" class="button primary" to="/stock-entry/new">
							<i class="pi pi-plus" /> New Stock Entry
						</RouterLink>
						<RouterLink v-if="page.kind === 'list' && selectedGroup.key === 'inspection' && canCreate('Inspection Entry')" class="button primary" :to="inspectionEntryRoute()">
							<i class="pi pi-plus" /> New GRN Inspection
						</RouterLink>
						<RouterLink v-if="page.kind === 'master-list' && canCreate(selectedMaster.doctype)" class="button primary" :to="masterCreateRoute()">
							<i class="pi pi-plus" /> New {{ masterEntityLabel(selectedMaster) }}
						</RouterLink>
					</div>
				</div>

				<div class="toolbar">
					<label class="search-box"><i class="pi pi-search" /><input v-model.trim="searchText" type="search" placeholder="Search the loaded records…" /></label>
					<button
						v-if="customizableListColumns.length"
						class="button secondary small list-columns-button"
						type="button"
						:disabled="listColumnState.loading"
						@click="showListColumnsModal = true"
					>
						<i class="pi pi-sliders-h" /> Columns
					</button>
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
							<thead><tr><th v-for="column in activeListColumns" :key="column.field">{{ column.label }}</th><th /></tr></thead>
							<tbody>
								<tr v-for="row in filteredRows" :key="row.name" tabindex="0" @click="openRow(row, $event)" @auxclick.middle="openRow(row, $event)" @keydown.enter="openRow(row, $event)">
									<td v-for="(column, index) in activeListColumns" :key="column.field">
										<span v-if="column.type === 'status' || column.type === 'enabled' || column.type === 'user_enabled'" class="status" :class="statusClass(statusForColumn(row, column))">{{ statusForColumn(row, column) }}</span>
										<span v-else :class="{ 'record-id': index === 0 }">{{ displayColumn(row, column) }}</span>
									</td>
									<td class="row-arrow">›</td>
								</tr>
							</tbody>
						</table>
					</div>
					<div class="mobile-list">
						<RouterLink v-for="row in filteredRows" :key="row.name" class="mobile-row" :to="rowRoute(row)">
							<span class="mobile-row-head"><strong>{{ displayColumn(row, activeListColumns[0]) }}</strong><span class="status" :class="statusClass(rowStatus(row))">{{ rowStatus(row) }}</span></span>
							<span class="mobile-row-grid"><span v-for="column in activeListColumns.slice(1, 5)" :key="column.field"><small>{{ column.label }}</small><strong>{{ displayColumn(row, column) }}</strong></span></span>
						</RouterLink>
					</div>
					<div v-if="listState.hasMore" class="load-more"><button class="button secondary" type="button" :disabled="listState.loading" @click="loadList(true)"><i v-if="listState.loading" class="pi pi-spin pi-spinner" /> Load more records</button></div>
				</template>
				<div v-if="page.kind === 'list' && selectedGroup.key === 'po'" class="view-note"><strong>Purchase Order workspace:</strong> create a new order here, then open any row to edit, submit or review it according to your permissions.</div>
				<div v-else-if="page.kind === 'list' && selectedGroup.key === 'grn'" class="view-note"><strong>Goods receipt workflow:</strong> select the source document, enter only the received quantities, then save and submit.</div>
				<div v-else-if="page.kind === 'list' && selectedGroup.key === 'ipd'" class="view-note"><strong>Production route:</strong> select the finished Item once, then build its yarn flow in process order.</div>
				<div v-else-if="page.kind === 'list' && selectedGroup.key === 'se'" class="view-note"><strong>Stock movement:</strong> choose the purpose, source and target, then enter the item quantities before saving and submitting.</div>
				<div v-else-if="page.kind === 'list' && selectedGroup.key === 'inspection'" class="view-note"><strong>GRN inspection:</strong> select a submitted Goods Received Note, classify each received quantity, then save and submit.</div>
				<div v-else class="view-note"><strong>Live records:</strong> select any row to review its current information.</div>
			</section>

			<!-- Permission-aware master/access landing. -->
			<section v-else-if="page.kind === 'manage'" class="page">
				<Breadcrumbs :items="[{ label: 'All Books', path: '/' }, { label: 'Manage' }]" />
				<div class="page-heading">
					<div class="heading-copy"><div class="eyebrow">Masters and access</div><h1>Manage</h1><p>Review the master data required by purchasing, receiving, billing and production.</p></div>
					<RouterLink class="button secondary heading-action" to="/">← All Books</RouterLink>
				</div>
				<div class="manage-grid">
					<RouterLink v-for="master in visibleMasters" :key="master.key" class="manage-card" :to="`/manage/${master.key}`">
						<strong>{{ master.label }}</strong>
						<p>{{ master.description }}</p>
						<span class="manage-foot"><span>{{ countLabel(masterCounts[master.key]) }}</span><strong>Manage ›</strong></span>
					</RouterLink>
				</div>
			</section>

			<!-- Commercial rates are intentionally separate from operational masters. -->
			<section v-else-if="page.kind === 'prices-costs'" class="page">
				<Breadcrumbs :items="[{ label: 'All Books', path: '/' }, { label: 'Prices & Costs' }]" />
				<div class="page-heading">
					<div class="heading-copy"><div class="eyebrow">Commercial setup</div><h1>Prices & Costs</h1><p>Maintain purchasing prices and supplier-specific production process costs.</p></div>
					<RouterLink class="button secondary heading-action" to="/">← All Books</RouterLink>
				</div>
				<div class="manage-grid">
					<RouterLink v-for="master in visiblePricesAndCosts" :key="master.key" class="manage-card" :to="`/prices-costs/${master.key}`">
						<strong>{{ master.label }}</strong>
						<p>{{ master.description }}</p>
						<span class="manage-foot"><span>{{ countLabel(masterCounts[master.key]) }}</span><strong>Manage ›</strong></span>
					</RouterLink>
				</div>
			</section>

			<!-- Read-only live detail shared by transactions and masters. -->
			<section v-else-if="(page.kind === 'detail' && selectedGroup) || (page.kind === 'master-detail' && selectedMaster)" class="page">
				<Breadcrumbs :items="detailBreadcrumbs" />
				<div v-if="detailState.loading" class="loading-state"><i class="pi pi-spin pi-spinner" /><span>Loading record…</span></div>
				<div v-else-if="detailState.error" class="error-state" role="alert"><i class="pi pi-exclamation-triangle" /><div><strong>Unable to load record</strong><span>{{ detailState.error }}</span></div><button class="button secondary small" type="button" @click="loadDetail">Retry</button></div>
				<template v-else-if="detailState.doc">
					<section class="detail-hero">
						<span v-if="page.kind !== 'master-detail'" class="book-identity" :class="detailIdentityClass">{{ detailIdentityCode }}</span>
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
								<div class="table-scroll"><table><thead><tr><th v-for="column in section.columns" :key="column">{{ humanize(column) }}</th></tr></thead><tbody><tr v-for="(row, index) in section.rows" :key="row.name || index"><td v-for="column in section.columns" :key="column">{{ displayDetailValue(column, row[column], row) }}</td></tr></tbody></table></div>
							</section>
							<section v-if="!childSections.length" class="section-card"><header><h2>Record information</h2></header><div class="section-copy">This document has no visible child rows. Its important fields are shown above.</div></section>
						</div>
						<aside>
							<section v-if="detailAddresses.length" class="section-card"><header><h2>Linked Addresses</h2><span>{{ detailAddresses.length }}</span></header><div class="address-stack"><article v-for="address in detailAddresses" :key="address.name"><strong>{{ address.address_title || address.address_type || 'Address' }}</strong><span>{{ formatAddress(address) }}</span><small v-if="address.phone"><i class="pi pi-phone" /> {{ address.phone }}</small></article></div></section>
							<section class="section-card"><header><h2>Connected records</h2><span>{{ linkedCards.length }}</span></header><div v-if="linkedCards.length" class="linked-stack"><template v-for="card in linkedCards" :key="`${card.doctype}:${card.name}`"><RouterLink v-if="linkedRoute(card)" :to="linkedRoute(card)"><span>{{ acronym(card.doctype) }}</span><span><strong>{{ card.name }}</strong><small>{{ card.doctype }}</small></span><i class="pi pi-angle-right" /></RouterLink><button v-else type="button" disabled><span>{{ acronym(card.doctype) }}</span><span><strong>{{ card.name }}</strong><small>{{ card.doctype }}</small></span><i class="pi pi-angle-right" /></button></template></div><div v-else class="section-copy">No connected records were returned for this document.</div></section>
							<RouterLink class="button secondary full" :to="detailBackPath">← Back to {{ detailBackLabel }}</RouterLink>
						</aside>
					</div>
					<div class="view-note"><strong>Live read-only view:</strong> this record and its child rows came from Frappe. Data-entry actions are intentionally not part of this phase.</div>
				</template>
			</section>

			<section v-else class="page"><div class="empty-state"><i class="pi pi-compass" /><h2>Page not found</h2><p>Return to the digital books and choose another page.</p><RouterLink class="button primary" to="/">Go to All Books</RouterLink></div></section>
		</main>

		<ColumnCustomizerModal
			v-if="currentListConfig?.doctype"
			v-model:visible="showListColumnsModal"
			:doctype="currentListConfig.doctype"
			:columns="customizableListColumns"
			@saved="onListColumnsSaved"
		/>
	</div>
</template>

<script setup>
import { computed, defineComponent, h, reactive, ref, watch } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"
import { callMethod, getList, getListView, getCount, getDoc, getLinkedDocs, getAddressList, getMeta } from "@/api/client"
import { logout } from "@/api/auth"
import { usePermissions } from "@/composables/usePermissions"
import { useDisplayLanguage } from "@/composables/useDisplayLanguage"
import { useTerminology } from "@/composables/useTerminology"
import { useLinkTitles, LOCALIZED_NAME_FIELDS } from "@/composables/useLinkTitles"
import ColumnCustomizerModal from "@/components/ColumnCustomizerModal.vue"
import DocDetail from "@/views/dynamic/DocDetail.vue"
import StockBalanceView from "./StockBalanceView.vue"
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
const { canRead, canCreate, isAdmin, hasRole } = usePermissions()
const { isTamil, setLanguage } = useDisplayLanguage()
const { term } = useTerminology()
const linkTitles = useLinkTitles()

const Breadcrumbs = defineComponent({
	props: { items: { type: Array, default: () => [] } },
	setup(props) {
		return () => h("nav", { class: "breadcrumbs", "aria-label": "Breadcrumb" },
			props.items.flatMap((item, index) => {
				const nodes = []
				if (index) nodes.push(h("span", { class: "breadcrumb-separator" }, "›"))
				nodes.push(item.path
					? h(RouterLink, { to: item.path }, () => item.label)
					: h("span", item.label))
				return nodes
			})
		)
	},
})

const page = computed(() => {
	const parts = route.path.split("/").filter(Boolean).map(decodeURIComponent)
	if (!parts.length || parts[0] === "home") return { kind: "home" }
	if (parts[0] === "stock") return { kind: "stock-note" }
	if (parts[0] === "purchase-order" && parts[1]) return { kind: "purchase-order-document", id: parts.slice(1).join("/") }
	if (parts[0] === "purchase-order") return { kind: "group", groupKey: "po" }
	if (parts[0] === "goods-received-note" && parts[1]) return { kind: "grn-document", id: parts.slice(1).join("/") }
	if (parts[0] === "goods-received-note") return { kind: "group", groupKey: "grn" }
	if (parts[0] === "delivery-challan" && parts[1]) return { kind: "dc-document", id: parts.slice(1).join("/") }
	if (parts[0] === "delivery-challan") return { kind: "list", groupKey: "dc", bookKey: "delivery-challans" }
	if (parts[0] === "purchase-invoice" && parts[1]) return { kind: "pi-document", id: parts.slice(1).join("/") }
	if (parts[0] === "purchase-invoice") return { kind: "group", groupKey: "pi" }
	if (parts[0] === "stock-entry" && parts[1]) return { kind: "stock-entry-document", id: parts.slice(1).join("/") }
	if (parts[0] === "stock-entry") return { kind: "list", groupKey: "se", bookKey: "stock-entries" }
	if (parts[0] === "inspection-entry" && parts[1]) return { kind: "inspection-document", id: parts.slice(1).join("/") }
	if (parts[0] === "inspection-entry") return { kind: "list", groupKey: "inspection", bookKey: "grn-inspections" }
	if (parts[0] === "item-production-detail" && parts[1]) return { kind: "ipd-document", id: parts.slice(1).join("/") }
	if (parts[0] === "item-production-detail") return { kind: "list", groupKey: "ipd", bookKey: "production-details" }
	if (parts[0] === "work-order" && parts[1]) return { kind: "detail", groupKey: "wo", name: parts.slice(1).join("/") }
	if (parts[0] === "work-order") return { kind: "group", groupKey: "wo" }
	if (parts[0] === "work-order-correction" && parts[1]) return { kind: "woc-document", id: parts.slice(1).join("/") }
	if (parts[0] === "work-order-correction") return { kind: "list", groupKey: "woc", bookKey: "work-order-corrections" }
	const routeMaster = MASTER_GROUPS.find((master) => master.route === parts[0])
	if (routeMaster && parts[1]) return { kind: "master-detail", masterKey: routeMaster.key, name: parts.slice(1).join("/") }
	if (routeMaster) return { kind: "master-list", masterKey: routeMaster.key }
	if (parts[0] === "group" && parts[1]) {
		const group = getTransactionGroup(parts[1])
		if (group?.directList) return { kind: "list", groupKey: group.key, bookKey: group.books[0]?.key }
		return { kind: "group", groupKey: parts[1] }
	}
	if (parts[0] === "list" && parts[1] && parts[2]) return { kind: "list", groupKey: parts[1], bookKey: parts[2] }
	if (parts[0] === "detail" && parts[1] && parts[2]) return { kind: "detail", groupKey: parts[1], name: parts.slice(2).join("/") }
	if (parts[0] === "manage" && parts[1]) return { kind: "master-list", masterKey: parts[1] }
	if (parts[0] === "manage") return { kind: "manage" }
	if (parts[0] === "prices-costs" && parts[1]) return { kind: "master-list", masterKey: parts[1] }
	if (parts[0] === "prices-costs") return { kind: "prices-costs" }
	if (parts[0] === "master" && parts[1] && parts[2]) return { kind: "master-detail", masterKey: parts[1], name: parts.slice(2).join("/") }
	return { kind: "not-found" }
})

const selectedGroup = computed(() => getTransactionGroup(page.value.groupKey))
const selectedBook = computed(() => getBook(page.value.groupKey, page.value.bookKey))
const selectedMaster = computed(() => getMasterGroup(page.value.masterKey))
const visibleGroups = computed(() => TRANSACTION_GROUPS.filter((group) => canRead(group.doctype)))
const visibleMasterRecords = computed(() => MASTER_GROUPS.filter((master) =>
	canRead(master.doctype) && (!master.adminOnly || isAdmin.value || hasRole("System Manager"))
))
const visibleMasters = computed(() => visibleMasterRecords.value.filter((master) => master.section !== "prices-costs"))
const visiblePricesAndCosts = computed(() => visibleMasterRecords.value.filter((master) => master.section === "prices-costs"))
const selectedMasterAllowed = computed(() => {
	const master = selectedMaster.value
	return !!master && visibleMasterRecords.value.some((allowed) => allowed.key === master.key)
})

const groupCounts = reactive({})
const bookCounts = reactive({})
const masterCounts = reactive({})
const listState = reactive({ rows: [], loading: false, error: "", page: 0, total: 0, hasMore: false })
const listColumnState = reactive({ doctype: "", meta: null, saved: null, loading: false })
const detailState = reactive({ doc: null, linked: {}, loading: false, error: "" })
const detailAddresses = ref([])
const searchText = ref("")
const activeStatus = ref("All")
const showListColumnsModal = ref(false)
let loadSequence = 0
let columnLoadSequence = 0

const bootUser = window.frappe?.boot?.user || {}
const userName = computed(() => bootUser.full_name || bootUser.name || "User")
const userInitials = computed(() => userName.value.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "U")

const currentListConfig = computed(() => page.value.kind === "master-list" ? selectedMaster.value : selectedGroup.value)
const NON_LISTABLE_FIELDS = new Set([
	"Table", "Table MultiSelect", "Text Editor", "Long Text", "Small Text", "Text",
	"HTML", "HTML Editor", "Code", "Markdown Editor", "Section Break", "Column Break",
	"Tab Break", "Fold", "Heading", "Button", "Image", "Geolocation", "Signature", "Password",
])

function columnType(field) {
	if (!field) return undefined
	if (field.fieldname === "docstatus" || ["status", "workflow_state", "approval_status", "open_status"].includes(field.fieldname)) return "status"
	if (field.fieldname === "disabled") return "enabled"
	if (field.fieldname === "enabled") return "user_enabled"
	if (field.fieldtype === "Date") return "date"
	if (field.fieldtype === "Datetime") return "datetime"
	if (field.fieldtype === "Currency") return "currency"
	if (["Int", "Long Int", "Float", "Percent"].includes(field.fieldtype)) return "quantity"
	if (field.fieldtype === "Check") return "check"
	return undefined
}

const configuredListColumnMap = computed(() => new Map(
	(currentListConfig.value?.columns || []).map((column) => [column.field, column]),
))
const primaryListColumn = computed(() => currentListConfig.value?.columns?.[0] || {
	field: "name",
	label: "Name",
	type: "id",
})
const eligibleListColumns = computed(() => {
	const fields = listColumnState.meta?.fields || []
	return fields
		.filter((field) => field.fieldname && !field.hidden && !NON_LISTABLE_FIELDS.has(field.fieldtype))
		.map((field) => {
			const configured = configuredListColumnMap.value.get(field.fieldname) || {}
			return {
				...configured,
				field: field.fieldname,
				label: configured.label || field.label || humanize(field.fieldname),
				fieldtype: field.fieldtype,
				in_list_view: !!field.in_list_view,
				type: configured.type || columnType(field),
				linkTarget: configured.linkTarget || (field.fieldtype === "Link" ? field.options || "" : ""),
			}
		})
})
const activeListColumns = computed(() => {
	const primary = primaryListColumn.value
	const byField = new Map(eligibleListColumns.value.map((column) => [column.field, column]))
	const saved = listColumnState.saved
	if (Array.isArray(saved) && saved.length) {
		return [primary, ...saved
			.filter((column) => column.enabled && column.fieldname !== primary.field)
			.map((column) => byField.get(column.fieldname))
			.filter(Boolean)]
	}
	const configured = currentListConfig.value?.columns || []
	if (configured.length) return configured
	return [primary, ...eligibleListColumns.value.filter((column) => column.in_list_view && column.field !== primary.field)]
})
const customizableListColumns = computed(() => {
	const primaryField = primaryListColumn.value.field
	const eligible = eligibleListColumns.value.filter((column) => column.field !== primaryField)
	const saved = listColumnState.saved
	if (Array.isArray(saved) && saved.length) {
		const byField = new Map(eligible.map((column) => [column.field, column]))
		const ordered = []
		const seen = new Set()
		for (const savedColumn of saved) {
			const column = byField.get(savedColumn.fieldname)
			if (!column) continue
			ordered.push({ fieldname: column.field, label: column.label, fieldtype: column.fieldtype, enabled: !!savedColumn.enabled })
			seen.add(column.field)
		}
		for (const column of eligible) {
			if (!seen.has(column.field)) ordered.push({ fieldname: column.field, label: column.label, fieldtype: column.fieldtype, enabled: false })
		}
		return ordered
	}
	const defaultFields = new Set((currentListConfig.value?.columns || []).map((column) => column.field))
	return eligible.map((column) => ({
		fieldname: column.field,
		label: column.label,
		fieldtype: column.fieldtype,
		enabled: defaultFields.size ? defaultFields.has(column.field) : !!column.in_list_view,
	}))
})
const metaListFieldnames = computed(() => new Set(
	(listColumnState.meta?.fields || []).map((field) => field.fieldname).filter(Boolean),
))
const listFetchFields = computed(() => {
	const fields = new Set(currentListConfig.value?.fields || ["name"])
	fields.add("name")
	for (const column of activeListColumns.value) {
		// A few approved master defaults (Primary Address, Phone, Warehouse Type)
		// are derived after the query. Never send those presentation-only keys to
		// frappe.get_list; saved User Listview choices themselves always come from
		// real meta fields.
		if (column.field === "name" || metaListFieldnames.value.has(column.field)) fields.add(column.field)
		if (metaListFieldnames.value.has(column.fallback)) fields.add(column.fallback)
		if (metaListFieldnames.value.has(column.linkValue)) fields.add(column.linkValue)
	}
	return [...fields]
})
const listTitle = computed(() => {
	if (page.value.kind === "master-list") return selectedMaster.value?.label || "Records"
	if (selectedGroup.value?.directList) return selectedGroup.value.label
	return selectedBook.value ? bookText(selectedBook.value, "label") : "Records"
})
const listDescription = computed(() => {
	if (page.value.kind === "master-list") return selectedMaster.value?.description || ""
	const description = selectedGroup.value?.directList ? selectedGroup.value.description : selectedBook.value?.note
	return `${description || ""} Select any row to review the complete live document.`
})
const listIdentityCode = computed(() => page.value.kind === "master-list" ? selectedMaster.value?.code : selectedGroup.value?.code)
const listIdentityClass = computed(() => page.value.kind === "master-list" ? "master-identity" : `cover-${selectedGroup.value?.cover}`)
const listBackPath = computed(() => {
	if (page.value.kind === "master-list") return selectedMaster.value?.section === "prices-costs" ? "/prices-costs" : "/manage"
	return selectedGroup.value?.directList ? "/" : `/group/${selectedGroup.value?.key}`
})
const listBackLabel = computed(() => {
	if (page.value.kind === "master-list") return selectedMaster.value?.section === "prices-costs" ? "Prices & Costs" : "Manage"
	return selectedGroup.value?.directList ? "All Books" : selectedGroup.value?.label
})
const listBreadcrumbs = computed(() => page.value.kind === "master-list"
	? [{ label: "All Books", path: "/" }, { label: selectedMaster.value?.section === "prices-costs" ? "Prices & Costs" : "Manage", path: selectedMaster.value?.section === "prices-costs" ? "/prices-costs" : "/manage" }, { label: selectedMaster.value?.label || "Records" }]
	: selectedGroup.value?.directList
		? [{ label: "All Books", path: "/" }, { label: selectedGroup.value?.label || "Records" }]
		: [{ label: "All Books", path: "/" }, { label: selectedGroup.value?.label || "Group", path: `/group/${selectedGroup.value?.key}` }, { label: selectedBook.value ? bookText(selectedBook.value, "label") : "Book" }]
)

function bookText(book, field) {
	if (!book) return ""
	return term(book.termKeys?.[field], book[field] || "")
}

const pageTitle = computed(() => {
	if (page.value.kind === "home") return "All Books"
	if (page.value.kind === "stock-note") return "Stock Balance"
	if (page.value.kind === "manage") return "Manage"
	if (page.value.kind === "prices-costs") return "Prices & Costs"
	if (page.value.kind === "purchase-order-document") return page.value.id === "new" ? "New Purchase Order" : page.value.id
	if (page.value.kind === "grn-document") return page.value.id === "new" ? "New Goods Received Note" : page.value.id
	if (page.value.kind === "pi-document") return page.value.id === "new" ? "New Supplier Bill" : page.value.id
	if (page.value.kind === "stock-entry-document") return page.value.id === "new" ? "New Stock Entry" : page.value.id
	if (page.value.kind === "inspection-document") return page.value.id === "new" ? "New GRN Inspection" : page.value.id
	if (page.value.kind === "ipd-document") return page.value.id === "new" ? "New Item Production Detail" : page.value.id
	if (page.value.kind === "detail" && page.value.groupKey === "wo") return page.value.name === "new" ? "New Work Order" : page.value.name
	if (page.value.kind === "woc-document") return page.value.id === "new" ? "New Work Order Correction" : page.value.id
	if (page.value.kind === "master-detail" && selectedMasterAllowed.value) {
		if (page.value.name === "new") return `New ${masterEntityLabel(selectedMaster.value)}`
		return linkTitles.titleFor(selectedMaster.value?.doctype, page.value.name) || page.value.name
	}
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
	const masterDoctype = page.value.kind === "master-detail" ? selectedMaster.value?.doctype : ""
	const masterFields = LOCALIZED_NAME_FIELDS[masterDoctype]
	if (masterFields && doc.name) {
		return linkTitles.linkParts(masterDoctype, doc.name, doc[masterFields.english], doc[masterFields.tamil]).primary
	}
	if (["wo", "ipd", "dc", "grn"].includes(selectedGroup.value?.key) && doc.item) {
		return linkTitles.titleFor("Item", doc.item) || doc.item
	}
	if (doc.supplier) return linkTitles.linkParts("Supplier", doc.supplier, doc.supplier_name).primary
	return doc.supplier_name || doc.name1 || doc.full_name || doc.agent_name || doc.item || doc.supplier || doc.name
})
const detailSubtitle = computed(() => {
	const doc = detailState.doc || {}
	const supplier = doc.supplier ? (linkTitles.titleFor("Supplier", doc.supplier) || doc.supplier) : ""
	if (doc.process_name) return `${doc.process_name}${supplier ? ` · ${supplier}` : ""}`
	if (supplier && supplier !== detailTitle.value) return supplier
	return detailConfig.value?.doctype || "Document"
})
const detailBackPath = computed(() => page.value.kind === "master-detail"
	? `/manage/${selectedMaster.value?.key}`
	: `/list/${selectedGroup.value?.key}/${route.query.book || selectedGroup.value?.books[0]?.key}`
)
const detailBackLabel = computed(() => {
	if (page.value.kind === "master-detail") return selectedMaster.value?.label
	const book = getBook(selectedGroup.value?.key, route.query.book)
	return book ? bookText(book, "label") : selectedGroup.value?.label
})
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
		.map((field) => ({ field, label: humanize(field), value: displayDetailValue(field, doc[field], doc) }))
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
	showListColumnsModal.value = false
	if (page.value.kind === "home") await loadHomeCounts()
	else if (page.value.kind === "manage" || page.value.kind === "prices-costs") await loadMasterCounts()
	else if (page.value.kind === "group") await loadBookCounts()
	else if (page.value.kind === "list" || page.value.kind === "master-list") await loadList(false)
	else if (page.value.kind === "detail" && page.value.groupKey === "wo") {
		// DocDetail owns Work Order load/create state.
		detailState.doc = null
		detailState.error = ""
	}
	else if (page.value.kind === "master-detail" && selectedMasterAllowed.value) {
		// DocDetail owns every permitted master load/create/edit state.
		detailState.doc = null
		detailState.error = ""
	}
	else if (page.value.kind === "detail" || page.value.kind === "master-detail") await loadDetail()
}, { immediate: true })

function groupRoute(group) {
	if (group.directList && group.books[0]) {
		return `/list/${group.key}/${group.books[0].key}`
	}
	return `/group/${group.key}`
}

function bookRoute(group, book) {
	return `/list/${group.key}/${book.key}`
}

function purchaseOrderRoute(book = null) {
	const query = {}
	if (book?.key) query.book = book.key
	if (book?.key === "karigan-order") query.mgk_is_karigan_order = 1
	if (book?.key === "salavai-cone-order") query.mgk_is_salavai_cone_order = 1
	if (book?.key === "other-orders") {
		query.mgk_is_karigan_order = 0
		query.mgk_is_salavai_cone_order = 0
	}
	return { path: "/purchase-order/new", query }
}

function grnRoute(book) {
	const against = book?.key === "po-grn" ? "Purchase Order" : "Work Order"
	return {
		path: "/goods-received-note/new",
		query: { book: book?.key || "", against },
	}
}

function deliveryChallanRoute(book = null) {
	return {
		path: "/delivery-challan/new",
		query: book?.key ? { book: book.key } : {},
	}
}

function purchaseInvoiceRoute(book) {
	const against = book?.key === "job-work-billing" ? "Work Order" : "Purchase Order"
	return {
		path: "/purchase-invoice/new",
		query: { book: book?.key || "", against },
	}
}

function inspectionEntryRoute() {
	return {
		path: "/inspection-entry/new",
		query: { against: "Goods Received Note" },
	}
}

function workOrderRoute(book = null) {
	const processName = book?.key === "dyeing"
		? "Dyeing"
		: book?.key === "doubling"
			? "Doubling"
			: ""
	return {
		path: "/work-order/new",
		query: processName ? { process_name: processName, book: book.key } : {},
	}
}

function masterCreateRoute() {
	if (!selectedMasterAllowed.value || !canCreate(selectedMaster.value.doctype)) return "/"
	return `/${selectedMaster.value.route}/new`
}

function masterEntityLabel(master) {
	return ({
		items: "Item",
		suppliers: "Supplier",
		agents: "MGK Agent",
		processes: "Process",
		"received-types": "Received Type",
		warehouses: "Warehouse",
		"item-prices": "Item Price",
		"process-costs": "Process Cost",
		users: "User",
	})[master?.key] || master?.label || "Record"
}

function rowRoute(row) {
	if (page.value.kind === "master-list" && selectedMasterAllowed.value) return `/${selectedMaster.value.route}/${encodeURIComponent(row.name)}`
	if (selectedGroup.value?.key === "po") return { path: `/purchase-order/${encodeURIComponent(row.name)}`, query: { book: selectedBook.value.key } }
	if (selectedGroup.value?.key === "grn") return { path: `/goods-received-note/${encodeURIComponent(row.name)}`, query: { book: selectedBook.value.key } }
	if (selectedGroup.value?.key === "dc") return { path: `/delivery-challan/${encodeURIComponent(row.name)}`, query: { book: selectedBook.value.key } }
	if (selectedGroup.value?.key === "pi") return { path: `/purchase-invoice/${encodeURIComponent(row.name)}`, query: { book: selectedBook.value.key } }
	if (selectedGroup.value?.key === "se") return `/stock-entry/${encodeURIComponent(row.name)}`
	if (selectedGroup.value?.key === "inspection") return `/inspection-entry/${encodeURIComponent(row.name)}`
	if (selectedGroup.value?.key === "ipd") return `/item-production-detail/${encodeURIComponent(row.name)}`
	if (selectedGroup.value?.key === "wo") return { path: `/work-order/${encodeURIComponent(row.name)}`, query: { book: selectedBook.value.key } }
	if (selectedGroup.value?.key === "woc") return `/work-order-correction/${encodeURIComponent(row.name)}`
	return { path: `/detail/${selectedGroup.value.key}/${encodeURIComponent(row.name)}`, query: { book: selectedBook.value.key } }
}

function openRow(row, event) {
	const target = rowRoute(row)
	if (event?.button === 1 || event?.ctrlKey || event?.metaKey) {
		event.preventDefault()
		window.open(router.resolve(target).href, "_blank", "noopener")
		return
	}
	router.push(target)
}

function resolveExperienceDocumentPath(doctype, name) {
	if (!doctype || !name) return ""
	const encodedName = encodeURIComponent(name)
	const master = MASTER_GROUPS.find((item) => item.doctype === doctype)
	if (master && canRead(master.doctype)) return `/${master.route}/${encodedName}`
	const group = TRANSACTION_GROUPS.find((item) => item.doctype === doctype)
	if (!group || !canRead(group.doctype)) return ""
	if (group.key === "po") return `/purchase-order/${encodedName}`
	if (group.key === "grn") return `/goods-received-note/${encodedName}`
	if (group.key === "dc") return `/delivery-challan/${encodedName}`
	if (group.key === "pi") return `/purchase-invoice/${encodedName}`
	if (group.key === "se") return `/stock-entry/${encodedName}`
	if (group.key === "inspection") return `/inspection-entry/${encodedName}`
	if (group.key === "ipd") return `/item-production-detail/${encodedName}`
	if (group.key === "wo") return `/work-order/${encodedName}`
	if (group.key === "woc") return `/work-order-correction/${encodedName}`
	return `/detail/${group.key}/${encodedName}`
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
	await Promise.all(visibleMasterRecords.value.map(async (master) => {
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
	if (!config || (page.value.kind === "master-list" && !selectedMasterAllowed.value)) return
	const sequence = ++loadSequence
	if (!append) {
		listState.rows = []
		listState.page = 0
		listState.total = 0
		listState.hasMore = false
	}
	listState.loading = true
	listState.error = ""
	if (!append) {
		await loadListColumnPreferences(config.doctype)
		if (sequence !== loadSequence) return
	}
	const filters = page.value.kind === "list" ? (selectedBook.value?.filters || []) : []
	const needsDistinct = hasChildTableFilters(config.doctype, filters)
	try {
		const params = {
			fields: listFetchFields.value,
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

async function getUserListColumns(doctype) {
	try {
		const rows = await callMethod(
			"yrp.yrp.doctype.user_listview.user_listview.get_user_listview",
			{ doctype_name: doctype },
		)
		return Array.isArray(rows) ? rows : null
	} catch {
		return null
	}
}

async function loadListColumnPreferences(doctype, force = false) {
	if (!doctype) return
	if (!force && listColumnState.doctype === doctype && listColumnState.meta) return
	const sequence = ++columnLoadSequence
	if (listColumnState.doctype !== doctype) {
		listColumnState.doctype = doctype
		listColumnState.meta = null
		listColumnState.saved = null
	}
	listColumnState.loading = true
	try {
		const [metaBundle, saved] = await Promise.all([
			getMeta(doctype),
			getUserListColumns(doctype),
		])
		if (sequence !== columnLoadSequence || currentListConfig.value?.doctype !== doctype) return
		listColumnState.doctype = doctype
		listColumnState.meta = Array.isArray(metaBundle) ? metaBundle[0] || null : metaBundle || null
		listColumnState.saved = saved
	} catch {
		if (sequence !== columnLoadSequence || currentListConfig.value?.doctype !== doctype) return
		listColumnState.doctype = doctype
		listColumnState.meta = null
		listColumnState.saved = null
	} finally {
		if (sequence === columnLoadSequence) listColumnState.loading = false
	}
}

async function onListColumnsSaved() {
	showListColumnsModal.value = false
	const doctype = currentListConfig.value?.doctype
	if (!doctype) return
	await loadListColumnPreferences(doctype, true)
	await loadList(false)
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
	if (column.type === "check") return Number(value) ? "Yes" : "No"
	if (column.localizedDoctype) {
		const canonical = row?.[column.linkValue || "name"] || row?.name
		return linkTitles.linkParts(column.localizedDoctype, canonical, value, row?.mgk_tamil_name).primary
	}
	if (column.linkTarget && value) {
		const canonical = row?.[column.linkValue || column.field] || value
		return linkTitles.linkParts(column.linkTarget, canonical, value).primary
	}
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

function localizedDetailValue(field, value, row = {}) {
	if (!value) return ""
	const supplierFields = new Set(["supplier", "billing_supplier", "from_supplier", "to_supplier", "from_location", "delivery_location", "mgk_handling_supplier"])
	const warehouseFields = new Set(["warehouse", "from_warehouse", "to_warehouse", "delivery_warehouse"])
	const itemFields = new Set(["item", "item_name", "parent_item", "yarn_item", "input_item", "output_item", "bom_item"])
	if (supplierFields.has(field)) return linkTitles.titleFor("Supplier", value) || value
	if (warehouseFields.has(field)) return linkTitles.titleFor("Warehouse", value) || value
	if (itemFields.has(field)) return linkTitles.titleFor("Item", value) || value
	if (field === "mgk_agent") return linkTitles.titleFor("MGK Agent", value) || value
	if (field === "supplier_name" && row.supplier) return linkTitles.linkParts("Supplier", row.supplier, value).primary
	return ""
}

function displayDetailValue(field, value, row = {}) {
	if (value === undefined || value === null || value === "") return "—"
	const localized = localizedDetailValue(field, value, row)
	if (localized) return localized
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

.brand { display: flex; align-items: center; gap: 12px; padding: 0; border: 0; background: transparent; color: inherit; text-align: left; text-decoration: none; }
.brand-mark { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 10px 16px 16px 10px; background: #14233c; color: #fff; box-shadow: inset 6px 0 rgba(0,0,0,.16); font-size: var(--type-label); font-weight: 900; letter-spacing: .08em; }
.brand-copy strong, .brand-copy small { display: block; }
.brand-copy strong { font-size: 1rem; line-height: 1.25; }
.brand-copy small { margin-top: 2px; color: var(--color-muted); font-size: var(--type-label); line-height: 1.35; }
.topbar-divider { width: 1px; height: 32px; background: #e5e0d7; }
.topbar-context { display: flex; gap: 5px; min-width: 0; color: var(--color-muted); font-size: var(--type-body); }
.topbar-context strong { overflow: hidden; color: #1d2739; text-overflow: ellipsis; white-space: nowrap; }
.topbar-actions { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.language-toggle { display: inline-flex; align-items: center; padding: 3px; border: 1px solid #d9d3c9; border-radius: 10px; background: #f4f1ec; }
.language-toggle button { min-width: 62px; padding: 6px 10px; border: 0; border-radius: 7px; background: transparent; color: #667085; font: inherit; font-size: 12px; font-weight: 700; cursor: pointer; }
.language-toggle button.active { background: #fff; color: #132541; box-shadow: 0 1px 3px rgb(20 37 63 / 14%); }
.language-toggle button:focus-visible { outline: 2px solid #0f9184; outline-offset: 2px; }
.live-chip { padding: 6px 10px; border-radius: 999px; background: #e6f5ef; color: #14775d; font-size: var(--type-label); font-weight: 800; letter-spacing: .04em; }
.avatar { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 50%; background: #14233c; color: #fff; font-size: var(--type-label); font-weight: 800; }
.icon-button { display: grid; place-items: center; width: 44px; height: 44px; border: 1px solid #e5e0d7; border-radius: 10px; background: #fff; color: #5f6878; }
.icon-button:hover { color: #172033; background: #f7f5f0; }

.ops-main { min-height: calc(100vh - 66px); }
.page { width: min(1440px, 100%); margin: 0 auto; padding: 30px 32px 64px; }
.po-document-page { width: min(1584px, 100%); }
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

.button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 10px 16px; border: 1px solid transparent; border-radius: 10px; font-size: var(--type-body); font-weight: 700; line-height: 1.4; text-decoration: none; }
.button.primary { background: #14233c; color: #fff; }
.button.secondary { border-color: #ded9cf; background: #fff; color: #172033; }
.button.secondary:hover { background: #f9f8f5; border-color: #c8c1b5; }
.button.small { min-height: 36px; padding: 7px 12px; font-size: var(--type-label); }
.button.full { width: 100%; }
.button:disabled { opacity: .55; cursor: wait; }
.home-heading-actions { display: flex; align-items: center; gap: 10px; margin-left: auto; }

.group-grid, .book-grid, .manage-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.group-card, .book-card, .manage-card { min-width: 0; border: 1px solid #e2ddd4; border-radius: 16px; background: #fff; color: inherit; text-align: left; text-decoration: none; box-shadow: 0 7px 24px rgba(25,35,53,.04); transition: transform .14s ease, border-color .14s ease, box-shadow .14s ease; }
.group-card:hover, .book-card:hover, .manage-card:hover { transform: translateY(-2px); border-color: #c9c1b5; box-shadow: 0 12px 30px rgba(25,35,53,.08); }
.group-card { display: flex; flex-direction: column; min-height: 252px; padding: 20px; }
.group-card-head { display: flex; align-items: flex-start; gap: 12px; }
.group-code { display: grid; place-items: center; flex: 0 0 auto; width: 42px; height: 48px; border-radius: 6px 10px 10px 6px; color: #fff; box-shadow: inset 5px 0 rgba(0,0,0,.14); font-size: var(--type-label); font-weight: 900; }
.group-copy { min-width: 0; flex: 1; }
.group-copy strong, .group-copy small { display: block; }
.group-copy strong { font-size: var(--type-card-title); line-height: 1.35; }
.group-copy small { margin-top: 6px; color: var(--color-muted); font-size: var(--type-body); line-height: 1.45; }
.group-record-count { flex: 0 0 auto; padding: 5px 8px; border-radius: 999px; background: #f3f1ed; color: var(--color-muted); font-size: var(--type-label); font-weight: 700; white-space: nowrap; }
.book-shelf { display: flex; align-items: flex-end; gap: 7px; min-height: 90px; margin: auto 0 0; padding: 0 4px 8px; border-bottom: 7px solid #d7c9b8; }
.mini-book { display: flex; align-items: center; justify-content: center; flex: 1 1 0; width: auto; min-width: 0; max-width: 128px; min-height: 70px; padding: 7px 8px; border-radius: 3px 7px 3px 3px; color: #fff; box-shadow: inset 5px 0 rgba(0,0,0,.14); font-size: .6875rem; font-weight: 800; line-height: 1.35; overflow-wrap: anywhere; text-align: center; text-wrap: balance; white-space: normal; }
.is-tamil .mini-book { font-size: .71875rem; line-height: 1.5; }
.direct-card-rail { display: block; width: 100%; height: 7px; margin-top: auto; border-radius: 999px; opacity: .78; }
.group-card-foot, .book-open, .manage-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; color: var(--color-muted); font-size: var(--type-body); }
.group-card-foot strong, .book-open strong, .manage-foot strong { color: #2869a7; font-size: var(--type-body); }

.cover-po { background: #b94d3d; }
.cover-grn { background: #267c69; }
.cover-pi { background: #72568e; }
.cover-ipd { background: #b57b28; }
.cover-wo { background: #2869a7; }
.cover-woc { background: #9a6248; }
.cover-dc { background: #53727c; }
.cover-se { background: #356d78; }
.cover-inspection { background: #7a5b2e; }

.breadcrumbs { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-height: 32px; margin-bottom: 16px; color: var(--color-muted); font-size: var(--type-body); }
:deep(.breadcrumbs a) { display: inline-flex; align-items: center; min-height: 32px; padding: 4px 0; color: #2869a7; font-weight: 700; text-decoration: none; }
.book-identity { display: grid; place-items: center; flex: 0 0 auto; width: 56px; height: 66px; border-radius: 6px 12px 12px 6px; color: #fff; box-shadow: inset 7px 0 rgba(0,0,0,.14); font-size: var(--type-label); font-weight: 900; }
.book-identity.master-identity { background: #e8f1f9; color: #2869a7; box-shadow: none; }
.book-card { overflow: hidden; display: grid; grid-template-columns: 156px minmax(0, 1fr); min-height: 205px; }
.book-cover { position: relative; display: flex; flex-direction: column; justify-content: center; min-height: 205px; padding: 18px; color: #fff; box-shadow: inset 10px 0 rgba(0,0,0,.14); }
.book-cover small { margin-bottom: 10px; font-size: var(--type-label); font-weight: 800; letter-spacing: .1em; }
.book-cover strong { font-size: 1rem; line-height: 1.4; overflow-wrap: anywhere; text-wrap: balance; }
.book-spine { position: absolute; inset: 0 auto 0 11px; width: 1px; background: rgba(255,255,255,.22); }
.book-meta { padding: 22px 18px 10px; }
.book-meta strong, .book-meta small { display: block; }
.book-meta strong { font-size: 1rem; line-height: 1.4; }
.book-meta small { margin-top: 8px; color: var(--color-muted); font-size: var(--type-body); line-height: 1.5; }
.book-open { grid-column: 2; align-self: end; padding: 0 18px 18px; }

.manage-card { display: flex; flex-direction: column; min-height: 132px; padding: 17px 18px; }
.manage-card > strong { font-size: var(--type-card-title); line-height: 1.35; }
.manage-card > p { margin: 6px 0 12px; color: var(--color-muted); font-size: var(--type-body); line-height: 1.45; }
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
.linked-stack a, .linked-stack button { display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px; border: 1px solid #e2ddd4; border-radius: 10px; background: #faf9f7; color: #172033; text-align: left; text-decoration: none; }
.linked-stack button:disabled { cursor: default; opacity: .75; }
.linked-stack a > span:first-child, .linked-stack button > span:first-child { display: grid; place-items: center; width: 36px; height: 40px; border-radius: 7px; background: #e8f1f9; color: #2869a7; font-size: .6875rem; font-weight: 900; }
.linked-stack a span:nth-child(2), .linked-stack button span:nth-child(2) { min-width: 0; }
.linked-stack a strong, .linked-stack a small, .linked-stack button strong, .linked-stack button small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.linked-stack a strong, .linked-stack button strong { font-size: var(--type-body); }
.linked-stack a small, .linked-stack button small { margin-top: 2px; color: var(--color-muted); font-size: var(--type-label); }
.linked-stack a i, .linked-stack button i { margin-left: auto; color: #929aa7; }
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
	.language-toggle button { min-width: 52px; padding-inline: 7px; }
	.page { padding: 22px 16px 46px; }
	.home-heading, .page-heading { flex-wrap: wrap; }
	.home-heading > .button, .home-heading-actions, .heading-action, .heading-actions { width: 100%; margin-left: 0; }
	.home-heading-actions { flex-wrap: wrap; }
	.home-heading-actions .button { flex: 1; }
	.heading-actions .button { flex: 1; }
	.group-grid, .book-grid, .manage-grid { grid-template-columns: 1fr; }
	.group-card { min-height: 230px; }
	.book-card { grid-template-columns: 170px minmax(0, 1fr); }
	.toolbar { align-items: stretch; flex-direction: column; }
	.search-box { max-width: none; }
	.status-filters { margin-left: 0; }
	.record-count { text-align: left; }
	.desktop-list { display: none; }
	.mobile-list { display: grid; gap: 10px; }
	.mobile-row { display: block; width: 100%; padding: 14px; border: 1px solid #e2ddd4; border-radius: 12px; background: #fff; color: #172033; text-align: left; text-decoration: none; }
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
	.book-card { grid-template-columns: 150px minmax(0, 1fr); }
	.is-tamil .book-cover strong { font-size: .9375rem; }
	.book-cover { min-height: 190px; padding: 14px; }
	.book-meta { padding: 18px 14px 8px; }
	.book-open { padding: 0 14px 14px; }
}
</style>
