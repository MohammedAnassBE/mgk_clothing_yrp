/**
 * Purchase Order — per-DocType field config.
 *
 * The supplier is the party we purchase from; `delivery_warehouse` is our
 * receiving warehouse. Keep the warehouse search unscoped so users can pick any
 * readable warehouse instead of filtering it by supplier.
 */

/**
 * Purchase Order entry stays meta-driven, but its working fields are ordered
 * around the way MGK buys goods. Server-calculated status and totals remain out
 * of the editable form and appear after the document is saved.
 */
export default {
	formOrder: [
		"supplier",
		"po_date",
		"expected_delivery_date",
		"delivery_warehouse",
		"mgk_agent",
		"mgk_goods_routing",
		"mgk_handling_supplier",
		"mgk_is_karigan_order",
		"mgk_is_salavai_cone_order",
		"comments",
	],
	hideFormFields: [
		"naming_series",
		"supplier_name",
		"open_status",
		"status",
		"total_qty",
		"total_stock_qty",
		"total",
		"total_discount",
		"total_tax",
		"grand_total",
		"in_words",
		"terms_and_condition",
		"approved_by",
		"cancel_reason",
		"amended_from",
	],
	help: {
		supplier: "Select the supplier first. Active Item Prices are checked against this supplier.",
		delivery_warehouse: "The warehouse where the ordered goods will be received.",
		mgk_agent: "Select the MGK agent responsible for this order, when applicable.",
		mgk_goods_routing: "Choose whether goods come directly or through another handling supplier.",
		mgk_handling_supplier: "Required when Goods Routing is Through Vendor.",
	},
	boolLabels: {
		mgk_is_karigan_order: { on: "Karigan order", off: "Not a Karigan order" },
		mgk_is_salavai_cone_order: { on: "Salavai Cone order", off: "Not a Salavai Cone order" },
	},
}
