from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from mgk_clothing_yrp.overrides.delivery_challan import before_validate


class TestMGKDeliveryChallan(FrappeTestCase):
	def test_from_warehouse_is_derived_from_selected_location(self):
		doc = SimpleNamespace(
			work_order="WO-TEST",
			from_location="SUP-LOCATION",
			from_warehouse="FORGED-WAREHOUSE",
		)
		with patch(
			"mgk_clothing_yrp.overrides.delivery_challan.frappe.get_all",
			return_value=["EXPECTED-WAREHOUSE"],
		):
			before_validate(doc)

		self.assertEqual(doc.from_warehouse, "EXPECTED-WAREHOUSE")

	def test_from_location_requires_one_active_warehouse(self):
		doc = SimpleNamespace(
			work_order="WO-TEST",
			from_location="SUP-LOCATION",
			from_warehouse=None,
		)
		for warehouses in ([], ["WH-1", "WH-2"]):
			with self.subTest(warehouses=warehouses), patch(
				"mgk_clothing_yrp.overrides.delivery_challan.frappe.get_all",
				return_value=warehouses,
			), self.assertRaises(frappe.ValidationError):
				before_validate(doc)
