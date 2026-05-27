/**
 * MGK Clothing — static DocType registry.
 *
 * Mirrors the finalized sidebar in `custom ui/MGK_WEB_PLAN.md` (8 groups,
 * 35 DocTypes) and the icon/label/slug choices in `custom ui/MGK_WEB.html`.
 * Used for: sidebar rendering, route → DocType resolution, submittable flags
 * (drives the All/Draft/Submitted/Cancelled tab strip) and the default list
 * columns each list view shows. No DB fetch — instant lookup.
 *
 * Route convention (matches the mockup's slugify): DocType label lowercased,
 * non-alphanumerics → "-". e.g. "Goods Received Note" → "goods-received-note".
 *
 * `listFields`: DEPRECATED as the column source (2026-05-26). DynamicListPage now
 * derives columns from the DocType meta (`in_list_view`) overlaid with the user's
 * `User Listview` choice, so these arrays + GENERIC_FIELDS are no longer read for
 * rendering (kept for now; prunable). The rest of this registry (route/label/icon/
 * group/submittable/dateTabs) is still authoritative.
 *
 * `roles`: sidebar-group role hint from the mockup. The sidebar additionally
 * hard-gates every item on live `canRead(doctype)` from frappe.boot, so this is
 * only a coarse grouping aid — real visibility is permission-driven.
 */

// Submittable transaction DocTypes — get the docstatus tab strip + the plain
// Submit/Cancel buttons on the detail page. NOTE: workflow-managed doctypes
// (see WORKFLOW below) are deliberately NOT listed here — they drive everything
// through workflow actions, not plain docstatus submit/cancel.
const SUBMITTABLE = new Set([
	"Work Order",
	"Production Order",
	"Delivery Challan",
	"Purchase Order",
	"Goods Received Note",
	"Purchase Invoice",
	"Debit",
	"Inspection Entry",
	"Stock Entry",
	"Stock Update",
	"Stock Reconciliation",
	"Stock Reservation Entry",
	// Plain-submittable (is_submittable=1, no workflow) — added 2026-05-27 so
	// their existing Submit/Cancel + docstatus tabs render on /web.
	"Bill Tracking",
	"Production Term",
	"Excel Sticker Print",
])

// Workflow-managed DocTypes → their ORDERED workflow_state values. These render
// transition-driven action buttons (WorkflowActions.vue) instead of plain
// Submit/Cancel, and a workflow-state tab strip on the list. Verified 2026-05-27:
// these are the only two active Workflows on mgk_yrp.site and both share the
// identical state set below. KEEP IN SYNC if MGK edits the Workflow states.
const WORKFLOW_STATES = ["Draft", "Approval Pending", "Approved", "Rejected", "Expired"]
const WORKFLOW = {
	"Process Cost": WORKFLOW_STATES,
	"Item Price": WORKFLOW_STATES,
}

// Workflow-state → PrimeVue Tag severity. Shared by the detail badge and the
// list Status column (both import this) so the two can't drift apart.
export const WORKFLOW_SEVERITY = {
	Approved: "success",
	Rejected: "danger",
	Expired: "danger",
	"Approval Pending": "warn",
	Draft: "warn",
}

function slugify(s) {
	return s
		.toLowerCase()
		.replace(/&/g, "")
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/(^-|-$)/g, "")
}

