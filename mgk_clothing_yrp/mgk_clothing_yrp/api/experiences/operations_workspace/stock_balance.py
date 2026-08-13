"""Permission-aware Stock Note data for the MGK Registered Experience."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from yrp.yrp_stock.report.stock_balance.stock_balance import execute as run_stock_balance


def _allowed_warehouses():
	"""Match YRP's Warehouse Link rule: configured users restrict the list."""
	filters = {"disabled": 0}
	restricted = frappe.db.sql_list(
		"SELECT DISTINCT parent FROM `tabWarehouse User` WHERE user=%s",
		frappe.session.user,
	)
	if restricted:
		filters["name"] = ["in", restricted]
	return frappe.get_list(
		"Warehouse",
		filters=filters,
		fields=["name", "name1", "supplier", "mgk_tamil_name"],
		order_by="name1 asc, name asc",
		limit_page_length=0,
	)


def _options(warehouses):
	supplier_ids = sorted({row.supplier for row in warehouses if row.supplier})
	suppliers = []
	if supplier_ids:
		suppliers = frappe.get_list(
			"Supplier",
			filters={"name": ["in", supplier_ids], "disabled": 0},
			fields=["name", "supplier_name", "mgk_tamil_name"],
			order_by="supplier_name asc, name asc",
			limit_page_length=0,
		)

	items = frappe.get_list(
		"Item",
		filters={"disabled": 0, "is_stock_item": 1},
		fields=["name", "name1", "mgk_tamil_name", "default_unit_of_measure"],
		order_by="name1 asc, name asc",
		limit_page_length=0,
	)
	received_types = frappe.get_list(
		"Received Type",
		fields=["name"],
		order_by="name asc",
		limit_page_length=0,
	)
	return {
		"warehouses": warehouses,
		"suppliers": suppliers,
		"items": items,
		"received_types": received_types,
	}


@frappe.whitelist()
def get_stock_note(from_date=None, to_date=None, supplier=None, warehouse=None, item=None, received_type=None):
	"""Return current balance plus the remaining FIFO quantity by inward date."""
	frappe.has_permission("Stock Ledger Entry", ptype="read", throw=True)
	frappe.has_permission("Warehouse", ptype="read", throw=True)

	to_date = getdate(to_date or nowdate())
	from_date = getdate(from_date or add_days(to_date, -30))
	if from_date > to_date:
		frappe.throw(_("From Date cannot be after To Date."))

	warehouses = _allowed_warehouses()
	allowed_names = {row.name for row in warehouses}
	if warehouse and warehouse not in allowed_names:
		frappe.throw(_("You are not permitted to view Warehouse {0}.").format(frappe.bold(warehouse)), frappe.PermissionError)

	selected_warehouses = [warehouse] if warehouse else sorted(allowed_names)
	if supplier:
		selected_warehouses = [
			row.name for row in warehouses
			if row.supplier == supplier and (not warehouse or row.name == warehouse)
		]

	filters = frappe._dict(
		from_date=from_date,
		to_date=to_date,
		warehouse=selected_warehouses or ["__no_permitted_warehouse__"],
		parent_item=item,
		received_type=received_type,
		remove_zero_balance_item=1,
		show_inward_date_split=1,
	)
	_columns, rows = run_stock_balance(filters)
	rows = [frappe._dict(row) for row in rows]

	warehouse_map = {row.name: row for row in warehouses}
	supplier_ids = {warehouse_map.get(row.warehouse, {}).get("supplier") for row in rows}
	supplier_ids.discard(None)
	supplier_names = {}
	if supplier_ids:
		supplier_names = {
			row.name: row
			for row in frappe.get_list(
				"Supplier",
				filters={"name": ["in", list(supplier_ids)]},
				fields=["name", "supplier_name", "mgk_tamil_name"],
				limit_page_length=0,
			)
		}

	item_ids = {row.item_name for row in rows if row.item_name}
	item_names = {}
	if item_ids:
		item_names = {
			row.name: row
			for row in frappe.get_list(
				"Item",
				filters={"name": ["in", list(item_ids)]},
				fields=["name", "name1", "mgk_tamil_name"],
				limit_page_length=0,
			)
		}

	uom_totals = {}
	for row in rows:
		warehouse_row = warehouse_map.get(row.warehouse) or frappe._dict()
		supplier_row = supplier_names.get(warehouse_row.get("supplier")) or frappe._dict()
		item_row = item_names.get(row.item_name) or frappe._dict()
		row.update(
			warehouse_name=warehouse_row.get("name1") or row.warehouse,
			warehouse_tamil_name=warehouse_row.get("mgk_tamil_name"),
			supplier=warehouse_row.get("supplier"),
			supplier_name=supplier_row.get("supplier_name"),
			supplier_tamil_name=supplier_row.get("mgk_tamil_name"),
			item_display_name=item_row.get("name1") or row.item_name,
			item_tamil_name=item_row.get("mgk_tamil_name"),
		)
		uom = row.stock_uom or "Units"
		uom_totals[uom] = flt(uom_totals.get(uom)) + flt(row.bal_qty)

	return {
		"filters": {"from_date": str(from_date), "to_date": str(to_date)},
		"options": _options(warehouses),
		"rows": rows,
		"summary": {
			"line_count": len(rows),
			"warehouse_count": len({row.warehouse for row in rows}),
			"total_value": flt(sum(flt(row.bal_val) for row in rows), 2),
			"uom_totals": uom_totals,
		},
	}
