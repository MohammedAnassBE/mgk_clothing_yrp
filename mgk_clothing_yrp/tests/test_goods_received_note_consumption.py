from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from mgk_clothing_yrp.overrides.goods_received_note import (
	apply_work_order_stock_update,
	calculate_consumption_plan,
	load_submitted_consumption_plan,
)


class TestMGKGoodsReceivedNoteConsumption(FrappeTestCase):
	def _work_order(self, delivered=100):
		return frappe._dict(
			name="WO-TEST",
			production_detail="IPD-TEST",
			process_name="Doubling",
			deliverables=[
				frappe._dict(
					name="WO-DEL-ORANGE",
					item_variant="INPUT-ORANGE",
					qty=100,
					pending_quantity=100 - delivered,
					stock_update=0,
					uom="Kg",
					valuation_rate=12,
					rate=0,
				),
				frappe._dict(
					name="WO-DEL-BLUE",
					item_variant="INPUT-BLUE",
					qty=100,
					pending_quantity=100 - delivered,
					stock_update=0,
					uom="Kg",
					valuation_rate=13,
					rate=0,
				),
			],
		)

	def _grn(self):
		return frappe._dict(
			against_id="WO-TEST",
			from_warehouse="SUPPLIER-WH",
			posting_date="2026-08-11",
			posting_time="10:00:00",
			items=[
				frappe._dict(item_variant="OUTPUT-ORANGE", quantity=5),
				frappe._dict(item_variant="OUTPUT-ORANGE", quantity=6),
				frappe._dict(item_variant="OUTPUT-BLUE", quantity=5),
			],
			# A correction receipt can coexist on the GRN, but must never consume
			# the Work Order's own deliverables.
			correction_items=[
				frappe._dict(item_variant="CORRECTION-OUTPUT", quantity=999),
			],
		)

	def test_consumes_matrix_inputs_for_regular_rows_only(self):
		wo = self._work_order()
		matrix_result = {
			"inputs": [
				{"item": "INPUT", "attrs": {"Colour": "Orange"}, "qty": 11, "uom": "Kg"},
				{"item": "INPUT", "attrs": {"Colour": "Blue"}, "qty": 5, "uom": "Kg"},
			],
			"outputs": [],
		}

		with (
			patch("mgk_clothing_yrp.overrides.goods_received_note.frappe.get_doc", return_value=wo),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.get_variant_attributes",
				side_effect=lambda variant: {"Colour": variant.rsplit("-", 1)[-1].title()},
			),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.frappe.get_cached_value",
				return_value="INPUT",
			),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.get_process_io",
				return_value=matrix_result,
			) as process_io,
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.get_conversion_factor",
				return_value={"conversion_factor": 1, "stock_uom": "Kg"},
			),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note._stock_dimension_values",
				return_value={"received_type": "Accepted"},
			),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.get_stock_balance",
				return_value=(100, 12),
			),
		):
			plan = calculate_consumption_plan(self._grn())

		demands = process_io.call_args.args[2]
		self.assertEqual(
			{row["item_variant"]: row["qty"] for row in demands},
			{"OUTPUT-ORANGE": 11, "OUTPUT-BLUE": 5},
		)
		self.assertEqual(
			{row["work_order_deliverable"]: row["quantity"] for row in plan},
			{"WO-DEL-ORANGE": 11, "WO-DEL-BLUE": 5},
		)

	def test_receipt_cannot_consume_more_than_delivered_input(self):
		wo = self._work_order(delivered=5)
		with (
			patch("mgk_clothing_yrp.overrides.goods_received_note.frappe.get_doc", return_value=wo),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.get_variant_attributes",
				side_effect=lambda variant: {"Colour": variant.rsplit("-", 1)[-1].title()},
			),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.frappe.get_cached_value",
				return_value="INPUT",
			),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.get_process_io",
				return_value={
					"inputs": [{"item": "INPUT", "attrs": {"Colour": "Orange"}, "qty": 11, "uom": "Kg"}],
					"outputs": [],
				},
			),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.get_conversion_factor",
				return_value={"conversion_factor": 1, "stock_uom": "Kg"},
			),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note._stock_dimension_values",
				return_value={"received_type": "Accepted"},
			),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.get_stock_balance",
				return_value=(100, 12),
			),
			self.assertRaisesRegex(frappe.ValidationError, "Deliver the remaining input"),
		):
			calculate_consumption_plan(self._grn())

	def test_stock_update_targets_only_named_work_order_deliverable(self):
		wo = self._work_order()
		plan = [
			{
				"work_order_deliverable": "WO-DEL-ORANGE",
				"quantity": 8,
			}
		]
		with (
			patch("mgk_clothing_yrp.overrides.goods_received_note.frappe.get_doc", return_value=wo),
			patch.object(frappe.db, "set_value") as set_value,
		):
			apply_work_order_stock_update("WO-TEST", plan)

		set_value.assert_called_once_with(
			"Work Order Deliverables",
			"WO-DEL-ORANGE",
			"stock_update",
			8.0,
			update_modified=False,
		)

	def test_cancel_audit_ignores_non_work_order_deliverable_sles(self):
		wo = self._work_order()
		grn = frappe._dict(
			doctype="Goods Received Note",
			name="GRN-TEST",
			against_id="WO-TEST",
			from_warehouse="SUPPLIER-WH",
		)
		ledger_rows = [
			frappe._dict(
				item="INPUT-ORANGE",
				qty=-8,
				uom="Kg",
				voucher_detail_no="WO-DEL-ORANGE",
				valuation_rate=12,
				outgoing_rate=12,
			),
			frappe._dict(
				item="CORRECTION-INPUT",
				qty=-99,
				uom="Kg",
				voucher_detail_no="CORRECTION-DELIVERABLE",
				valuation_rate=1,
				outgoing_rate=1,
			),
		]
		with (
			patch("mgk_clothing_yrp.overrides.goods_received_note.frappe.get_doc", return_value=wo),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.get_dimension_fieldnames",
				return_value=["received_type"],
			),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.frappe.get_all",
				return_value=ledger_rows,
			),
			patch(
				"mgk_clothing_yrp.overrides.goods_received_note.get_conversion_factor",
				return_value={"conversion_factor": 1, "stock_uom": "Kg"},
			),
		):
			plan = load_submitted_consumption_plan(grn)

		self.assertEqual(len(plan), 1)
		self.assertEqual(plan[0]["work_order_deliverable"], "WO-DEL-ORANGE")
		self.assertEqual(plan[0]["quantity"], 8)

	def test_cancel_restores_recorded_work_order_stock_update(self):
		wo = self._work_order()
		wo.deliverables[0].stock_update = 20
		plan = [
			{
				"work_order_deliverable": "WO-DEL-ORANGE",
				"quantity": 8,
			}
		]
		with (
			patch("mgk_clothing_yrp.overrides.goods_received_note.frappe.get_doc", return_value=wo),
			patch.object(frappe.db, "set_value") as set_value,
		):
			apply_work_order_stock_update("WO-TEST", plan, cancel=True)

		self.assertEqual(set_value.call_args.args[3], 12.0)
