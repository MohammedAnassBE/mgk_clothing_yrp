/**
 * MGK Delivery Challan — source-driven Work Order dispatch.
 *
 * The operator chooses only the Work Order, dispatching location and quantities.
 * Receiver, warehouses, process/IPD context, rates and source references remain
 * derived values. The server is still authoritative for stock and pending limits.
 */
import { searchLink } from "@/api/client"

const linkSearchHandlers = {
	work_order: () => (q) => searchLink("Work Order", q, {
		docstatus: 1,
		open_status: ["!=", "Close"],
	}),
	from_location: () => (q) => searchLink("Supplier", q, { disabled: 0 }),
}

const labels = {
	from_location: "From Location",
	supplier: "To Location",
	supplier_name: "To Location Name",
	supplier_document_no: "Dispatch Document / DC No",
	comments: "Notes",
}

const help = {
	work_order: "Choose a submitted, open Work Order. Its pending deliverables and receiving location load automatically.",
	from_location: "Choose the location dispatching the goods. Its unique active linked Warehouse is applied automatically.",
	supplier_document_no: "Optional — enter the printed or manual Delivery Challan reference used for this dispatch.",
	vehicle_no: "Optional — enter the vehicle number used for this dispatch.",
	comments: "Optional — record handling instructions or other dispatch notes.",
}

const formOrder = [
	"work_order", "from_location",
	"supplier_document_no", "vehicle_no", "comments",
]

const formGroups = [
	{
		key: "dispatch-source",
		label: "Work Order and movement",
		fields: ["work_order", "from_location"],
	},
	{
		key: "dispatch-references",
		label: "Document and transport",
		fields: ["supplier_document_no", "vehicle_no", "comments"],
	},
]

const hideFormFields = [
	"naming_series", "is_rework", "posting_date", "posting_time",
	"edit_posting_date_and_time", "process_name", "item", "production_detail",
	"supplier", "from_warehouse", "to_warehouse", "purchase_order",
	"total_delivered_qty", "stock_value",
	"total_value", "is_internal_unit", "transfer_complete", "ste_transferred",
	"ste_transferred_percent", "amended_from",
]

export default {
	formOrder,
	formGroups,
	hideFormFields,
	linkSearchHandlers,
	labels,
	help,
}
