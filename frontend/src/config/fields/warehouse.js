export default {
	detailGroups: [
		{ label: "Warehouse identity", fields: ["name1", "mgk_tamil_name", "supplier", "disabled"] },
	],
	formOrder: ["name1", "mgk_tamil_name", "supplier", "disabled"],
	formGroups: [
		{ label: "Warehouse identity", fields: ["name1", "mgk_tamil_name", "supplier", "disabled"] },
	],
	labels: { name1: "Warehouse name", mgk_tamil_name: "Warehouse name (Tamil)", supplier: "Linked supplier" },
	help: {
		mgk_tamil_name: "Enter the Tamil name shown in warehouse Link fields and movement views.",
		supplier: "Select the supplier associated with this warehouse.",
	},
}