// Raw group definitions (order = sidebar order). Icons are primeicons names.
const GROUPS = [
	{
		group: "Procurement",
		roles: ["Purchase Manager", "System Manager"],
		items: [
			{ doctype: "Purchase Order", icon: "pi pi-upload", dateTabs: "po_date", listFields: [
				{ field: "supplier", label: "Supplier" },
				{ field: "po_date", label: "Date", type: "Date" },
				{ field: "grand_total", label: "Grand Total", type: "Currency" },
			] },
			{ doctype: "Goods Received Note", icon: "pi pi-plus-circle", dateTabs: "posting_date", listFields: [
				{ field: "supplier", label: "Supplier" },
				{ field: "delivery_challan", label: "Against DC" },
				{ field: "posting_date", label: "Posting", type: "Date" },
			] },
			{ doctype: "Purchase Invoice", icon: "pi pi-file", dateTabs: "posting_date" },
			{ doctype: "Bill Tracking", icon: "pi pi-indian-rupee" },
			{ doctype: "Debit", icon: "pi pi-minus-circle" },
		],
	},
	{
		group: "Production",
		roles: ["Production Manager", "System Manager"],
		items: [
			{ doctype: "Work Order", icon: "pi pi-bars", dateTabs: "wo_date", listFields: [
				{ field: "item", label: "Item" },
				{ field: "supplier", label: "Job-worker" },
				{ field: "process_name", label: "Process" },
				{ field: "wo_date", label: "WO Date", type: "Date" },
			] },
			{ doctype: "Production Order", icon: "pi pi-th-large", dateTabs: "posting_date" },
			{ doctype: "Delivery Challan", icon: "pi pi-send", dateTabs: "posting_date", listFields: [
				{ field: "work_order", label: "Work Order" },
				{ field: "supplier", label: "Job-worker" },
				{ field: "posting_date", label: "Posting", type: "Date" },
			] },
			{ doctype: "Item Production Detail", icon: "pi pi-table" },
		],
	},
	{
		group: "Stock",
		roles: ["Stock Manager", "System Manager"],
		items: [
			{ doctype: "Inspection Entry", icon: "pi pi-verified", dateTabs: "posting_date", listFields: [
				{ field: "against", label: "Against" },
				{ field: "inspector", label: "Inspector" },
				{ field: "posting_date", label: "Posting", type: "Date" },
			] },
			{ doctype: "Stock Entry", icon: "pi pi-sync", dateTabs: "posting_date" },
			{ doctype: "Stock Update", icon: "pi pi-replay" },
			{ doctype: "Stock Reconciliation", icon: "pi pi-check-square", dateTabs: "posting_date" },
			{ doctype: "Stock Reservation Entry", icon: "pi pi-circle" },
		],
	},
	{
		group: "Item Masters",
		roles: "*",
		items: [
			{ doctype: "Item", icon: "pi pi-box", listFields: [
				{ field: "name1", label: "Item Name" },
				{ field: "item_group", label: "Item Group" },
				{ field: "default_unit_of_measure", label: "UOM" },
			] },
			{ doctype: "Item Group", icon: "pi pi-sitemap" },
			{ doctype: "Item Category", icon: "pi pi-tag" },
			{ doctype: "Brand", icon: "pi pi-star" },
			{ doctype: "UOM", icon: "pi pi-arrows-h" },
			{ doctype: "Item Price", icon: "pi pi-indian-rupee" },
			{ doctype: "Tax Slab", icon: "pi pi-percentage" },
			{ doctype: "Item Master Template", icon: "pi pi-clone" },
		],
	},
	{
		group: "Parties",
		roles: "*",
		items: [
			{ doctype: "Supplier", icon: "pi pi-building" },
			{ doctype: "MGK Agent", icon: "pi pi-user" },
			{ doctype: "Vendor Bill Delivery Person", icon: "pi pi-id-card" },
			{ doctype: "Department", icon: "pi pi-th-large" },
		],
	},
	{
		group: "Process & Setup",
		roles: "*",
		items: [
			{ doctype: "Process", icon: "pi pi-cog" },
			{ doctype: "Process Cost", icon: "pi pi-indian-rupee" },
			{ doctype: "Production Term", icon: "pi pi-bolt" },
			{ doctype: "Received Type", icon: "pi pi-inbox" },
			{ doctype: "Warehouse", icon: "pi pi-warehouse" },
			{ doctype: "Holiday List", icon: "pi pi-calendar" },
			{ doctype: "Terms and Condition", icon: "pi pi-book" },
			// Workstation (erpnext) is NOT installed on mgk_yrp.site. Removed from the
			// registry 2026-05-27 — it was leaking into the sidebar for Administrator
			// (canRead is always true for admins) and its list page is meaningless here.
		],
	},
	{
		group: "Tools",
		roles: ["Purchase Manager", "Production Manager", "System Manager"],
		items: [{ doctype: "Excel Sticker Print", icon: "pi pi-print" }],
	},
]

// Flatten into a registry with derived route/label/isSubmittable.
const DOCTYPES = []
for (const g of GROUPS) {
	for (const it of g.items) {
		DOCTYPES.push({
			doctype: it.doctype,
			route: slugify(it.doctype),
			label: it.doctype,
			icon: it.icon,
			group: g.group,
			roles: g.roles,
			isSubmittable: SUBMITTABLE.has(it.doctype),
			isWorkflow: it.doctype in WORKFLOW,
			workflowStates: WORKFLOW[it.doctype] || null,
			dateTabs: it.dateTabs || null,
			listFields: it.listFields || null,
			note: it.note || null,
		})
	}
}

// Default columns for any DocType without an explicit listFields config.
export const GENERIC_FIELDS = [
	{ field: "modified", label: "Last Updated", type: "Datetime" },
]

export function getRegistryByRoute(slug) {
	return DOCTYPES.find((d) => d.route === slug) || null
}

export function getRegistryByDoctype(name) {
	return DOCTYPES.find((d) => d.doctype === name) || null
}

/**
 * Sidebar groups in declared order. The `filterFn(doctype)` lets the sidebar
 * drop items the user can't read (live perms). Home is injected separately.
 */
export function getSidebarGroups(filterFn = () => true) {
	return GROUPS.map((g) => ({
		group: g.group,
		items: DOCTYPES.filter(
			(d) => d.group === g.group && filterFn(d.doctype)
		),
	})).filter((g) => g.items.length > 0)
}

export { DOCTYPES, SUBMITTABLE, WORKFLOW }
