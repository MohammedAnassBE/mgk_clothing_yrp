# Copyright (c) 2026, MGK Clothing and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from mgk_clothing_yrp.mgk_clothing_yrp.api import link_search as link_search_api


class _SupplierMeta:
	name = "Supplier"
	title_field = "supplier_name"
	search_fields = "supplier_name"

	@staticmethod
	def has_field(fieldname):
		return fieldname in {"supplier_name", "mgk_tamil_name"}


class TestBilingualLinkSearch(FrappeTestCase):
	def test_returns_canonical_name_with_both_display_labels(self):
		rows = [
			frappe._dict(
				name="S-0007",
				supplier_name="MGK Sample Yarn Supplier",
				mgk_tamil_name="எம்ஜிகே மாதிரி நூல் சப்ளையர்",
			)
		]
		with (
			patch.object(link_search_api.frappe, "get_meta", return_value=_SupplierMeta()),
			patch.object(link_search_api.frappe, "get_list", return_value=rows) as get_list,
		):
			result = link_search_api.link_search("Supplier", "Yarn")

		self.assertEqual(result[0]["name"], "S-0007")
		self.assertEqual(result[0]["label_en"], "MGK Sample Yarn Supplier")
		self.assertEqual(result[0]["label_ta"], "எம்ஜிகே மாதிரி நூல் சப்ளையர்")
		self.assertEqual(result[0]["label"], result[0]["label_en"])
		self.assertIn("mgk_tamil_name", get_list.call_args.kwargs["fields"])

	def test_tamil_display_field_is_not_a_search_field(self):
		with (
			patch.object(link_search_api.frappe, "get_meta", return_value=_SupplierMeta()),
			patch.object(link_search_api.frappe, "get_list", return_value=[]) as get_list,
		):
			link_search_api.link_search("Supplier", "நூல்")

		or_filters = get_list.call_args.kwargs["or_filters"]
		self.assertEqual(or_filters, [["name", "like", "%நூல்%"], ["supplier_name", "like", "%நூல்%"]])
		self.assertNotIn(["mgk_tamil_name", "like", "%நூல்%"], or_filters)

	def test_missing_tamil_name_falls_back_in_frontend_not_server_storage(self):
		rows = [
			frappe._dict(
				name="S-0011",
				supplier_name="Supplier Without Tamil",
				mgk_tamil_name=None,
			)
		]
		with (
			patch.object(link_search_api.frappe, "get_meta", return_value=_SupplierMeta()),
			patch.object(link_search_api.frappe, "get_list", return_value=rows),
		):
			result = link_search_api.link_search("Supplier", "Without")

		self.assertEqual(result[0]["label_en"], "Supplier Without Tamil")
		self.assertEqual(result[0]["label_ta"], "")
