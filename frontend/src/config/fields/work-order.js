/**
 * Work Order — Details-tab field grid.
 *
 * Mirrors the curated field set shown in the approved mockup
 * (`custom ui/MGK_WEB.html`, WO detail) rather than dumping every meta field.
 * The approval state (`approved_by` / `rejection_reason`) is surfaced by the
 * WorkOrderApproval gate + side card, so it is intentionally omitted here.
 */
export default [
	{ fieldname: "production_detail", label: "Item Production Detail", type: "Link" },
	{ fieldname: "process_name", label: "Process", type: "Link" },
	{ fieldname: "item", label: "Item", type: "Link" },
	{ fieldname: "supplier", label: "Supplier (Job-worker)", type: "Link" },
	{ fieldname: "supplier_name", label: "Job-worker Name" },
	{ fieldname: "delivery_location", label: "Delivery Location", type: "Link" },
	{ fieldname: "parent_wo", label: "Parent WO", type: "Link" },
	{ fieldname: "total_quantity", label: "Total Quantity", type: "Float" },
	{ fieldname: "wo_date", label: "WO Date", type: "Date" },
	{ fieldname: "planned_start_date", label: "Planned Start", type: "Date" },
	{ fieldname: "planned_end_date", label: "Planned End", type: "Date" },
	{ fieldname: "expected_delivery_date", label: "Expected Delivery", type: "Date" },
	{ fieldname: "is_rework", label: "Is Rework", type: "Check" },
	{ fieldname: "rework_type", label: "Rework Type" },
	{ fieldname: "comments", label: "Comments", type: "Text" },
]
