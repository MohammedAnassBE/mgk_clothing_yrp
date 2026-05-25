# Copyright (c) 2026, MGK Clothing and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from mgk_clothing_yrp.mgk_clothing_yrp.api.work_order import (
	_apply_approve,
	_apply_reject,
	_approval_state,
	get_approver_role,
)
from mgk_clothing_yrp.overrides.work_order import before_submit


def _configure_settings():
	# Dyeing Process + System Manager role both exist on the site.
	s = frappe.get_single("MGK Settings")
	s.set("process_approval_roles", [{"process_name": "Dyeing", "approver_role": "System Manager"}])
	s.save()


class TestWOApprovalConfig(FrappeTestCase):
	def setUp(self):
		_configure_settings()

	def test_configured_process_returns_role(self):
		self.assertEqual(get_approver_role("Dyeing"), "System Manager")

	def test_unconfigured_process_returns_none(self):
		self.assertIsNone(get_approver_role("Cutting"))

	def test_blank_process_returns_none(self):
		self.assertIsNone(get_approver_role(None))


class TestWOBeforeSubmitGate(FrappeTestCase):
	def setUp(self):
		_configure_settings()

	def _wo(self, **kwargs):
		# In-memory WO (never inserted) — exercises only the gate's field reads.
		return frappe.get_doc({"doctype": "Work Order", **kwargs})

	def test_configured_process_unapproved_blocks_submit(self):
		wo = self._wo(process_name="Dyeing")
		with self.assertRaises(frappe.ValidationError):
			before_submit(wo)

	def test_configured_process_approved_allows_submit(self):
		wo = self._wo(process_name="Dyeing", approved_by="Administrator")
		before_submit(wo)  # must not raise

	def test_unconfigured_process_allows_submit(self):
		wo = self._wo(process_name="Cutting")
		before_submit(wo)  # must not raise


class TestWOApplyActions(FrappeTestCase):
	def setUp(self):
		_configure_settings()

	def _wo(self, **kwargs):
		return frappe.get_doc({"doctype": "Work Order", **kwargs})

	def test_apply_approve_stamps_and_logs(self):
		wo = self._wo(process_name="Dyeing")
		_apply_approve(wo)
		self.assertEqual(wo.approved_by, frappe.session.user)
		self.assertIsNone(wo.rejection_reason)
		self.assertEqual(len(wo.get("mgk_approval_log")), 1)
		self.assertEqual(wo.mgk_approval_log[0].action, "Approved")

	def test_apply_reject_stamps_clears_approval_and_logs(self):
		wo = self._wo(process_name="Dyeing", approved_by="Administrator")
		_apply_reject(wo, "border design needs rework")
		self.assertEqual(wo.rejection_reason, "border design needs rework")
		self.assertFalse(wo.approved_by)
		self.assertEqual(len(wo.get("mgk_approval_log")), 1)
		row = wo.mgk_approval_log[0]
		self.assertEqual(row.action, "Rejected")
		self.assertEqual(row.reason, "border design needs rework")

	def test_state_can_approve_for_admin(self):
		wo = self._wo(process_name="Dyeing")
		st = _approval_state(wo)
		self.assertTrue(st["needs_approval"])
		self.assertTrue(st["can_approve"])  # Administrator holds System Manager

	def test_state_unconfigured_process_not_gated(self):
		wo = self._wo(process_name="Cutting")
		st = _approval_state(wo)
		self.assertFalse(st["needs_approval"])
		self.assertFalse(st["can_approve"])
