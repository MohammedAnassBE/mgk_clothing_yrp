"""mgk_clothing_yrp design-approval API for Work Order.

Role-gated approve/reject that stamps base-yrp's `approved_by`/`rejection_reason`
and appends to the `mgk_approval_log` child table. The role for a WO's
process is configured in MGK Settings.process_approval_roles (process_name -> approver_role).

The pure logic (_apply_approve / _apply_reject / _approval_state) is split out
from the get_doc/save wrappers so it is unit-testable on an in-memory doc.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime


def get_approver_role(process):
	"""Approver Role configured for this Process in MGK Settings, or None."""
	if not process:
		return None
	settings = frappe.get_single("MGK Settings")
	for row in settings.get("process_approval_roles") or []:
		if row.process_name == process:
			return row.approver_role
	return None


def _require_role(wo):
	role = get_approver_role(wo.process_name)
	if not role:
		frappe.throw(_("Process '{0}' is not configured for design approval in MGK Settings.").format(wo.process_name or ""))
	if role not in frappe.get_roles(frappe.session.user):
		frappe.throw(_("You need the '{0}' role to approve or reject this Work Order.").format(role))


def _append_log(wo, action, reason=None):
	wo.append("mgk_approval_log", {
		"action": action,
		"action_by": frappe.session.user,
		"action_at": now_datetime(),
		"reason": reason,
	})


def _apply_approve(wo):
	wo.approved_by = frappe.session.user
	wo.rejection_reason = None
	_append_log(wo, "Approved")


def _apply_reject(wo, reason):
	wo.rejection_reason = reason
	wo.approved_by = None
	_append_log(wo, "Rejected", reason)


def _approval_state(wo):
	role = get_approver_role(wo.process_name)
	return {
		"needs_approval": bool(role),
		"approver_role": role,
		"can_approve": bool(role) and role in frappe.get_roles(frappe.session.user),
		"approved_by": wo.approved_by,
		"rejection_reason": wo.rejection_reason,
		"docstatus": wo.docstatus,
	}


@frappe.whitelist()
def approve(work_order):
	wo = frappe.get_doc("Work Order", work_order)
	wo.check_permission("write")
	if wo.docstatus != 0:
		frappe.throw(_("Only a draft Work Order can be approved."))
	_require_role(wo)
	_apply_approve(wo)
	wo.save()
	return {"approved_by": wo.approved_by}


@frappe.whitelist()
def reject(work_order, reason):
	if not (reason and reason.strip()):
		frappe.throw(_("A reason is required to reject."))
	wo = frappe.get_doc("Work Order", work_order)
	wo.check_permission("write")
	if wo.docstatus != 0:
		frappe.throw(_("Only a draft Work Order can be rejected."))
	_require_role(wo)
	_apply_reject(wo, reason)
	wo.save()
	return {"rejection_reason": wo.rejection_reason}


@frappe.whitelist()
def get_approval_state(work_order):
	"""Everything the client needs to render the gate (role logic stays server-side)."""
	wo = frappe.get_doc("Work Order", work_order)
	wo.check_permission("read")
	return _approval_state(wo)
