"""Grant MGK workflow roles authority over their operational masters."""

import frappe
from frappe.permissions import setup_custom_perms


RULES = (
	("Process", "Production Planner"),
	("Received Type", "Stock Manager"),
)


def _ensure_rule(doctype, role):
	if not frappe.db.exists("DocType", doctype) or not frappe.db.exists("Role", role):
		return

	# The first Custom DocPerm for a DocType replaces its standard permission
	# table, so copy every standard row before adding MGK's extra role.
	setup_custom_perms(doctype)
	filters = {
		"parent": doctype,
		"role": role,
		"permlevel": 0,
		"if_owner": 0,
	}
	values = {
		"read": 1,
		"write": 1,
		"create": 1,
		"select": 1,
		"report": 1,
	}
	name = frappe.db.get_value("Custom DocPerm", filters, "name")
	if name:
		frappe.db.set_value(
			"Custom DocPerm",
			name,
			values,
			update_modified=False,
		)
	else:
		frappe.get_doc(
			{
				"doctype": "Custom DocPerm",
				**filters,
				**values,
			}
		).insert(ignore_permissions=True)

	frappe.clear_cache(doctype=doctype)


def execute():
	for doctype, role in RULES:
		_ensure_rule(doctype, role)
