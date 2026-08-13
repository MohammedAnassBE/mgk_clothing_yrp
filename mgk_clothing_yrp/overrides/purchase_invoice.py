"""mgk_clothing_yrp customisations on yrp's `Purchase Invoice`.

Owns the company-specific item-aggregation logic when fetching items from
GRNs into a Purchase Invoice. The base yrp implementation handles the
generic case; this override replaces it for sites where mgk_clothing_yrp
is installed.

Wired via `override_whitelisted_methods` in hooks.py.

The Work Order branch is where MGK Clothing's piece / debit / approval
math lives — edit that block when the customer's formula needs to change,
not the base yrp file.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt

from yrp.yrp.doctype.purchase_invoice.purchase_invoice import (
	_check_invoice_fetch_permission,
	_get_item_group,
	_get_tax_rate,
	_get_work_order_item_totals,
	_normal_json,
	_validate_selected_grn,
)


@frappe.whitelist()
def fetch_grn_details(grns, against, supplier, purchase_invoice=None):
	_check_invoice_fetch_permission(purchase_invoice)
	frappe.has_permission("Goods Received Note", "read", throw=True)
	grns = frappe.parse_json(grns) if isinstance(grns, str) else grns
	grns = list(dict.fromkeys(grns or []))
	if not grns:
		frappe.throw(_("Please select at least one GRN."))

	items = {}
	wo_items = {}
	total_quantity = 0
	for grn_name in grns:
		_validate_selected_grn(grn_name, supplier, against, purchase_invoice)
		grn = frappe.get_doc("Goods Received Note", grn_name)

		work_order = (
			frappe.get_doc("Work Order", grn.against_id) if grn.against == "Work Order" else None
		)
		for grn_item in grn.get("items") or []:
			qty = flt(grn_item.quantity)
			stock_rate = flt(grn_item.rate)
			rate = (flt(grn_item.amount) / qty) if qty else stock_rate
			tax = grn_item.get("tax") if grn_item.meta.get_field("tax") else None
			set_combination = _normal_json(grn_item.get("set_combination"))
			key = (
				grn_item.item_variant,
				grn_item.uom,
				rate,
				tax,
				json.dumps(set_combination, sort_keys=True),
			)
			item_group = _get_item_group(grn_item.item_variant)
			items.setdefault(
				key,
				{
					"item": grn_item.item_variant,
					"item_group": item_group,
					"qty": 0,
					"uom": grn_item.uom,
					"rate": rate,
					"amount": 0,
					"tax": tax,
					"actual_rate": stock_rate,
					"actual_qty": 0,
					"_actual_amount": 0,
					"set_combination": json.dumps(set_combination) if set_combination else None,
				},
			)
			items[key]["qty"] += qty
			items[key]["actual_qty"] += qty
			items[key]["amount"] += qty * rate
			items[key]["_actual_amount"] += qty * stock_rate
			total_quantity += qty

			if work_order:
				wo_key = (
					work_order.name,
					grn_item.item_variant,
					json.dumps(set_combination, sort_keys=True),
				)
				wo_totals = _get_work_order_item_totals(
					work_order, grn_item.item_variant, set_combination
				)
				wo_items.setdefault(
					wo_key,
					{
						"work_order": work_order.name,
						"item_variant": grn_item.item_variant,
						"set_combination": json.dumps(set_combination) if set_combination else None,
						"quantity": 0,
						"total_delivered": wo_totals["total_delivered"],
						"total_received": wo_totals["total_received"],
						"billed": wo_totals["billed"],
					},
				)
				wo_items[wo_key]["quantity"] += qty

	item_rows = list(items.values())
	for row in item_rows:
		row["rate"] = flt(row["amount"]) / flt(row["qty"]) if flt(row["qty"]) else 0
		row["actual_rate"] = (
			flt(row.pop("_actual_amount")) / flt(row["actual_qty"])
			if flt(row["actual_qty"])
			else 0
		)
		row["amount"] = flt(row["qty"]) * flt(row["rate"])

	grand_total = sum(
		flt(row["amount"]) + (flt(row["amount"]) * _get_tax_rate(row.get("tax")) / 100)
		for row in item_rows
	)

	return {
		"items": item_rows,
		"total": grand_total,
		"total_quantity": total_quantity,
		"wo_items": list(wo_items.values()),
		"tax_rates": {
			row.get("tax"): _get_tax_rate(row.get("tax"))
			for row in item_rows
			if row.get("tax")
		},
		"allow_to_change_rate": 1,
	}
