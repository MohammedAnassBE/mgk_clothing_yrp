/**
 * Goods Received Note — per-DocType field config.
 *
 * Mirrors yrp's Supplier+Warehouse pair rule (conventions.md 2026-05-23 +
 * 2026-05-29). On GRN the from-side party is `supplier` (Sender) and the
 * to-side party is `delivery_location` (Receiver):
 *   from_warehouse → filtered by supplier
 *   to_warehouse   → filtered by delivery_location
 *
 * Returns null when the party is empty so the LinkField falls through to
 * listing all warehouses — the user can still pick freely.
 */
import { searchLink } from "@/api/client"

const linkSearchHandlers = {
	against_id: (form) =>
		form.against
			? (q) => searchLink(form.against, q, {
				docstatus: 1,
				open_status: ["!=", "Close"],
			})
			: null,
	from_warehouse: (form) =>
		form.supplier
			? (q) => searchLink("Warehouse", q, { supplier: form.supplier })
			: null,
	to_warehouse: (form) =>
		form.delivery_location
			? (q) => searchLink("Warehouse", q, { supplier: form.delivery_location })
			: null,
	delivery_challan: (form) =>
		form.against === "Work Order"
			? (q) => searchLink("Delivery Challan", q, {
				docstatus: 1,
				...(form.against_id ? { work_order: form.against_id } : {}),
			})
			: null,
}

// Q18: unify the vendor-party term ("Job-worker") with WO + DC. On a GRN the
// sender party is `supplier`; `delivery_location` is the receiving side.
const labels = {
	supplier: "Job-worker",
	against_id: "Source document",
	delivery_challan: "Delivery Challan / DC No",
	supplier_document_no: "Supplier DC / Document No",
	comments: "Notes",
}

// Q13: surface help on the pivotal Against selector (Desk hides its description
// from /web users) so a floor user knows what the choice drives.
const help = {
	against: "Receive against a Work Order (job-work return) or a Purchase Order (bought-in goods). This drives which items and quantities load below.",
	against_id: "Choose a submitted, open source. Its supplier, warehouses, pending items, rates and references load automatically.",
	delivery_challan: "Optional — select the submitted Delivery Challan whose goods are being returned against this Work Order.",
	supplier_document_no: "Optional — enter the supplier's printed DC, invoice or document reference number.",
	vehicle_no: "Optional — enter the vehicle number used for this receipt.",
	freight_charges: "Optional — enter the total freight charged for this receipt.",
	comments: "Optional — record receipt notes or handling instructions.",
}

const formOrder = [
	"against",
	"against_id",
	"delivery_challan",
	"posting_date",
	"posting_time",
	"edit_posting_date_and_time",
	"supplier",
	"from_warehouse",
	"to_warehouse",
	"supplier_document_no",
	"vehicle_no",
	"freight_charges",
	"comments",
]

const formGroups = [
	{
		key: "receipt-source",
		label: "Receipt source",
		fields: ["against_id", "delivery_challan"],
	},
	{
		key: "receipt-references",
		label: "Document and transport",
		fields: ["supplier_document_no", "vehicle_no", "freight_charges", "comments"],
	},
]

export default {
	formOrder,
	formGroups,
	linkSearchHandlers,
	labels,
	help,
}
