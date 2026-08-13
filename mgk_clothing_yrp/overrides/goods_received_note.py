"""MGK Work Order GRN material-consumption accounting.

The base YRP GRN receives the Work Order outputs and updates the receivable
pending quantity.  MGK's yarn workflow also needs to consume the proportional
Work Order inputs when those outputs are received.  This override deliberately
uses only ``Goods Received Note.items`` and ``Work Order.deliverables``;
``correction_items`` and Work Order Correction deliverables are never part of
this calculation.

The submitted Stock Ledger Entries are the durable audit trail.  Their
``voucher_detail_no`` points at the source Work Order Deliverables row, so a
cancel restores the exact quantities originally consumed even if the IPD
matrix is edited later.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from yrp.stock.dimensions import get_dimension_fieldnames
from yrp.stock.utils import get_conversion_factor, get_stock_balance
from yrp.yrp.doctype.goods_received_note.goods_received_note import (
	GoodsReceivedNote,
)
from yrp.yrp.doctype.work_order.work_order import (
	_stock_dimension_values,
	get_variant_attributes,
)
from yrp.yrp.utils.ipd_engine import get_process_io


QTY_TOLERANCE = 0.0001


class MGKGoodsReceivedNote(GoodsReceivedNote):
	"""Extend only MGK's Work Order receipt lifecycle."""

	def before_submit(self):
		super().before_submit()
		if self._uses_mgk_deliverable_consumption():
			_lock_work_order(self.against_id)
			self.flags.mgk_deliverable_consumption = calculate_consumption_plan(self)

	def before_cancel(self):
		if self._uses_mgk_deliverable_consumption():
			_lock_work_order(self.against_id)
			if frappe.db.get_value("Work Order", self.against_id, "open_status") == "Close":
				frappe.throw(
					_("Reopen Work Order {0} before cancelling Goods Received Note {1}.").format(
						self.against_id, self.name
					)
				)
			self.flags.mgk_deliverable_consumption = load_submitted_consumption_plan(self)
		super().before_cancel()

	def on_submit(self):
		super().on_submit()
		if self._uses_mgk_deliverable_consumption():
			apply_work_order_stock_update(
				self.against_id,
				self.flags.get("mgk_deliverable_consumption") or [],
			)
		self.make_repost_action()

	def on_cancel(self):
		super().on_cancel()
		if self._uses_mgk_deliverable_consumption():
			apply_work_order_stock_update(
				self.against_id,
				self.flags.get("mgk_deliverable_consumption") or [],
				cancel=True,
			)
		self.make_repost_action()

	def make_stock_ledger_entries(self, cancel=False):
		"""Post the base receipt, then the MGK input consumption."""
		super().make_stock_ledger_entries(cancel=cancel)
		if not self._uses_mgk_deliverable_consumption():
			return

		plan = self.flags.get("mgk_deliverable_consumption")
		if plan is None:
			plan = (
				load_submitted_consumption_plan(self)
				if cancel
				else calculate_consumption_plan(self)
			)
			self.flags.mgk_deliverable_consumption = plan
		if not plan:
			return

		from yrp.stock.stock_ledger import make_sl_entries

		make_sl_entries(
			[consumption_sle(self, row) for row in plan],
			cancel=cancel,
		)

	def make_repost_action(self):
		from yrp.stock.stock_ledger import enqueue_voucher_repost

		enqueue_voucher_repost(self)

	def _uses_mgk_deliverable_consumption(self):
		return bool(
			self.against == "Work Order"
			and self.against_id
			and not self.get("is_rework")
			and self.get("items")
		)


