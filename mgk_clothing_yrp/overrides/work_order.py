"""mgk_clothing_yrp Work Order before_submit design-approval gate.

If the WO's process is listed in MGK Settings.process_approval_roles, the WO
cannot be submitted until `approved_by` is set (stamped by the approve API).
Processes NOT listed in MGK Settings are unaffected and submit freely.
Wired via `doc_events["Work Order"]["before_submit"]` in hooks.py.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, nowtime

from mgk_clothing_yrp.mgk_clothing_yrp.api.work_order import get_approver_role
from yrp.yrp.doctype.work_order.work_order import (
	_apply_close_details,
	_get_wo_close_approver_role,
	_is_wo_close_manager,
	_stock_dimension_values,
	_validate_wo_close,
)


def before_submit(doc, method=None):
	if get_approver_role(doc.process_name) and not doc.get("approved_by"):
		frappe.throw(
			_("Design approval is required for process '{0}' before this Work Order can be submitted. Ask the configured approver.").format(doc.process_name)
		)


@frappe.whitelist()
def update_stock(work_order, close_reason=None, close_other_reason=None, close_remarks=None):
	"""Close an MGK Work Order using only its unconsumed delivered inputs.

	GRN submissions increment ``Work Order Deliverables.stock_update``.  Closing
	therefore consumes only ``delivered - stock_update``.  Available stock is
	tracked per item/warehouse/dimension bucket across every deliverable row so
	duplicate rows can never consume the same physical balance twice.  Work
	Order Correction deliverables are intentionally outside this document and
	are never read here.
	"""
	from yrp.stock.stock_ledger import enqueue_voucher_repost, make_sl_entries
	from yrp.stock.utils import (
		close_voucher_reservations,
		get_conversion_factor,
		get_stock_balance,
	)
	from yrp.yrp.doctype.delivery_challan.delivery_challan import (
		_get_warehouse_for_supplier,
	)

	frappe.db.sql(
		"SELECT name FROM `tabWork Order` WHERE name=%s FOR UPDATE",
		(work_order,),
	)
	doc = frappe.get_doc("Work Order", work_order)
	if doc.docstatus != 1:
		frappe.throw(_("Only submitted Work Orders can be closed."))
	if doc.open_status == "Close":
		return "Close"

	if not _is_wo_close_manager(throw_if_missing=True):
		if doc.open_status == "Close Request":
			approver_role = _get_wo_close_approver_role()
			frappe.throw(
				_("Only users with role {0} can approve close requests.").format(
					approver_role
				)
			)
		_apply_close_details(
			doc,
			"Close Request",
			close_reason,
			close_other_reason,
			close_remarks,
		)
		doc.save(ignore_permissions=True)
		frappe.msgprint(_("Close Request has been submitted for approval."), alert=True)
		return "Close Request"

	_validate_wo_close(doc)
	warehouse = _get_warehouse_for_supplier(doc.supplier)
	if not warehouse:
		frappe.throw(_("No active Warehouse found for supplier {0}.").format(doc.supplier))

	entries = []
	remaining_by_bucket = {}
	posting_date = nowdate()
	posting_time = nowtime()
	for row in doc.get("deliverables") or []:
		delivered_qty = flt(row.qty) - flt(row.pending_quantity)
		reduce_qty = delivered_qty - flt(row.stock_update)
		if reduce_qty <= 0:
			continue
		conversion = get_conversion_factor(row.item_variant, row.uom)
		factor = flt(conversion.get("conversion_factor")) or 1
		reduce_stock_qty = reduce_qty * factor

		dimensions = _stock_dimension_values(doc, row)
		bucket = (
			row.item_variant,
			warehouse,
			tuple(sorted(dimensions.items())),
		)
		if bucket not in remaining_by_bucket:
			balance, valuation_rate = get_stock_balance(
				row.item_variant,
				warehouse,
				posting_date=posting_date,
				posting_time=posting_time,
				with_valuation_rate=True,
				**dimensions,
			)
			remaining_by_bucket[bucket] = {
				"qty": max(flt(balance), 0),
				"valuation_rate": flt(valuation_rate),
			}

		bucket_balance = remaining_by_bucket[bucket]
		reduce_stock_qty = min(reduce_stock_qty, bucket_balance["qty"])
		if reduce_stock_qty <= 0:
			continue
		reduce_qty = reduce_stock_qty / factor

		entries.append(
			{
				"item": row.item_variant,
				"warehouse": warehouse,
				"uom": conversion.get("stock_uom") or row.uom,
				"voucher_type": doc.doctype,
				"voucher_no": doc.name,
				"voucher_detail_no": row.name,
				"posting_date": posting_date,
				"posting_time": posting_time,
				"qty": -reduce_stock_qty,
				"rate": 0,
				"outgoing_rate": flt(
					row.valuation_rate
					or row.rate
					or bucket_balance["valuation_rate"]
				),
				"is_cancelled": 0,
				**dimensions,
			}
		)
		row.stock_update = flt(row.stock_update) + reduce_qty
		bucket_balance["qty"] -= reduce_stock_qty

	make_sl_entries(entries)
	_apply_close_details(doc, "Close", close_reason, close_other_reason, close_remarks)
	doc.closed_by = frappe.session.user
	doc.is_delivered = 1
	doc.total_quantity = 0
	doc.save(ignore_permissions=True)
	close_voucher_reservations("Work Order", doc.name)
	enqueue_voucher_repost(
		frappe._dict(
			doctype=doc.doctype,
			name=doc.name,
			posting_date=posting_date,
			posting_time=posting_time,
		)
	)
	return "Close"
