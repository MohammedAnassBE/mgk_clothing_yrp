"""mgk_clothing_yrp Work Order before_submit design-approval gate.

If the WO's process is listed in MGK Settings.process_approval_roles, the WO
cannot be submitted until `approved_by` is set (stamped by the approve API).
Processes NOT listed in MGK Settings are unaffected and submit freely.
Wired via `doc_events["Work Order"]["before_submit"]` in hooks.py.
"""

import frappe
from frappe import _

from mgk_clothing_yrp.mgk_clothing_yrp.api.work_order import get_approver_role


def before_submit(doc, method=None):
	if get_approver_role(doc.process_name) and not doc.get("approved_by"):
		frappe.throw(
			_("Design approval is required for process '{0}' before this Work Order can be submitted. Ask the configured approver.").format(doc.process_name)
		)
