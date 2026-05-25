# Copyright (c) 2026, MGK Clothing and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from mgk_clothing_yrp.overrides.purchase_order import validate


class TestPurchaseOrderMGK(FrappeTestCase):
	def _po(self, **kwargs):
		# Built in-memory and never inserted, so no link/mandatory dependencies
		# are needed — we only exercise the routing guard in `validate`.
		return frappe.get_doc({"doctype": "Purchase Order", **kwargs})

	def test_through_vendor_without_handling_supplier_raises(self):
		doc = self._po(mgk_goods_routing="Through Vendor")
		with self.assertRaises(frappe.ValidationError):
			validate(doc)

	def test_through_vendor_with_handling_supplier_ok(self):
		doc = self._po(mgk_goods_routing="Through Vendor", mgk_handling_supplier="S-0001")
		validate(doc)  # must not raise

	def test_direct_routing_ok(self):
		doc = self._po(mgk_goods_routing="Direct")
		validate(doc)  # must not raise
