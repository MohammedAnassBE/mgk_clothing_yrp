"""MGK-specific Delivery Challan routing rules."""

import frappe
from frappe import _


def before_validate(doc, method=None):
	"""Derive the hidden stock Warehouse from the operator's From Location.

	The MGK Registered Experience deliberately asks the floor operator for a
	business location, not an internal stock ledger field.  Re-resolving here is
	important: UI hiding is not authorization, and a direct API request must not
	be able to pair a location with an unrelated Warehouse.
	"""
	if not doc.work_order or not doc.from_location:
		return

	warehouses = frappe.get_all(
		"Warehouse",
		filters={"supplier": doc.from_location, "disabled": 0},
		pluck="name",
		limit=2,
	)
	if not warehouses:
		frappe.throw(
			_("Create one active Warehouse linked to From Location {0} before saving.").format(
				frappe.bold(doc.from_location)
			)
		)
	if len(warehouses) > 1:
		frappe.throw(
			_("From Location {0} has multiple active Warehouses. Keep exactly one active Warehouse linked to it.").format(
				frappe.bold(doc.from_location)
			)
		)

	doc.from_warehouse = warehouses[0]
