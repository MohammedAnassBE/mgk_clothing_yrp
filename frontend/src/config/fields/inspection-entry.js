/**
 * Inspection Entry — per-DocType field config consumed by DocDetail.vue.
 *
 * `against_id` is a Dynamic Link controlled by `against` (Goods Received Note /
 * Stock Entry). The default name-search would list ALL records of the target
 * (including draft + rework GRNs), so we mirror the Desk `set_query`
 * (inspection_entry.js): only SUBMITTED sources; GRNs exclude rework; Stock
 * Entries must be Purpose = "Material Receipt". The factory closes over the live
 * `form`, so the filter re-evaluates when `against` changes.
 */
import { searchLink } from "@/api/client"

// No `against` chosen yet → no suggestions (the user must pick the source kind
// first, exactly like the Desk, which can't resolve the Dynamic Link target).
const emptyHandler = async () => []

const linkSearchHandlers = {
	against_id: (form) => {
		if (!form.against) return emptyHandler
		const filters = { docstatus: 1 }
		if (form.against === "Goods Received Note") filters.is_rework = 0
		else if (form.against === "Stock Entry") filters.purpose = "Material Receipt"
		return (q) => searchLink(form.against, q, filters)
	},
}

export default {
	linkSearchHandlers,
}
