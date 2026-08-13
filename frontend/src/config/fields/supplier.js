export default {
	detailGroups: [
		{ label: "Supplier identity", fields: ["supplier_name", "mgk_tamil_name", "disabled", "is_company_location", "department"] },
		{ label: "Tax details", fields: ["gstin", "pan"] },
		{ label: "Default terms", fields: ["po_terms_and_condition", "wo_terms_and_condition"] },
	],
	formOrder: [
		"supplier_name", "mgk_tamil_name", "disabled", "is_company_location", "department",
		"gstin", "pan", "po_terms_and_condition", "wo_terms_and_condition",
	],
	formGroups: [
		{ label: "Supplier identity", fields: ["supplier_name", "mgk_tamil_name", "disabled", "is_company_location", "department"] },
		{ label: "Tax details", fields: ["gstin", "pan"] },
		{ label: "Default terms", fields: ["po_terms_and_condition", "wo_terms_and_condition"] },
	],
	hideFormFields: ["uid"],
	labels: {
		mgk_tamil_name: "Supplier name (Tamil)",
		gstin: "GSTIN / UIN",
		po_terms_and_condition: "Purchase Order terms",
		wo_terms_and_condition: "Work Order terms",
	},
	help: {
		supplier_name: "Use the familiar supplier or job-worker name.",
		mgk_tamil_name: "Enter the Tamil name exactly as operators should see it when Tamil is enabled.",
		is_company_location: "Enable only when this party represents an MGK-owned location.",
	},
}
