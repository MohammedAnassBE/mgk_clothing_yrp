export default {
	detailGroups: [
		{ label: "Receipt classification", fields: ["received_type_name", "is_default"] },
	],
	allowFormFields: ["received_type_name", "is_default"],
	formOrder: ["received_type_name", "is_default"],
	formGroups: [
		{ label: "Receipt classification", fields: ["received_type_name", "is_default"] },
	],
	labels: {
		received_type_name: "Received Type name",
		is_default: "Use as default",
	},
	help: {
		received_type_name: "The classification shown while receiving or inspecting stock.",
		is_default: "Use this classification automatically when no other Received Type is selected.",
	},
}
