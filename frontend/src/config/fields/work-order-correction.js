/**
 * MGK Work Order Correction — one submitted/open Work Order plus manually
 * entered additional deliverables and/or receivables. The two movement grids
 * are rendered by DocDetail's grouped stock editor; this config owns only the
 * concise source/context fields around them.
 */
import { searchLink } from "@/api/client"

const linkSearchHandlers = {
	work_order: () => (query) => searchLink("Work Order", query, {
		docstatus: 1,
		open_status: ["!=", "Close"],
	}),
}

const formOrder = [
	"work_order", "correction_date", "reason",
	"process_name", "item", "production_detail", "supplier", "delivery_location",
	"wo_date", "supplier_address", "delivery_address",
]

const formGroups = [
	{
		key: "correction-source",
		label: "Correction details",
		fields: ["work_order", "correction_date", "reason"],
	},
	{
		key: "work-order-context",
		label: "Work Order context",
		fields: [
			"process_name", "item", "production_detail", "supplier", "delivery_location",
			"wo_date", "supplier_address", "delivery_address",
		],
	},
]

const hideFormFields = ["naming_series", "status", "amended_from"]

const labels = {
	supplier: "Job-worker",
	delivery_location: "Delivery Location",
	reason: "Correction Reason",
}

const help = {
	work_order: "Choose a submitted, open Work Order. Its process, Item and routing details load automatically.",
	reason: "Record why these extra deliverables or receivables are required.",
}

export default {
	formOrder,
	formGroups,
	hideFormFields,
	linkSearchHandlers,
	labels,
	help,
}
