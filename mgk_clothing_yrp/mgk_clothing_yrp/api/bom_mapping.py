"""Create / configure Item BOM Attribute Mapping docs from the /web IPD surface.

`BOMMappingEditor.vue` and `IPDConfigView.openMapping` drive the standalone
(non-submittable) **Item BOM Attribute Mapping** doctype, which the IPD engine
reads in "Mode B" to resolve per-variant BOM quantities. The editor builds its
grid columns from the mapping's own `item_attributes` / `bom_item_attributes`
child tables — so those MUST be populated when the mapping is created, or the
grid renders empty ("no item-side attributes to map").

This starts from production_api's
`item_production_detail.ItemProductionDetail.update_mapping_values` pattern but
uses YRP's full `Item Production Detail.item_attributes` table for the produced
side. Every listed IPD attribute must drive the mapping's finished-item
combinations: a BOM quantity can differ for Size + Colour, not only for the
primary attribute. The BOM side still comes from every attribute on the
consumed Item. YRP's mapping doctype also dropped production_api's
`item_production_detail` link field, so we don't set it — the owning IPD is
recovered (when needed) via the Item BOM child row that back-links the mapping.

Permission model: these run as standalone whitelisted endpoints reachable by any
logged-in /web user, so — unlike production_api, which calls update_mapping_values
from inside the already-permission-gated IPD controller save — we DO NOT pass
`ignore_permissions`. Standard "Item BOM Attribute Mapping" create/write perms
apply (same roles as the sibling editor api/item_attribute.py: System Manager,
Item Master Manager, Production Planner, Merch User). `flags.ignore_validate` is
still set (as the reference does) — that only skips the *values-completeness*
check on a freshly-seeded doc with no `values` yet; it does not bypass perms.
"""

import frappe
from frappe import _
from mgk_clothing_yrp.ipd_lock import assert_ipd_editable
from yrp.yrp.doctype.item.item import (
	get_attribute_values as get_item_attribute_values,
)


def _bom_item_attribute_rows(bom_item):
	"""[{attribute: a}] for every attribute on the BOM (consumed) Item.

	Mirror production_api: `for item in frappe.get_cached_doc("Item", bom.item).attributes`.
	"""
	if not bom_item:
		return []
	item_doc = frappe.get_cached_doc("Item", bom_item)
	return [{"attribute": a.attribute} for a in (item_doc.attributes or [])]


def _ipd_item_attributes(ipd_doc):
	"""Return the ordered, unique attributes configured on an IPD."""
	attributes = []
	for row in ipd_doc.get("item_attributes") or []:
		attribute = row.get("attribute")
		if attribute and attribute not in attributes:
			attributes.append(attribute)
	if not attributes:
		frappe.throw(
			_("Add Item Attributes to Item Production Detail {0} first.").format(
				ipd_doc.name
			)
		)
	return attributes


def _ipd_item_attribute_values(ipd_doc):
	"""Return values from the IPD-owned mappings, with Item fallback.

	MGK clones Item attribute mappings for each IPD so the operator can narrow
	values without changing the Item master. The popup must therefore read the
	child row's mapping first rather than rebuilding combinations from Item data.
	"""
	result = {}
	fallback_attributes = []
	for row in ipd_doc.get("item_attributes") or []:
		attribute = row.get("attribute")
		if not attribute:
			continue
		if row.get("mapping"):
			mapping_doc = frappe.get_cached_doc(
				"Item Item Attribute Mapping", row.mapping
			)
			result[attribute] = [
				value.attribute_value for value in mapping_doc.get("values") or []
			]
		else:
			fallback_attributes.append(attribute)
	if fallback_attributes:
		result.update(
			get_item_attribute_values(ipd_doc.item, fallback_attributes) or {}
		)
	return result


def _seed_columns(doc, item_attributes, bom_item):
	"""Populate the mapping's attribute child tables in place (no save).

	item-side = every attribute listed on the owning IPD; bom-side = all BOM Item
	attributes. Leaves `values` untouched. Throws if the BOM Item has no
	attributes (an attribute-mapped BOM row is meaningless without them — better
	a clear message than a dead-end "nothing to map" grid).
	"""
	bom_rows = _bom_item_attribute_rows(bom_item)
	if not bom_rows:
		frappe.throw(
			_("BOM Item {0} has no attributes — it can't be attribute-mapped.").format(bom_item)
		)
	doc.set(
		"item_attributes",
		[{"attribute": attribute} for attribute in item_attributes],
	)
	doc.set("bom_item_attributes", bom_rows)


def _find_bom_row(ipd_doc, bom_row):
	if not bom_row:
		return None
	for row in ipd_doc.get("item_bom") or []:
		if row.name == bom_row:
			return row
	frappe.throw(
		_("BOM row {0} does not belong to Item Production Detail {1}.").format(
			bom_row, ipd_doc.name
		)
	)


