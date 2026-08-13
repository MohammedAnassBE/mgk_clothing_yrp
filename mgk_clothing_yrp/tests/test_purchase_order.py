# Copyright (c) 2026, MGK Clothing and contributors
# See license.txt

import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase

from mgk_clothing_yrp.mgk_clothing_yrp.api import purchase_order as purchase_order_api
from mgk_clothing_yrp.overrides.item import validate as validate_item
from mgk_clothing_yrp.overrides.purchase_order import (
	_validate_book_classification,
	before_validate,
	validate,
)


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

	def test_received_type_is_forced_from_settings(self):
		doc = self._po_with_item()
		doc.items[0].received_type = "Rejected"

		with patch.object(
			frappe.db,
			"get_single_value",
			return_value="Accepted",
		):
			before_validate(doc)

		self.assertEqual(doc.items[0].received_type, "Accepted")

	def test_item_cannot_have_both_book_classifications(self):
		item = frappe._dict(mgk_is_karigan=1, mgk_is_salavai_cone=1)
		with self.assertRaises(frappe.ValidationError):
			validate_item(item)

	def test_purchase_order_cannot_have_both_book_classifications(self):
		doc = self._po(mgk_is_karigan_order=1, mgk_is_salavai_cone_order=1)
		with self.assertRaises(frappe.ValidationError):
			_validate_book_classification(doc)

	def test_karigan_order_accepts_only_karigan_items(self):
		doc = self._po_with_item("VARIANT-1")
		doc.mgk_is_karigan_order = 1
		doc.mgk_is_salavai_cone_order = 0
		with patch.object(
			frappe,
			"get_all",
			side_effect=[
				[frappe._dict(name="VARIANT-1", item="Karigan Yarn")],
				[frappe._dict(
					name="Karigan Yarn",
					mgk_is_karigan=1,
					mgk_is_salavai_cone=0,
				)],
			],
		):
			_validate_book_classification(doc)

	def test_karigan_order_rejects_non_karigan_items(self):
		doc = self._po_with_item("VARIANT-1")
		doc.mgk_is_karigan_order = 1
		doc.mgk_is_salavai_cone_order = 0
		with (
			patch.object(
				frappe,
				"get_all",
				side_effect=[
					[frappe._dict(name="VARIANT-1", item="Salavai Yarn")],
					[frappe._dict(
						name="Salavai Yarn",
						mgk_is_karigan=0,
						mgk_is_salavai_cone=1,
					)],
				],
			),
			self.assertRaises(frappe.ValidationError),
		):
			_validate_book_classification(doc)

	def test_other_order_rejects_classified_items(self):
		doc = self._po_with_item("VARIANT-1")
		doc.mgk_is_karigan_order = 0
		doc.mgk_is_salavai_cone_order = 0
		with (
			patch.object(
				frappe,
				"get_all",
				side_effect=[
					[frappe._dict(name="VARIANT-1", item="Karigan Yarn")],
					[frappe._dict(
						name="Karigan Yarn",
						mgk_is_karigan=1,
						mgk_is_salavai_cone=0,
					)],
				],
			),
			self.assertRaisesRegex(frappe.ValidationError, "Other Order"),
		):
			_validate_book_classification(doc)

	def test_previous_price_resolves_only_positive_cells(self):
		item_details = [
			{
				"items": [
					{
						"name": "Yarn",
						"attributes": {"Colour": "Blue"},
						"primary_attribute": "Size",
						"values": {"S": {"qty": 5}, "M": {"qty": 0}},
					}
				]
			}
		]

		with patch(
			"yrp.yrp.doctype.item.item.get_variant",
			return_value="Yarn-Blue-S",
		) as get_variant:
			result = purchase_order_api._resolve_previous_price_variants(item_details)

		self.assertEqual(result, {"0:0:S": "Yarn-Blue-S"})
		get_variant.assert_called_once_with("Yarn", {"Colour": "Blue", "Size": "S"})

	def test_previous_price_uses_latest_visible_submitted_order(self):
		orders = [
			frappe._dict(name="PO-NEWER", po_date="2026-07-02", creation="2026-07-02 09:00:00"),
			frappe._dict(name="PO-OLDER", po_date="2026-07-01", creation="2026-07-01 09:00:00"),
		]
		rows = [
			frappe._dict(parent="PO-OLDER", item_variant="Yarn-Blue", rate=90, idx=1),
			frappe._dict(parent="PO-NEWER", item_variant="Yarn-Blue", rate=110, idx=1),
		]

		with (
			patch.object(purchase_order_api.frappe, "has_permission", return_value=True),
			patch.object(
				purchase_order_api,
				"_resolve_previous_price_variants",
				return_value={"0:0:default": "Yarn-Blue"},
			),
			patch.object(purchase_order_api.frappe, "get_list", return_value=orders) as get_list,
			patch.object(purchase_order_api.frappe, "get_all", return_value=rows),
		):
			result = purchase_order_api.get_previous_purchase_prices(
				[{"items": [{"name": "Yarn", "values": {"default": {"qty": 5}}}]}],
				supplier="SUP-1",
			)

		self.assertEqual(result["0:0:default"]["rate"], 110)
		self.assertEqual(result["0:0:default"]["purchase_order"], "PO-NEWER")
		self.assertEqual(result["0:0:default"]["po_date"], "2026-07-02")
		self.assertEqual(get_list.call_args.kwargs["filters"]["docstatus"], 1)
