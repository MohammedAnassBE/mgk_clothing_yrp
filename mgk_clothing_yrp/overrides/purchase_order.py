"""mgk_clothing_yrp customisations on yrp's `Purchase Order`.

Phase 1 (Greige Yarn procurement): when goods are routed "Through Vendor",
a handling supplier must be named. Server-side belt-and-braces alongside the
`mandatory_depends_on` on the `mgk_handling_supplier` Custom Field.

Wired via `doc_events["Purchase Order"]["validate"]` in hooks.py.
"""

import frappe
from frappe import _


def validate(doc, method=None):
	if doc.get("mgk_goods_routing") == "Through Vendor" and not doc.get("mgk_handling_supplier"):
		frappe.throw(_("Handling Supplier is required when Goods Routing is 'Through Vendor'."))