@frappe.whitelist()
def create_mapping(ipd, bom_item=None, bom_row=None):
	"""Create an Item BOM Attribute Mapping for an attribute-mapped BOM row.

	`ipd` is the owning Item Production Detail name (gives us `item` + its full
	`item_attributes` table); `bom_item` is the consumed Item; `bom_row` is the
	Item BOM child-row name to back-link (optional). Returns the mapping name.

	Idempotent + transactional: if `bom_row` already links a mapping, that name
	is returned without creating a duplicate; otherwise the insert AND the
	back-link write happen in this one request, so a failure rolls both back
	(no orphaned, never-linked mapping). Faithful port of production_api's
	update_mapping_values create branch.
	"""
	if not ipd:
		frappe.throw(_("IPD is required"))
	ipd_doc = frappe.get_doc("Item Production Detail", ipd)
	ipd_doc.check_permission("write")
	assert_ipd_editable(ipd_doc)
	row = _find_bom_row(ipd_doc, bom_row)
	if row:
		# The parent child row is the authoritative context. Never trust a client
		# supplied Item that can point the popup at a different BOM Item.
		bom_item = row.item
	if not bom_item:
		frappe.throw(_("BOM Item is required"))

	# Idempotency: never create a second mapping for a row that already has one.
	if row and row.attribute_mapping:
		existing_doc = frappe.get_doc(
			"Item BOM Attribute Mapping", row.attribute_mapping
		)
		existing_doc.check_permission("write")
		if existing_doc.bom_item != bom_item or existing_doc.item != ipd_doc.item:
			frappe.throw(
				_("The existing BOM mapping does not match this IPD BOM row.")
			)
		if not row.based_on_attribute_mapping:
			row.based_on_attribute_mapping = 1
			ipd_doc.save()
		return existing_doc.name

	item_attributes = _ipd_item_attributes(ipd_doc)

	doc = frappe.new_doc("Item BOM Attribute Mapping")
	doc.item = ipd_doc.item
	doc.bom_item = bom_item
	_seed_columns(doc, item_attributes, bom_item)
	doc.flags.ignore_validate = True
	doc.insert()

	# Back-link through the parent document so child-table ownership, idx and
	# validation remain authoritative. This also enables Mode B automatically:
	# the operator's "Manage combinations" action is the explicit opt-in.
	if row:
		row.based_on_attribute_mapping = 1
		row.attribute_mapping = doc.name
		ipd_doc.save()
	return doc.name


def _owning_ipd(mapping_name):
	"""Return the IPD whose Item BOM row links this mapping, if any."""
	rows = frappe.get_all(
		"Item BOM",
		filters={"attribute_mapping": mapping_name, "parenttype": "Item Production Detail"},
		fields=["parent"],
		limit=1,
	)
	if not rows:
		return None
	return frappe.get_doc("Item Production Detail", rows[0].parent)


@frappe.whitelist()
def get_mapping_context(mapping):
	"""Return the owning IPD and its ordered finished-item attributes.

	Child-table list queries are not a reliable public client API in Frappe. The
	embedded editor uses this permission-checked endpoint to expand legacy
	primary-only mappings in memory before the operator saves them.
	"""
	if not mapping:
		frappe.throw(_("Mapping is required"))
	mapping_doc = frappe.get_doc("Item BOM Attribute Mapping", mapping)
	mapping_doc.check_permission("read")
	ipd_doc = _owning_ipd(mapping)
	if not ipd_doc:
		return {"ipd": None, "item": mapping_doc.item, "item_attributes": []}
	ipd_doc.check_permission("read")
	return {
		"ipd": ipd_doc.name,
		"item": ipd_doc.item,
		"item_attributes": _ipd_item_attributes(ipd_doc),
		"item_attribute_values": _ipd_item_attribute_values(ipd_doc),
	}


@frappe.whitelist()
def configure_columns(mapping):
	"""Heal an existing mapping whose attribute columns were never populated.

	Idempotent: if `item_attributes` already has rows, returns unchanged. Else
	derives item-side = all attributes listed on the owning IPD, bom-side = BOM Item
	attributes, and saves. Used by the editor's empty-state "Configure columns"
	action so a mapping created before this fix (or in Desk without columns)
	becomes usable in /web without a Desk visit.
	"""
	if not mapping:
		frappe.throw(_("Mapping is required"))
	doc = frappe.get_doc("Item BOM Attribute Mapping", mapping)
	if doc.item_attributes:
		return {"name": doc.name, "changed": False}

	ipd_doc = _owning_ipd(mapping)
	if not ipd_doc:
		frappe.throw(
			_(
				"Cannot determine the item-side attributes because no IPD links this mapping."
			)
		)
	if not doc.bom_item:
		frappe.throw(_("This mapping has no BOM Item set."))
	assert_ipd_editable(ipd_doc)

	_seed_columns(doc, _ipd_item_attributes(ipd_doc), doc.bom_item)
	doc.flags.ignore_validate = True
	doc.save()
	return {"name": doc.name, "changed": True}
