"""In-/web editors for master and IPD-specific attribute mappings.

`ItemAttributeListView.vue` (mgk_clothing_yrp frontend) calls
`update_mapping_values` when the user finishes editing an attribute's value
list inline. Doing this server-side as a single unit avoids the timestamp
race that a multi-call frontend flow (insert each Item Attribute Value, then
PUT the parent) ran into — the parent's `modified` would change between the
last insert and the parent save.

The generic endpoint respects mapping permissions. The IPD endpoint resolves
the mapping exclusively through the owning Item Production Detail, requires
write access to that IPD, and never accepts an Item master mapping as its write
target.
"""

import json

import frappe
from frappe import _
from mgk_clothing_yrp.ipd_lock import assert_ipd_editable


@frappe.whitelist()
def update_mapping_values(mapping, attribute_name, values):
	"""Replace an Item Item Attribute Mapping's `values` table.

	`values` is a list of plain strings (the attribute values). For each
	value that has no backing Item Attribute Value doc, one is inserted
	first (so the child-table Link target resolves on the subsequent save).

	Returns the updated value list in the order it was persisted.
	"""
	if not mapping:
		frappe.throw(_("Mapping is required"))
	if not attribute_name:
		frappe.throw(_("Attribute name is required"))

	clean_values = _clean_values(values)
	_ensure_attribute_values(attribute_name, clean_values)
	return _replace_mapping_values(mapping, attribute_name, clean_values)


@frappe.whitelist()
def update_ipd_mapping_values(
	item_production_detail,
	attribute_name,
	values,
	mapping=None,
):
	"""Update one mapping owned by an Item Production Detail.

	Legacy MGK IPDs may still point at their Item's master mapping. In that case
	the IPD is saved once to clone its mappings before any values are written.
	"""
	if not item_production_detail:
		frappe.throw(_("Item Production Detail is required"))
	if not attribute_name:
		frappe.throw(_("Attribute name is required"))

	ipd = frappe.get_doc("Item Production Detail", item_production_detail)
	ipd.check_permission("write")
	assert_ipd_editable(ipd)
	row = next(
		(
			row
			for row in ipd.get("item_attributes") or []
			if row.get("attribute") == attribute_name
		),
		None,
	)
	if not row:
		frappe.throw(
			_("Attribute {0} is not configured on Item Production Detail {1}").format(
				attribute_name, item_production_detail
			)
		)
	if mapping and row.get("mapping") != mapping:
		frappe.throw(_("The attribute mapping changed. Reload and try again."))

	from mgk_clothing_yrp.yarn_process import ensure_ipd_attribute_mappings

	if ensure_ipd_attribute_mappings(ipd):
		ipd.save()
		row = next(
			row
			for row in ipd.get("item_attributes") or []
			if row.get("attribute") == attribute_name
		)

	# A second ownership check makes it impossible for a crafted request to use
	# this endpoint to mutate an Item master or another IPD's mapping.
	from mgk_clothing_yrp.yarn_process import _mapping_is_shared

	if _mapping_is_shared(row.get("mapping"), ipd.name):
		frappe.throw(_("The IPD attribute mapping is not isolated."))

	clean_values = _clean_values(values)
	_ensure_attribute_values(attribute_name, clean_values)
	return _replace_mapping_values(
		row.get("mapping"),
		attribute_name,
		clean_values,
		ignore_permissions=True,
	)


def _clean_values(values):
	if isinstance(values, str):
		try:
			values = json.loads(values)
		except (TypeError, ValueError):
			frappe.throw(_("Invalid `values` payload"))
	if not isinstance(values, list):
		frappe.throw(_("`values` must be a list"))

	# Deduplicate while preserving order — defensive; the frontend already
	# blocks duplicates client-side, but we don't trust the client alone.
	seen = set()
	clean_values = []
	for v in values:
		s = str(v or "").strip()
		if not s or s in seen:
			continue
		seen.add(s)
		clean_values.append(s)
	return clean_values


def _ensure_attribute_values(attribute_name, clean_values):
	# Ensure every value has a backing Item Attribute Value doc. Insert
	#    inside the same transaction so the subsequent mapping.save doesn't
	#    race with an external commit on the same Attribute Value records.
	for v in clean_values:
		if not frappe.db.exists("Item Attribute Value", v):
			frappe.get_doc(
				{
					"doctype": "Item Attribute Value",
					"attribute_name": attribute_name,
					"attribute_value": v,
				}
			).insert()



def _replace_mapping_values(
	mapping,
	attribute_name,
	clean_values,
	ignore_permissions=False,
):
	# Replace the mapping's child rows in one shot.
	doc = frappe.get_doc("Item Item Attribute Mapping", mapping)
	if doc.attribute_name != attribute_name:
		frappe.throw(
			_("Mapping {0} belongs to attribute {1}, not {2}.").format(
				doc.name, doc.attribute_name, attribute_name
			)
		)
	doc.set("values", [])
	for i, v in enumerate(clean_values, start=1):
		doc.append("values", {"attribute_value": v, "idx": i})
	doc.save(ignore_permissions=ignore_permissions)
	return {
		"name": doc.name,
		"attribute_name": doc.attribute_name,
		"values": [r.attribute_value for r in doc.values],
	}
