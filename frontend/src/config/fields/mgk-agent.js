export default {
	detailGroups: [
		{ label: "Agent identity", fields: ["agent_name", "mgk_tamil_name", "disabled"] },
		{ label: "Commission reference", fields: ["commission_terms"] },
	],
	formOrder: ["agent_name", "mgk_tamil_name", "disabled", "commission_terms"],
	formGroups: [
		{ label: "Agent identity", fields: ["agent_name", "mgk_tamil_name", "disabled"] },
		{ label: "Commission reference", fields: ["commission_terms"] },
	],
	help: {
		mgk_tamil_name: "Enter the Tamil agent name shown when Tamil display is enabled.",
		commission_terms: "Record the agreed informal commission reference for this agent.",
	},
}
