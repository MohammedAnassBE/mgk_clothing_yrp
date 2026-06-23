"""mgk_clothing_yrp customisations on yrp's `Purchase Order`.

Phase 1 (Greige Yarn procurement): when goods are routed "Through Vendor",
a handling supplier must be named. Server-side belt-and-braces alongside the
`mandatory_depends_on` on the `mgk_handling_supplier` Custom Field.

Wired via `doc_events["Purchase Order"]` in hooks.py.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt


def validate(doc, method=None):
	if doc.get("mgk_goods_routing") == "Through Vendor" and not doc.get("mgk_handling_supplier"):
		frappe.throw(_("Handling Supplier is required when Goods Routing is 'Through Vendor'."))


def before_submit(doc, method=None):
	validate_item_prices_exist(doc)


def validate_item_prices_exist(doc):
	from yrp.yrp.doctype.item_price.item_price import get_active_price

	rows_by_item = defaultdict(list)
	for row in doc.get("items") or []:
		if flt(row.get("qty")) <= 0:
			continue
		parent_item = frappe.get_cached_value("Item Variant", row.get("item_variant"), "item")
		if parent_item:
			rows_by_item[parent_item].append(row)

	missing = []
	for parent_item in sorted(rows_by_item):
		if not get_active_price(parent_item, doc.get("supplier"), raise_error=False):
			missing.append(parent_item)

	if missing:
		frappe.throw(
			_("Active Item Price is required before submitting this Purchase Order for: {0}").format(
				", ".join(missing)
			)
		)
