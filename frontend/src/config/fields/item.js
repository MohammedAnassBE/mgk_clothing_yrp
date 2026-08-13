/**
 * Item — per-DocType field config consumed by DocDetail.vue.
 *
 * `hideFormFields`: drop fields the user explicitly doesn't want surfaced
 * in the EDIT/CREATE form. weight_per_unit / weight_uom are tracked
 * elsewhere on this site and add noise here.
 *
 * The Attributes table's internal `mapping` link is always hidden. Base yrp's
 * `Item._ensure_attribute_mappings_exist` owns that link; MGK operators work
 * only with the human Attribute name and the focused Attribute Values editor.
 *
 * `boolLabels`: humanise the new `is_yarn_item` Check (desk-side addition,
 * 2026-06-18) so it reads as a clear yes/no on the form rather than the
 * raw "Is Yarn Item: No" double-take. The field is meta-driven, so it
 * renders automatically in EDIT/CREATE as a toggle; it is intentionally
 * NOT in hideFormFields so users can set it. IPD's `yarn_item` link search
 * filters on this flag (see config/fields/item-production-detail.js).
 */
const hideFormFields = [
	"weight_per_unit",
	"weight_uom",
]

const boolLabels = {
	is_yarn_item: { on: "Yarn item", off: "Not a yarn item" },
	mgk_is_karigan: { on: "Karigan item", off: "Not a Karigan item" },
	mgk_is_salavai_cone: { on: "Salavai Cone item", off: "Not a Salavai Cone item" },
}

export default {
	detailGroups: [
		{ label: "Item identity", fields: ["name1", "mgk_tamil_name", "item_group", "brand", "hsn_code", "disabled"] },
		{ label: "Stock and purchasing", fields: ["is_stock_item", "allow_negative_stock", "is_purchase_item", "is_sales_item", "over_delivery_receipt_allowance", "po_excess_allowed_percentage", "is_ineligible_for_itc"] },
		{ label: "Units and attributes", fields: ["default_unit_of_measure", "secondary_unit_of_measure", "primary_attribute", "dependent_attribute"] },
	],
	formOrder: [
		"name1", "mgk_tamil_name", "item_group", "brand", "hsn_code", "disabled",
		"is_stock_item", "allow_negative_stock", "is_purchase_item", "is_sales_item",
		"over_delivery_receipt_allowance", "po_excess_allowed_percentage", "is_ineligible_for_itc",
		"default_unit_of_measure", "secondary_unit_of_measure", "primary_attribute", "dependent_attribute",
	],
	formGroups: [
		{ label: "Item identity", fields: ["name1", "mgk_tamil_name", "item_group", "brand", "hsn_code", "disabled"] },
		{ label: "Stock and purchasing", fields: ["is_stock_item", "allow_negative_stock", "is_purchase_item", "is_sales_item", "over_delivery_receipt_allowance", "po_excess_allowed_percentage", "is_ineligible_for_itc"] },
		{ label: "Units and attributes", fields: ["default_unit_of_measure", "secondary_unit_of_measure", "primary_attribute", "dependent_attribute"] },
	],
	hideFormFields,
	hideChildTables: ["categories"],
	childColumnRules: {
		attributes: {
			mapping: () => true,
		},
	},
	boolLabels,
	labels: {
		name1: "Item name",
		mgk_tamil_name: "Item name (Tamil)",
		default_unit_of_measure: "Primary UOM",
		secondary_unit_of_measure: "Secondary UOM",
		over_delivery_receipt_allowance: "Delivery tolerance (%)",
		po_excess_allowed_percentage: "PO receipt excess (%)",
	},
	help: {
		mgk_tamil_name: "Enter the Tamil name shown throughout purchasing, production and stock screens.",
		item_group: "Choose the group that controls this Item's working behaviour.",
		default_unit_of_measure: "The unit used for normal purchasing and stock movement.",
		primary_attribute: "The main variant dimension, such as Size or Colour.",
		allow_negative_stock: "",
		po_excess_allowed_percentage: "",
		mgk_is_karigan: "",
		mgk_is_salavai_cone: "",
	},
}
