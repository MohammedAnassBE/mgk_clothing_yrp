/**
 * MGK Stock Entry — a purpose-led writing surface.
 *
 * Base YRP owns the Stock Entry controller, stock dimensions, valuation, transit
 * rules and ledger posting. This config only presents those fields in the order
 * an operator works: purpose/date, movement, items, then optional references.
 */
import { searchLink } from "@/api/client"

const linkSearchHandlers = {
	from_warehouse: (form) =>
		form.from_supplier
			? (q) => searchLink("Warehouse", q, { supplier: form.from_supplier, disabled: 0 })
			: (q) => searchLink("Warehouse", q, { disabled: 0 }),
	to_warehouse: (form) =>
		form.to_supplier
			? (q) => searchLink("Warehouse", q, { supplier: form.to_supplier, disabled: 0 })
			: (q) => searchLink("Warehouse", q, { disabled: 0 }),
}

export default {
	formOrder: [
		"purpose",
		"posting_date",
		"posting_time",
		"edit_posting_date_and_time",
		"from_supplier",
		"from_warehouse",
		"to_supplier",
		"to_warehouse",
		"skip_transit",
		"vehicle_no",
		"additional_amount",
		"comments",
	],
	formGroups: [
		{
			key: "movement-type",
			label: "Movement type and date",
			fields: ["purpose", "posting_date", "posting_time", "edit_posting_date_and_time"],
		},
		{
			key: "movement-route",
			label: "Source and destination",
			fields: [
				"from_supplier", "from_warehouse", "to_supplier", "to_warehouse",
				"skip_transit",
			],
		},
		{
			key: "movement-notes",
			label: "Transport and notes",
			fields: ["vehicle_no", "additional_amount", "comments"],
		},
	],
	hideFormFields: [
		"naming_series", "terms_and_condition", "against", "against_id",
		"total_amount", "per_transferred", "amended_from",
	],
	linkSearchHandlers,
	labels: {
		from_supplier: "From Location",
		from_warehouse: "From Warehouse",
		to_supplier: "To Location",
		to_warehouse: "To Warehouse",
		additional_amount: "Additional Transfer Cost",
		comments: "Notes",
	},
	help: {
		purpose: "Choose what happens to the stock. The source and destination fields change automatically.",
		from_supplier: "Optional location filter. The From Warehouse list is narrowed to this location.",
		from_warehouse: "Warehouse from which stock will be reduced.",
		to_supplier: "Optional location filter. The To Warehouse list is narrowed to this location.",
		to_warehouse: "Warehouse into which stock will be received.",
		skip_transit: "For Send to Warehouse, post directly to the target instead of keeping stock in transit.",
		additional_amount: "Optional cost added while sending stock to another warehouse.",
		vehicle_no: "Optional vehicle reference for this movement.",
		comments: "Optional movement or handling instructions.",
	},
}