def calculate_consumption_plan(grn):
	"""Return exact Work Order input rows consumed by this GRN.

	Each received Work Order output is sent through the approved/generated IPD
	Process Matrix.  The required input is then allocated only against the
	already-delivered balance of the Work Order's own deliverable rows.
	"""
	wo = frappe.get_doc("Work Order", grn.against_id)
	if not wo.production_detail or not wo.process_name:
		# Submitted legacy MGK Work Orders predate the now-mandatory IPD field.
		# Keep their existing GRN path working; all newly created MGK Work Orders
		# have an IPD and therefore use the matrix-backed consumption path below.
		return []

	demands_by_variant = defaultdict(float)
	for row in grn.get("items") or []:
		qty = flt(row.quantity)
		if qty > 0:
			demands_by_variant[row.item_variant] += qty
	if not demands_by_variant:
		return []

	demands = [
		{
			"item_variant": variant,
			"reference_item_variant": variant,
			"attrs": get_variant_attributes(variant),
			"qty": qty,
		}
		for variant, qty in demands_by_variant.items()
	]
	matrix_io = get_process_io(wo.production_detail, wo.process_name, demands)
	input_rows = matrix_io.get("inputs") or []
	if not input_rows:
		frappe.throw(
			_("The Process Matrix returned no input materials for Work Order {0}.").format(
				wo.name
			)
		)

	variant_cache = {}
	required_stock_by_variant = defaultdict(float)
	required_uom_by_variant = {}
	for matrix_row in input_rows:
		variant = find_deliverable_variant(
			wo.get("deliverables") or [],
			matrix_row.get("item"),
			matrix_row.get("attrs") or {},
			variant_cache,
		)
		matrix_uom = matrix_row.get("uom")
		conversion = get_conversion_factor(variant, matrix_uom)
		stock_qty = flt(matrix_row.get("qty")) * (flt(conversion.get("conversion_factor")) or 1)
		required_stock_by_variant[variant] += stock_qty
		required_uom_by_variant[variant] = conversion.get("stock_uom") or matrix_uom

	plan = []
	for variant, required_stock_qty in required_stock_by_variant.items():
		remaining_stock_qty = required_stock_qty
		for deliverable in wo.get("deliverables") or []:
			if deliverable.item_variant != variant:
				continue
			conversion = get_conversion_factor(variant, deliverable.uom)
			factor = flt(conversion.get("conversion_factor")) or 1
			delivered_qty = flt(deliverable.qty) - flt(deliverable.pending_quantity)
			available_qty = max(delivered_qty - flt(deliverable.stock_update), 0)
			available_stock_qty = available_qty * factor
			if available_stock_qty <= QTY_TOLERANCE:
				continue

			take_stock_qty = min(remaining_stock_qty, available_stock_qty)
			take_qty = take_stock_qty / factor
			dimensions = _stock_dimension_values(wo, deliverable)
			_balance, valuation_rate = get_stock_balance(
				variant,
				grn.from_warehouse,
				posting_date=grn.posting_date,
				posting_time=grn.posting_time,
				with_valuation_rate=True,
				**dimensions,
			)
			plan.append(
				{
					"work_order_deliverable": deliverable.name,
					"item_variant": variant,
					"quantity": take_qty,
					"stock_qty": take_stock_qty,
					"uom": deliverable.uom,
					"stock_uom": conversion.get("stock_uom") or required_uom_by_variant.get(variant),
					"valuation_rate": flt(deliverable.valuation_rate or deliverable.rate or valuation_rate),
					"dimensions": dimensions,
				}
			)
			remaining_stock_qty -= take_stock_qty
			if remaining_stock_qty <= QTY_TOLERANCE:
				break

		if remaining_stock_qty > QTY_TOLERANCE:
			available = required_stock_qty - remaining_stock_qty
			frappe.throw(
				_(
					"Work Order {0} has only {1} delivered stock available for {2}, "
					"but this receipt requires {3}. Deliver the remaining input before receiving it."
				).format(
					wo.name,
					flt(available),
					variant,
					flt(required_stock_qty),
				)
			)

	return plan


def find_deliverable_variant(deliverables, item, attributes, variant_cache=None):
	"""Resolve a matrix input strictly to a variant already on the Work Order."""
	variant_cache = variant_cache if variant_cache is not None else {}
	matches = []
	for row in deliverables:
		variant = row.item_variant
		if variant not in variant_cache:
			variant_cache[variant] = {
				"item": frappe.get_cached_value("Item Variant", variant, "item"),
				"attributes": get_variant_attributes(variant),
			}
		context = variant_cache[variant]
		if context["item"] != item:
			continue
		if all(context["attributes"].get(key) == value for key, value in attributes.items()):
			matches.append(variant)

	unique_matches = list(dict.fromkeys(matches))
	if len(unique_matches) != 1:
		frappe.throw(
			_(
				"Could not uniquely match Process Matrix input {0} ({1}) to Work Order deliverables."
			).format(item, ", ".join(f"{key}: {value}" for key, value in sorted(attributes.items())) or _("no attributes"))
		)
	return unique_matches[0]


