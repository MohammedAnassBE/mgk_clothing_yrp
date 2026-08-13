from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from mgk_clothing_yrp.overrides.work_order import update_stock


class TestMGKWorkOrderClose(FrappeTestCase):
	def test_duplicate_rows_share_one_physical_stock_balance(self):
		rows = [
			frappe._dict(
				name="DEL-1",
				item_variant="YARN-BLUE",
				qty=8,
				pending_quantity=0,
				stock_update=0,
				uom="Kg",
				valuation_rate=20,
				rate=0,
			),
			frappe._dict(
				name="DEL-2",
				item_variant="YARN-BLUE",
				qty=8,
				pending_quantity=0,
				stock_update=0,
				uom="Kg",
				valuation_rate=20,
				rate=0,
			),
		]
		doc = frappe._dict(
			name="WO-TEST",
			doctype="Work Order",
			docstatus=1,
			open_status="Open",
			supplier="SUPPLIER-1",
			deliverables=rows,
			# Deliberately large correction row: the close function must never
			# inspect or consume it.
			correction_deliverables=[
				frappe._dict(item_variant="YARN-BLUE", qty=999)
			],
		)
		doc.save = Mock()

		with (
			patch.object(frappe.db, "sql"),
			patch("mgk_clothing_yrp.overrides.work_order.frappe.get_doc", return_value=doc),
			patch("mgk_clothing_yrp.overrides.work_order._is_wo_close_manager", return_value=True),
			patch("mgk_clothing_yrp.overrides.work_order._validate_wo_close"),
			patch(
				"yrp.yrp.doctype.delivery_challan.delivery_challan._get_warehouse_for_supplier",
				return_value="SUPPLIER-WH",
			),
			patch(
				"mgk_clothing_yrp.overrides.work_order._stock_dimension_values",
				return_value={"received_type": "Accepted"},
			),
			patch(
				"yrp.stock.utils.get_conversion_factor",
				return_value={"conversion_factor": 1, "stock_uom": "Kg"},
			),
			patch("yrp.stock.utils.get_stock_balance", return_value=(10, 20)) as balance,
			patch("yrp.stock.stock_ledger.make_sl_entries") as make_sl_entries,
			patch("yrp.stock.stock_ledger.enqueue_voucher_repost"),
			patch("yrp.stock.utils.close_voucher_reservations"),
			patch("mgk_clothing_yrp.overrides.work_order.nowdate", return_value="2026-08-11"),
			patch("mgk_clothing_yrp.overrides.work_order.nowtime", return_value="10:00:00"),
		):
			result = update_stock("WO-TEST")

		entries = make_sl_entries.call_args.args[0]
		self.assertEqual(result, "Close")
		self.assertEqual(sum(abs(row["qty"]) for row in entries), 10)
		self.assertEqual([abs(row["qty"]) for row in entries], [8, 2])
		self.assertEqual(rows[0].stock_update, 8)
		self.assertEqual(rows[1].stock_update, 2)
		balance.assert_called_once()

	def test_close_converts_form_quantity_to_stock_uom(self):
		row = frappe._dict(
			name="DEL-1",
			item_variant="YARN-CONE",
			qty=8,
			pending_quantity=0,
			stock_update=0,
			uom="Cone",
			valuation_rate=20,
			rate=0,
		)
		doc = frappe._dict(
			name="WO-TEST",
			doctype="Work Order",
			docstatus=1,
			open_status="Open",
			supplier="SUPPLIER-1",
			deliverables=[row],
		)
		doc.save = Mock()
		with (
			patch.object(frappe.db, "sql"),
			patch("mgk_clothing_yrp.overrides.work_order.frappe.get_doc", return_value=doc),
			patch("mgk_clothing_yrp.overrides.work_order._is_wo_close_manager", return_value=True),
			patch("mgk_clothing_yrp.overrides.work_order._validate_wo_close"),
			patch(
				"yrp.yrp.doctype.delivery_challan.delivery_challan._get_warehouse_for_supplier",
				return_value="SUPPLIER-WH",
			),
			patch(
				"mgk_clothing_yrp.overrides.work_order._stock_dimension_values",
				return_value={"received_type": "Accepted"},
			),
			patch(
				"yrp.stock.utils.get_conversion_factor",
				return_value={"conversion_factor": 2, "stock_uom": "Kg"},
			),
			patch("yrp.stock.utils.get_stock_balance", return_value=(10, 20)),
			patch("yrp.stock.stock_ledger.make_sl_entries") as make_sl_entries,
			patch("yrp.stock.stock_ledger.enqueue_voucher_repost"),
			patch("yrp.stock.utils.close_voucher_reservations"),
			patch("mgk_clothing_yrp.overrides.work_order.nowdate", return_value="2026-08-11"),
			patch("mgk_clothing_yrp.overrides.work_order.nowtime", return_value="10:00:00"),
		):
			update_stock("WO-TEST")

		entry = make_sl_entries.call_args.args[0][0]
		self.assertEqual(entry["qty"], -10)
		self.assertEqual(entry["uom"], "Kg")
		self.assertEqual(row.stock_update, 5)
