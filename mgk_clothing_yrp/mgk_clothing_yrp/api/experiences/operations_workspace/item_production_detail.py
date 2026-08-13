"""MGK Item Production Detail yarn-flow and approval actions."""

from __future__ import annotations

import frappe

from mgk_clothing_yrp.ipd_lock import (
	APPROVED,
	NOT_APPROVED,
	allow_approval_transition,
	assert_ipd_editable,
)
from mgk_clothing_yrp.yarn_process import (
	get_item_attribute_options,
	regenerate_process_matrices,
)


def _only_system_manager():
	if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
		frappe.throw(
			"Only a System Manager can approve or regenerate an Item Production Detail.",
			frappe.PermissionError,
		)


def _guard_not_modified(doc, modified):
	if modified and str(doc.modified) != str(modified):
		from frappe.exceptions import TimestampMismatchError

		raise TimestampMismatchError(
			"This Item Production Detail was modified after you opened it. Reload and try again."
		)


def _approval_state(doc):
	matrices = frappe.get_all(
		"IPD Process Matrix",
		filters={"ipd": doc.name, "docstatus": ["<", 2]},
		fields=["name", "process_name"],
		order_by="process_name asc, name asc",
	)
	can_manage = (
		frappe.session.user == "Administrator"
		or "System Manager" in frappe.get_roles()
	)
	return {
		"name": doc.name,
		"approval_status": doc.approval_status or NOT_APPROVED,
		"approved_by": doc.approved_by,
		"can_approve": can_manage,
		"can_regenerate": can_manage and doc.approval_status != APPROVED,
		"is_locked": doc.approval_status == APPROVED,
		"matrix_count": len(matrices),
		"matrices": matrices,
	}


@frappe.whitelist()
def get_entry_context():
	"""Return the small, permission-checked catalogue needed by the IPD editor.

	The document is still saved through Frappe's normal resource API, so the
	Item Production Detail controller and MGK ``before_validate`` hook remain
	authoritative. This endpoint only prevents the frontend from downloading
	whole Item and Process documents one by one.
	"""
	frappe.has_permission("Item Production Detail", ptype="read", throw=True)
	frappe.has_permission("Item", ptype="read", throw=True)
	frappe.has_permission("Process", ptype="read", throw=True)

	processes = frappe.get_list(
		"Process",
		filters={"is_yarn_process": 1, "is_group": 0},
		fields=["name", "is_item_conversion"],
		order_by="name asc",
		limit_page_length=0,
	)
	change_attributes = []
	if processes:
		change_attributes = frappe.get_all(
			"Process Value Change",
			filters={
				"parenttype": "Process",
				"parent": ["in", [row.name for row in processes]],
			},
			fields=["parent", "attribute"],
			order_by="parent asc, idx asc",
		)
	attributes_by_process = {}
	for row in change_attributes:
		attributes_by_process.setdefault(row.parent, []).append(row.attribute)
	for process in processes:
		process.value_change_attributes = attributes_by_process.get(process.name, [])

	yarn_items = []
	for row in frappe.get_list(
		"Item",
		filters={"is_yarn_item": 1, "disabled": 0},
		fields=["name", "default_unit_of_measure", "dependent_attribute"],
		order_by="name asc",
		limit_page_length=0,
	):
		# MGK's yarn transformation engine intentionally supports normal Item
		# attributes only. Do not offer an Item the authoritative validator will
		# reject later.
		if row.dependent_attribute:
			continue
		value_options = get_item_attribute_options(row.name)
		yarn_items.append(
			{
				"name": row.name,
				"uom": row.default_unit_of_measure,
				"attributes": list(value_options),
				"value_options": value_options,
				"colours": list(value_options.get("Colour") or []),
			}
		)

	return {"processes": processes, "yarn_items": yarn_items}


@frappe.whitelist()
def get_approval_state(name):
	doc = frappe.get_doc("Item Production Detail", name)
	doc.check_permission("read")
	return _approval_state(doc)


@frappe.whitelist()
def approve(name, modified=None):
	"""Approve one IPD and atomically compile its process matrices."""
	_only_system_manager()
	doc = frappe.get_doc("Item Production Detail", name)
	_guard_not_modified(doc, modified)
	assert_ipd_editable(doc)
	# Compile while the persisted IPD is still editable. If the following
	# approval save fails its timestamp check, the request transaction rolls the
	# matrix replacement back as well.
	regenerate_process_matrices(doc)
	doc.approval_status = APPROVED
	doc.approved_by = frappe.session.user
	with allow_approval_transition(doc.name, APPROVED):
		doc.save(ignore_permissions=True)
	return _approval_state(frappe.get_doc("Item Production Detail", name))


@frappe.whitelist()
def reject(name, modified=None):
	"""Return an approved IPD to Not Approved without deleting test matrices."""
	_only_system_manager()
	doc = frappe.get_doc("Item Production Detail", name)
	_guard_not_modified(doc, modified)
	doc.approval_status = NOT_APPROVED
	doc.approved_by = None
	with allow_approval_transition(doc.name, NOT_APPROVED):
		doc.save(ignore_permissions=True)
	return _approval_state(doc)


@frappe.whitelist()
def regenerate_matrix(name, modified=None):
	"""System Manager test action; does not alter approval status."""
	_only_system_manager()
	doc = frappe.get_doc("Item Production Detail", name)
	_guard_not_modified(doc, modified)
	doc.check_permission("read")
	assert_ipd_editable(doc)
	regenerate_process_matrices(doc)
	return _approval_state(frappe.get_doc("Item Production Detail", name))
