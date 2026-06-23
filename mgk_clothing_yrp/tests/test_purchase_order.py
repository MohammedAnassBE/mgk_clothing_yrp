# Copyright (c) 2026, MGK Clothing and contributors
# See license.txt

import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase

from mgk_clothing_yrp.overrides.purchase_order import before_submit, validate


class TestPurchaseOrderMGK(FrappeTestCase):
	def _po(self, **kwargs):
		# Built in-memory and never inserted, so no link/mandatory dependencies
		# are needed — we only exercise the routing guard in `validate`.
		return frappe.get_doc({"doctype": "Purchase Order", **kwargs})

	def _po_with_item(self, item_variant="ITEM-VARIANT-1"):
		return self._po(
			supplier="S-0001",
			items=[
				{
					"doctype": "Purchase Order Item",
					"idx": 1,
					"item_variant": item_variant,
					"qty": 1,
				}
			]
		)

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

	def test_item_price_check_does_not_run_on_save_validate(self):
		doc = self._po_with_item()
		validate(doc)  # must not raise

	def test_item_price_required_before_submit(self):
		doc = self._po_with_item()
		with (
			patch("frappe.get_cached_value", return_value="ITEM-1"),
			patch("yrp.yrp.doctype.item_price.item_price.get_active_price", return_value=None),
			self.assertRaisesRegex(frappe.ValidationError, "Active Item Price is required"),
		):
			before_submit(doc)
