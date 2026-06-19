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
 *
 * `boolLabels`: humanise the new `is_yarn_item` Check (desk-side addition,
 * 2026-06-18) so it reads as a clear yes/no on the form rather than the
 * raw "Is Yarn Item: No" double-take. The field is meta-driven, so it
 * renders automatically in EDIT/CREATE as a toggle; it is intentionally
 * NOT in hideFormFields so users can set it. IPD's `yarn_item` link search
 * filters on this flag (see config/fields/item-production-detail.js).
 */
const hideFormFields = [
	"weight_per_unit",
	"weight_uom",
]

const readOnlyChildFields = {
	"Item Item Attribute": ["mapping"],
}

const boolLabels = {
	is_yarn_item: { on: "Yarn item", off: "Not a yarn item" },
}

export default {
	hideFormFields,
	readOnlyChildFields,
	boolLabels,
}
