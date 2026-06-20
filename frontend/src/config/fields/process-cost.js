/**
 * Process Cost — SPA field config (self-contained; consumed directly by
 * DocDetail.vue, NOT registered in config/fields/index.js).
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
	childColumnRules: {
		process_cost_values: {
			// Hide the attribute-value column unless depends_on_attribute is set.
			attribute_value: (parent) => !parent?.depends_on_attribute,
		},
	},
}
