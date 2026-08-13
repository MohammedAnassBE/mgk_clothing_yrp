export default {
	detailGroups: [
		{ label: "Purchase price identity", fields: ["item_name", "supplier", "supplier_name", "uom"] },
		{ label: "Effective period", fields: ["from_date", "to_date", "workflow_state", "approved_by"] },
		{ label: "Rate rule", fields: ["depends_on_attribute", "attribute", "tax"] },
	],
	formOrder: [
		"item_name", "supplier", "uom", "from_date", "to_date",
		"depends_on_attribute", "attribute", "tax",
	],
	formGroups: [
		{ label: "Purchase price identity", fields: ["item_name", "supplier", "uom"] },
		{ label: "Effective period", fields: ["from_date", "to_date"] },
		{ label: "Rate rule", fields: ["depends_on_attribute", "attribute", "tax"] },
	],
	hideFormFields: ["supplier_name", "approved_by", "amended_from"],
	labels: {
		item_name: "Item",
		depends_on_attribute: "Different price by attribute",
		attribute: "Price attribute",
		tax: "Tax slab",
	},
	help: {
		supplier: "Leave blank only when the price applies without a supplier restriction.",
		from_date: "The price becomes active from this date after approval.",
		depends_on_attribute: "Enable when Colour, Size, or another Item attribute has different prices.",
	},
	childColumnRules: {
		item_price_values: {
			attribute_value: (parent) => !parent?.depends_on_attribute,
		},
	},
}
