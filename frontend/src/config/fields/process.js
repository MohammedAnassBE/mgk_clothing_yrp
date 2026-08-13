export default {
	detailGroups: [
		{
			label: "Process identity",
			fields: ["process_name", "is_yarn_process", "is_item_conversion", "is_group", "is_manual_entry_in_grn"],
		},
		{
			label: "Units and defaults",
			fields: [
				"input_uom", "output_uom", "default_wastage", "default_excess",
				"default_lead_time_days", "wo_excess_allowed_percentage",
			],
		},
	],
	formOrder: [
		"process_name", "is_yarn_process", "is_item_conversion", "is_group",
		"is_manual_entry_in_grn", "input_uom", "output_uom", "default_wastage",
		"default_excess", "default_lead_time_days", "wo_excess_allowed_percentage",
		"value_change_attributes", "process_details",
	],
	formGroups: [
		{
			label: "Process identity",
			fields: ["process_name", "is_yarn_process", "is_item_conversion", "is_group", "is_manual_entry_in_grn"],
		},
		{
			label: "Units and defaults",
			fields: [
				"input_uom", "output_uom", "default_wastage", "default_excess",
				"default_lead_time_days", "wo_excess_allowed_percentage",
			],
		},
		{ label: "Transformation", fields: ["value_change_attributes"] },
		{ label: "Sub-processes", fields: ["process_details"] },
	],
	labels: {
		is_yarn_process: "Yarn process",
		is_item_conversion: "Changes the Item",
		is_manual_entry_in_grn: "Allow manual GRN entry",
		wo_excess_allowed_percentage: "Work Order receipt excess allowed %",
	},
	help: {
		is_yarn_process: "Enable when this Process participates in the MGK yarn production route.",
		is_item_conversion: "Enable when the input Item becomes a different output Item.",
		value_change_attributes: "Choose attributes such as Colour whose values this Process may change.",
		wo_excess_allowed_percentage: "Maximum extra quantity allowed when receiving against a Work Order.",
	},
}
