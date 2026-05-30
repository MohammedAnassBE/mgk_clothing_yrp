/**
 * Item — per-DocType field config consumed by DocDetail.vue.
 *
 * `hideFormFields`: drop fields the user explicitly doesn't want surfaced
 * in the EDIT/CREATE form. weight_per_unit / weight_uom are tracked
 * elsewhere on this site and add noise here.
 *
 * `readOnlyChildFields`: per-child-doctype field name set. Cells in those
 * columns render as display-only spans in the edit grid — used to prevent
 * the user from picking an existing shared mapping for the Attributes
 * table, since base yrp's `Item._ensure_attribute_mappings_exist`
 * auto-creates one on save.
 */
const hideFormFields = [
	"weight_per_unit",
	"weight_uom",
]

const readOnlyChildFields = {
	"Item Item Attribute": ["mapping"],
}

export default {
	hideFormFields,
	readOnlyChildFields,
}
