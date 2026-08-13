/**
 * Inspection Entry — per-DocType field config consumed by DocDetail.vue.
 *
 * The base DocType supports GRN or Stock Entry. The MGK Registered Experience
 * deliberately exposes the client-approved GRN flow only: Against is seeded to
 * Goods Received Note and hidden; the operator chooses one submitted, non-rework
 * GRN and classifies its received rows.
 */
import { searchLink } from "@/api/client"

const linkSearchHandlers = {
	against_id: () => (q) => searchLink("Goods Received Note", q, {
		docstatus: 1,
		is_rework: 0,
	}),
}

export default {
	formOrder: ["against_id", "posting_date", "posting_time", "remarks"],
	formGroups: [
		{
			key: "inspection-source",
			label: "Goods Received Note",
			fields: ["against_id", "posting_date", "posting_time"],
		},
		{
			key: "inspection-notes",
			label: "Inspection notes",
			fields: ["remarks"],
		},
	],
	hideFormFields: ["against", "inspector", "status", "is_converted", "amended_from"],
	linkSearchHandlers,
	labels: {
		against_id: "Goods Received Note",
		remarks: "Inspection Notes",
	},
	help: {
		against_id: "Choose a submitted Goods Received Note. Its received rows load automatically below.",
		remarks: "Optional notes about this inspection or classification.",
	},
}
