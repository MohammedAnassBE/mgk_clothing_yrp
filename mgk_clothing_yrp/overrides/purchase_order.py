"""mgk_clothing_yrp customisations on yrp's `Purchase Order`.

Phase 1 (Greige Yarn procurement): when goods are routed "Through Vendor",
a handling supplier must be named. Server-side belt-and-braces alongside the
`mandatory_depends_on` on the `mgk_handling_supplier` Custom Field.

Wired via `doc_events["Purchase Order"]` in hooks.py.
"""

import frappe
from frappe import _


def before_validate(doc, method=None):
	"""MGK POs always inherit the configured stock Received Type.

	The value remains stored on each Purchase Order Item for downstream stock
	classification, but it is deliberately not a user decision in MGK's order
	entry workflow.
	"""
	default_received_type = frappe.db.get_single_value(
		"YRP Stock Settings", "default_received_type"
	)
	if not default_received_type:
		frappe.throw(
			_("Set Default Received Type in YRP Stock Settings before saving a Purchase Order.")
		)

	for row in doc.get("items") or []:
		row.received_type = default_received_type


def validate(doc, method=None):
	if doc.get("mgk_goods_routing") == "Through Vendor" and not doc.get("mgk_handling_supplier"):
		frappe.throw(_("Handling Supplier is required when Goods Routing is 'Through Vendor'."))

	_validate_book_classification(doc)


def _validate_book_classification(doc):
	"""Keep MGK book flags and the Item classifications consistent server-side."""
	is_karigan = bool(doc.get("mgk_is_karigan_order"))
	is_salavai = bool(doc.get("mgk_is_salavai_cone_order"))
	if is_karigan and is_salavai:
		frappe.throw(
			_("A Purchase Order cannot belong to both the Karigan and Salavai Cone books.")
		)

	variant_names = [row.item_variant for row in doc.get("items") or [] if row.item_variant]
	if not variant_names:
		return

	variant_items = {
		row.name: row.item
		for row in frappe.get_all(
			"Item Variant",
			filters={"name": ["in", variant_names]},
			fields=["name", "item"],
		)
	}
	parent_items = set(variant_items.values())
	item_classifications = {
		row.name: (bool(row.mgk_is_karigan), bool(row.mgk_is_salavai_cone))
		for row in frappe.get_all(
			"Item",
			filters={"name": ["in", list(parent_items)]},
			fields=["name", "mgk_is_karigan", "mgk_is_salavai_cone"],
		)
	}

	def is_allowed(item):
		karigan_item, salavai_item = item_classifications.get(item, (False, False))
		if is_karigan:
			return karigan_item
		if is_salavai:
			return salavai_item
		return not karigan_item and not salavai_item

	invalid = sorted(
		{
			variant_items.get(variant, variant)
			for variant in variant_names
			if not is_allowed(variant_items.get(variant))
		}
	)
	if invalid:
		if not is_karigan and not is_salavai:
			frappe.throw(
				_(
					"Classified Items cannot be added to an Other Order. "
					"Select the matching Karigan or Salavai Cone order type for: {0}"
				).format(", ".join(invalid))
			)

		book = _("Karigan") if is_karigan else _("Salavai Cone")
		frappe.throw(
			_("Only {0} Items are allowed in this Purchase Order. Invalid Item(s): {1}").format(
				book, ", ".join(invalid)
			)
		)
