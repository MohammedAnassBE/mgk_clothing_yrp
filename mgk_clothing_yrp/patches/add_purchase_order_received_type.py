"""Create MGK's hidden PO Received Type field and backfill existing rows."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


FIELD_DEFINITION = {
	"fieldname": "received_type",
	"fieldtype": "Link",
	"label": "Received Type",
	"options": "Received Type",
	"insert_after": "item",
	"reqd": 0,
	"hidden": 1,
	"module": "MGK Clothing YRP",
	"description": "Set automatically from YRP Stock Settings for MGK Purchase Orders.",
}


def execute():
	if not frappe.db.exists("DocType", "Purchase Order Item"):
		return

	create_custom_fields(
		{"Purchase Order Item": [FIELD_DEFINITION]},
		update=True,
	)
	frappe.clear_cache(doctype="Purchase Order Item")

	default_received_type = frappe.db.get_single_value(
		"YRP Stock Settings", "default_received_type"
	)
	if not default_received_type:
		return

	frappe.db.sql(
		"""
		UPDATE `tabPurchase Order Item`
		SET received_type = %s
		WHERE received_type IS NULL OR received_type = ''
		""",
		default_received_type,
	)
