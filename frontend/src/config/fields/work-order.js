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
import { searchAddressForParty } from "@/api/client"

const detail = [
	{ fieldname: "production_detail", label: "Item Production Detail", type: "Link" },
	{ fieldname: "process_name", label: "Process", type: "Link" },
	{ fieldname: "item", label: "Item", type: "Link" },
	{ fieldname: "supplier", label: "Supplier (Job-worker)", type: "Link" },
	{ fieldname: "supplier_name", label: "Job-worker Name" },
	{ fieldname: "delivery_location", label: "Delivery Location", type: "Link" },
	{ fieldname: "delivery_location_name", label: "Delivery Location Name" },
	{ fieldname: "parent_wo", label: "Parent WO", type: "Link" },
	{ fieldname: "total_quantity", label: "Total Quantity", type: "Float" },
	{ fieldname: "wo_date", label: "WO Date", type: "Date" },
	{ fieldname: "planned_start_date", label: "Planned Start", type: "Date" },
	{ fieldname: "planned_end_date", label: "Planned End", type: "Date" },
	{ fieldname: "expected_delivery_date", label: "Expected Delivery", type: "Date" },
	{ fieldname: "is_rework", label: "Is Rework", type: "Check" },
	{ fieldname: "rework_type", label: "Rework Type" },
	{ fieldname: "supplier_address", label: "Supplier Address", type: "Link" },
	{ fieldname: "delivery_address", label: "Delivery Address", type: "Link" },
	{ fieldname: "comments", label: "Comments", type: "Text" },
]

// Form-mode field order — every editable field listed in the order the Desk
// would render it. System-managed / depends_on-gated fields stay in the list
// so they appear in the right place if they ever become visible (e.g.
// supplier_type/rework_type when is_rework is on). Hidden + read-only-empty
// fields are filtered out downstream by DocDetail.
const formOrder = [
	"naming_series",
	"edit_wo_date",
	"wo_date",
	"supplier",
	"supplier_name",
	"parent_wo",
	"process_name",
	"terms_and_condition",
	"item",
	"production_detail",
	"delivery_location",
	"delivery_location_name",
	"planned_start_date",
	"planned_end_date",
	"expected_delivery_date",
	"supplier_type",
	"rework_type",
	"supplier_address",
	"supplier_address_details",
	"delivery_address",
	"delivery_address_details",
	"planned_quantity",
	"comments",
]

// Hide unconditionally in EDIT/CREATE:
// - includes_packing: user opted out (2026-05-29).
// - open_status / is_delivered / status: system-managed read-only fields
//   that have non-empty defaults ("Open" / 0 / "0"). The shared visibility
//   rule "read-only + empty → hide" wouldn't drop them (Check is never
//   "empty", and the strings are non-empty), so they'd leak into the New
//   WO form as disabled controls — distracting and against the U4 audit
//   intent. Listed here explicitly.
const hideFormFields = [
	"includes_packing",
	"open_status",
	"is_delivered",
	"status",
]

// Empty-party handler used by the address fields below: returns no suggestions
// (instead of falling through to the default name-like search, which would
// list ALL addresses on the site and let the user assign a wrong-party
// address). Mirrors the Desk's "select party first" behaviour.
const emptyHandler = async () => []

const linkSearchHandlers = {
	supplier_address: (form) =>
		form.supplier
			? (q) => searchAddressForParty("Supplier", form.supplier, q)
			: emptyHandler,
	delivery_address: (form) =>
		form.delivery_location
			? (q) => searchAddressForParty("Supplier", form.delivery_location, q)
			: emptyHandler,
}

export default {
	detail,
	formOrder,
	hideFormFields,
	linkSearchHandlers,
}