def consumption_sle(grn, row):
	base = {
		"item": row["item_variant"],
		"warehouse": grn.from_warehouse,
		"uom": row.get("stock_uom") or row.get("uom"),
		"voucher_type": grn.doctype,
		"voucher_no": grn.name,
		"voucher_detail_no": row["work_order_deliverable"],
		"posting_date": grn.posting_date,
		"posting_time": grn.posting_time,
		"qty": -flt(row["stock_qty"]),
		"rate": 0,
		"outgoing_rate": flt(row.get("valuation_rate")),
		"is_cancelled": 0,
	}
	base.update(row.get("dimensions") or {})
	return base


def load_submitted_consumption_plan(grn):
	"""Load the exact active MGK consumption SLEs for cancellation."""
	wo_rows = {
		row.name: row
		for row in frappe.get_doc("Work Order", grn.against_id).get("deliverables") or []
	}
	if not wo_rows:
		return []

	fields = [
		"item",
		"qty",
		"uom",
		"voucher_detail_no",
		"valuation_rate",
		"outgoing_rate",
	] + get_dimension_fieldnames()
	ledger_rows = frappe.get_all(
		"Stock Ledger Entry",
		filters={
			"voucher_type": grn.doctype,
			"voucher_no": grn.name,
			"warehouse": grn.from_warehouse,
			"qty": ["<", 0],
			"is_cancelled": 0,
		},
		fields=fields,
		order_by="creation asc",
	)

	plan = []
	for ledger_row in ledger_rows:
		deliverable = wo_rows.get(ledger_row.voucher_detail_no)
		if not deliverable:
			continue
		conversion = get_conversion_factor(ledger_row.item, deliverable.uom)
		factor = flt(conversion.get("conversion_factor")) or 1
		dimensions = {
			fieldname: ledger_row.get(fieldname)
			for fieldname in get_dimension_fieldnames()
		}
		plan.append(
			{
				"work_order_deliverable": deliverable.name,
				"item_variant": ledger_row.item,
				"quantity": abs(flt(ledger_row.qty)) / factor,
				"stock_qty": abs(flt(ledger_row.qty)),
				"uom": deliverable.uom,
				"stock_uom": conversion.get("stock_uom") or ledger_row.uom,
				"valuation_rate": flt(ledger_row.outgoing_rate or ledger_row.valuation_rate),
				"dimensions": dimensions,
			}
		)
	return plan


def apply_work_order_stock_update(work_order, plan, cancel=False):
	"""Increment/decrement only the Work Order's own deliverable rows."""
	if not plan:
		return
	rows = {
		row.name: row
		for row in frappe.get_doc("Work Order", work_order).get("deliverables") or []
	}
	qty_by_row = defaultdict(float)
	for item in plan:
		qty_by_row[item["work_order_deliverable"]] += flt(item["quantity"])

	for row_name, qty in qty_by_row.items():
		row = rows.get(row_name)
		if not row:
			frappe.throw(
				_("Work Order Deliverable {0} no longer exists on {1}.").format(
					row_name, work_order
				)
			)
		current = flt(row.stock_update)
		if cancel and current + QTY_TOLERANCE < qty:
			frappe.throw(
				_("Consumed stock audit mismatch for Work Order Deliverable {0}.").format(row_name)
			)
		new_value = max(current - qty, 0) if cancel else current + qty
		frappe.db.set_value(
			"Work Order Deliverables",
			row_name,
			"stock_update",
			flt(new_value),
			update_modified=False,
		)


def _lock_work_order(work_order):
	frappe.db.sql(
		"SELECT name FROM `tabWork Order` WHERE name=%s FOR UPDATE",
		(work_order,),
	)
