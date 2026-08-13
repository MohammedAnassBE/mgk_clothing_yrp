/**
 * Process Cost — SPA field config registered through config/fields/index.js.
 *
 * Parent-aware child-table column hide. Desk hides the `attribute_value` column
 * of the `process_cost_values` grid unless the parent's `depends_on_attribute`
 * checkbox is ticked; the SPA's child-table columns are otherwise parent-state-
 * agnostic, so we declare that one rule here and let DocDetail apply it reactively
 * (the rule reads the live parent doc/form, so it re-evaluates as the checkbox
 * toggles).
 *
 * Shape consumed by DocDetail.childColumnHiddenBy():
 *   childColumnRules: {
 *     <childTableFieldname>: {
 *       <columnFieldname>: (parent) => boolean   // true ⇒ HIDE the column
 *     }
 *   }
 * `parent` is the live edit `form` (edit/create) or `doc.value` (view). Returning
 * `true` drops the column from BOTH the view DataTable and the edit grid.
 */
export default {
	doctype: "Process Cost",
	detailGroups: [
		{
			label: "Cost identity",
			fields: ["item", "uom", "process_name", "supplier", "supplier_name", "is_rework"],
		},
		{
			label: "Effective period",
			fields: ["from_date", "to_date", "is_expired", "workflow_state", "approved_by"],
		},
		{
			label: "Rate rule",
			fields: ["depends_on_attribute", "attribute", "tax_slab"],
		},
	],
	formOrder: [
		"item",
		"uom",
		"process_name",
		"supplier",
		"from_date",
		"to_date",
		"depends_on_attribute",
		"attribute",
		"tax_slab",
		"is_rework",
	],
	formGroups: [
		{ label: "Cost identity", fields: ["item", "uom", "process_name", "supplier", "is_rework"] },
		{ label: "Effective period", fields: ["from_date", "to_date"] },
		{ label: "Rate rule", fields: ["depends_on_attribute", "attribute", "tax_slab"] },
	],
	hideFormFields: ["is_expired", "approved_by", "supplier_name"],
	labels: {
		supplier: "Job-worker",
		process_name: "Process",
		depends_on_attribute: "Different rate by attribute",
		attribute: "Rate attribute",
		tax_slab: "Tax slab",
	},
	help: {
		item: "Choose the Item that will be received from this process.",
		process_name: "This cost is applied only to Work Orders for this process.",
		supplier: "Choose the job-worker whose Work Orders will use this rate.",
		from_date: "The rate becomes active from this date after approval.",
		depends_on_attribute: "Enable when Colour, Size, or another Item attribute has different rates.",
		attribute: "Selecting an attribute fills one rate row for each available value.",
	},
	childColumnRules: {
		process_cost_values: {
			// Hide the attribute-value column unless depends_on_attribute is set.
			attribute_value: (parent) => !parent?.depends_on_attribute,
		},
	},
}
