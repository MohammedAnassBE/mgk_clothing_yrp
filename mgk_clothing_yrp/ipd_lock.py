"""Server-side immutability rules for approved MGK production details.

An approved Item Production Detail is a released production definition.  Its
parent fields, private attribute values, generated Process Matrices and BOM
combination mappings must all stay unchanged until a System Manager explicitly
rejects the approval.
"""

from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _


APPROVED = "Approved"
NOT_APPROVED = "Not Approved"
_TRANSITION_FLAG = "mgk_ipd_approval_transition"


def _locked_message(ipd_name):
	return _(
		"Item Production Detail {0} is Approved and locked. Reject its approval "
		"before changing the production details, attribute values, Process "
		"Matrices, or BOM combinations."
	).format(ipd_name)


def _transition_message(ipd_name):
	return _(
		"Use the Approve IPD or Reject Approval action to change the approval "
		"status of Item Production Detail {0}."
	).format(ipd_name)


def _is_allowed_transition(doc):
	return frappe.flags.get(_TRANSITION_FLAG) == (
		doc.name,
		doc.get("approval_status") or NOT_APPROVED,
	)


@contextmanager
def allow_approval_transition(ipd_name, target_status):
	"""Authorize one internal approval API save for this request only."""
	previous = frappe.flags.get(_TRANSITION_FLAG)
	frappe.flags[_TRANSITION_FLAG] = (ipd_name, target_status)
	try:
		yield
	finally:
		if previous is None:
			frappe.flags.pop(_TRANSITION_FLAG, None)
		else:
			frappe.flags[_TRANSITION_FLAG] = previous


def assert_ipd_editable(ipd, action=None):
	"""Throw when ``ipd`` is already approved in the database."""
	ipd_name = ipd.name if hasattr(ipd, "name") else ipd
	if not ipd_name:
		return
	status = frappe.db.get_value(
		"Item Production Detail", ipd_name, "approval_status"
	)
	if status == APPROVED:
		frappe.throw(_locked_message(ipd_name))


def validate_ipd_change(doc, method=None):
	"""Guard the parent document and its approval fields."""
	if doc.is_new():
		if (
			(doc.get("approval_status") or NOT_APPROVED) != NOT_APPROVED
			or doc.get("approved_by")
		):
			frappe.throw(_transition_message(doc.name or _("New IPD")))
		return

	stored = frappe.db.get_value(
		"Item Production Detail",
		doc.name,
		["approval_status", "approved_by"],
		as_dict=True,
	)
	if not stored:
		return

	stored_status = stored.approval_status or NOT_APPROVED
	new_status = doc.get("approval_status") or NOT_APPROVED
	approval_changed = (
		stored_status != new_status
		or (stored.approved_by or None) != (doc.get("approved_by") or None)
	)
	allowed_transition = _is_allowed_transition(doc)

	if approval_changed and not allowed_transition:
		frappe.throw(_transition_message(doc.name))
	if stored_status == APPROVED and not allowed_transition:
		frappe.throw(_locked_message(doc.name))


def validate_ipd_delete(doc, method=None):
	assert_ipd_editable(doc)


def _related_ipd_names(doc):
	if doc.doctype == "IPD Process Matrix":
		return [doc.get("ipd")] if doc.get("ipd") else []

	if doc.doctype == "Item BOM Attribute Mapping":
		return frappe.get_all(
			"Item BOM",
			filters={
				"attribute_mapping": doc.name,
				"parenttype": "Item Production Detail",
			},
			pluck="parent",
		)

	if doc.doctype == "Item Item Attribute Mapping":
		return frappe.get_all(
			"IPD Item Attribute",
			filters={
				"mapping": doc.name,
				"parenttype": "Item Production Detail",
			},
			pluck="parent",
		)

	return []


def validate_related_ipd_change(doc, method=None):
	"""Lock standalone records that form part of an approved IPD."""
	for ipd_name in set(_related_ipd_names(doc)):
		assert_ipd_editable(ipd_name)
