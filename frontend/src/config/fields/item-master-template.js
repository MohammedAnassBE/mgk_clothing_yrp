/**
 * Item Master Template — per-DocType field config consumed by DocDetail.vue.
 *
 * Mirrors item.js: the attributes child table's `mapping` Link renders
 * display-only so the user can't pick an existing shared Item Item Attribute
 * Mapping — the controller (`ItemMasterTemplate.validate` ->
 * `_ensure_attribute_mappings_exist`) auto-creates a fresh mapping per attribute
 * row on save. The Attribute Values editor (ItemAttributeListView, wired in
 * DocDetail for this doctype) then manages each mapping's values, exactly like
 * Item.
 */
const readOnlyChildFields = {
	"Item Item Attribute": ["mapping"],
}

export default {
	readOnlyChildFields,
}
