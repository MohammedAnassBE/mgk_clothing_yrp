/**
 * Work Order — per-DocType field config consumed by DocDetail.vue.
 *
 * Three concerns:
 *   • `detail`  — curated Details-tab list shown in VIEW mode (mirrors the
 *                 mockup in `custom ui/MGK_WEB.html`; tighter than meta order).
 *   • `formOrder` — exact field order for EDIT / CREATE mode. Mirrors the Desk
 *                 form so naming_series is the first user-facing input.
 *   • `hideFormFields` — fields the user explicitly does not want surfaced in
 *                 the form (e.g. `includes_packing` — packing is computed from
 *                 the Item context on MGK's floor).
 *   • `linkSearchHandlers` — per-Link-field custom search factories. Each
 *                 receives the reactive form object and returns either an async
 *                 `(query) => Array<{ name }>` (when a filter applies) or null
 *                 (fall through to the default name-like search). Used to
 *                 restrict the Address autocomplete to addresses belonging to
 *                 the selected party, the same way the Desk does.
 */
import { callMethod, searchAddressForParty } from "@/api/client"

// Curated VIEW Details grouping. Work Order's own DocType layout is a flat
// 26-field top section + several UNNAMED sections, so meta Section-Break
// grouping would render one giant card + repeated "More" cards. These named
// groups give it the same tidy multi-card Details tab as Delivery Challan.
// Fields not present / hidden / read-only-empty are dropped per-group by
// DocDetail; a group whose fields all drop is not rendered. JSON blobs and the
// *_details / *_name / amended_from noise are filtered globally, so they are
// intentionally omitted here.
const detailGroups = [
	{
		label: "Identity",
		fields: [
			"naming_series", "status", "is_rework", "rework_type",
			"item", "production_detail", "process_name", "parent_wo",
		],
	},
	{
		label: "Job-worker & Delivery",
		fields: [
			"supplier", "supplier_type", "supplier_address",
			"delivery_location", "delivery_address", "terms_and_condition",
		],
	},
	{
		label: "Schedule",
		fields: [
			"wo_date", "planned_start_date", "planned_end_date", "planned_quantity", "expected_delivery_date",
			"start_date", "end_date", "first_dc_date", "last_dc_date", "first_grn_date", "last_grn_date",
		],
	},
	{
		label: "Quantities",
		fields: [
			"total_quantity",
			"total_no_of_pieces_delivered", "total_no_of_pieces_received", "wo_colours",
		],
	},
	{
		label: "Status & Closure",
		fields: [
			"open_status", "is_delivered", "is_internal_unit", "includes_packing", "is_manual_entry",
			"close_reason", "close_other_reason", "close_remarks", "closed_by",
			"approved_by", "rejection_reason",
		],
	},
	{
		label: "Stock & Costing",
		fields: ["process_cost", "reduce_stock_entry", "update_stock_entry"],
	},
	{
		label: "Notes",
		fields: ["comments"],
	},
]

// Form-mode field order — every editable field listed in the order the Desk
// would render it. System-managed / depends_on-gated fields stay in the list
// so they appear in the right place if they ever become visible (e.g.
// supplier_type/rework_type when is_rework is on). Hidden + read-only-empty
// fields are filtered out downstream by DocDetail.
const formOrder = [
	"naming_series",
	"process_name",
	"production_detail",
	"item",
	"supplier",
	"supplier_name",
	"delivery_location",
	"delivery_location_name",
	"supplier_address",
	"supplier_address_details",
	"delivery_address",
	"delivery_address_details",
	"edit_wo_date",
	"wo_date",
	"planned_start_date",
	"planned_end_date",
	"planned_quantity",
	"expected_delivery_date",
	"parent_wo",
	"supplier_type",
	"rework_type",
	"terms_and_condition",
	"comments",
]

// The base Work Order has a large unnamed first section. The MGK Registered
// Experience groups the same fields around the operator's actual sequence.
// This is presentation only: field metadata, required rules and server-side
// validation remain authoritative.
const formGroups = [
	{
		label: "Work setup",
		fields: ["naming_series", "process_name", "production_detail", "item"],
	},
	{
		label: "Job-worker and delivery",
		fields: [
			"supplier", "supplier_name", "delivery_location", "delivery_location_name",
			"supplier_address", "supplier_address_details", "delivery_address", "delivery_address_details",
		],
	},
	{
		label: "Schedule and quantity",
		fields: [
			"edit_wo_date", "wo_date", "planned_start_date", "planned_end_date",
			"planned_quantity", "expected_delivery_date",
		],
	},
	{
		label: "Additional details",
		fields: ["parent_wo", "supplier_type", "rework_type", "terms_and_condition"],
	},
]

// Hide unconditionally in EDIT/CREATE:
// - includes_packing: user opted out (2026-05-29).
// - open_status / is_delivered / status: system-managed read-only fields
//   that have non-empty defaults ("Open" / 0 / "0"). The shared visibility
//   rule "read-only + empty → hide" wouldn't drop them (Check is never
//   "empty", and the strings are non-empty), so they'd leak into the New
//   WO form as disabled controls — distracting and against the U4 audit
//   intent. Listed here explicitly.
// - comments: dropped from the regular form-field grid so it can be re-rendered
//   as the VERY LAST element of the WO form — below the mgk_items grid and the
//   deliverables/receivables pivots (DocDetail renders a dedicated WO comments
//   block after all child tables). Mirrors the Desk's bottom-of-form placement.
const hideFormFields = [
	"is_rework",
	"includes_packing",
	"open_status",
	"is_delivered",
	"status",
	"comments",
]

// Empty-party handler used by the address fields below: returns no suggestions
// (instead of falling through to the default name-like search, which would
// list ALL addresses on the site and let the user assign a wrong-party
// address). Mirrors the Desk's "select party first" behaviour.
const emptyHandler = async () => []

const linkSearchHandlers = {
	production_detail: (form) =>
		form.process_name
			? async (query) => (
				await callMethod(
					"mgk_clothing_yrp.mgk_clothing_yrp.api.work_order.get_work_order_production_detail_options",
					{ process_name: form.process_name, txt: query || "" },
				)
			) || []
			: emptyHandler,
	supplier_address: (form) =>
		form.supplier
			? (q) => searchAddressForParty("Supplier", form.supplier, q)
			: emptyHandler,
	delivery_address: (form) =>
		form.delivery_location
			? (q) => searchAddressForParty("Supplier", form.delivery_location, q)
			: emptyHandler,
}

// Q18: unify the vendor party to ONE term across WO/DC/GRN. The Desk/meta calls
// it "Supplier"; on MGK's floor the party doing the job IS the job-worker.
const labels = {
	production_detail: "Item Production Detail",
	supplier: "Job-worker",
	supplier_name: "Job-worker Name",
	supplier_address: "Job-worker Address",
	supplier_address_details: "Job-worker Address Details",
}

const help = {
	process_name: "Choose the job-work process first. It controls which Production Details are available.",
	production_detail: "Choose the production route for this Work Order. The Item is filled automatically.",
	supplier: "Choose the job-worker who will perform this process.",
	delivery_location: "Choose where the processed goods must be returned.",
	planned_quantity: "Enter the quantity planned for this Work Order.",
}

export default {
	detailGroups,
	formOrder,
	formGroups,
	hideFormFields,
	linkSearchHandlers,
	labels,
	help,
}
