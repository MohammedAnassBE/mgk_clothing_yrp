"""MGK Purchase Order queries used by the registered `/web` experience."""

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime


@frappe.whitelist()
def get_previous_purchase_prices(item_details, supplier=None, current_purchase_order=None):
	"""Return the latest earlier submitted PO rate for each grouped item cell."""
	if not frappe.has_permission("Purchase Order", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if isinstance(item_details, str):
		try:
			item_details = json.loads(item_details or "[]")
		except (TypeError, ValueError):
			frappe.throw(_("Invalid item details format"))
	if not isinstance(item_details, list) or not item_details:
		return {}

	current = None
	if current_purchase_order:
		current = frappe.get_doc("Purchase Order", current_purchase_order)
		current.check_permission("read")
		supplier = current.supplier
	if not supplier:
		return {}

	variant_by_key = _resolve_previous_price_variants(item_details)
	if not variant_by_key:
		return {}

	orders = frappe.get_list(
		"Purchase Order",
		filters={"supplier": supplier, "docstatus": 1},
		fields=["name", "po_date", "creation"],
		order_by="po_date desc, creation desc",
		limit_page_length=0,
	)
	if current:
		current_date = getdate(current.po_date)
		current_creation = get_datetime(current.creation)
		orders = [
			row
			for row in orders
			if row.name != current.name
			and (
				getdate(row.po_date) < current_date
				or (
					getdate(row.po_date) == current_date
					and get_datetime(row.creation) < current_creation
				)
			)
		]
	if not orders:
		return {}

	order_rank = {row.name: index for index, row in enumerate(orders)}
	order_dates = {row.name: row.po_date for row in orders}
	rows = frappe.get_all(
		"Purchase Order Item",
		filters={
			"parent": ["in", list(order_rank)],
			"item_variant": ["in", sorted(set(variant_by_key.values()))],
		},
		fields=["parent", "item_variant", "rate", "idx"],
		limit_page_length=0,
	)
	rows.sort(key=lambda row: (order_rank.get(row.parent, len(order_rank)), row.idx or 0))

	latest_by_variant = {}
	for row in rows:
		latest_by_variant.setdefault(
			row.item_variant,
			{
				"rate": flt(row.rate),
				"purchase_order": row.parent,
				"po_date": order_dates.get(row.parent),
			},
		)

	return {
		key: latest_by_variant[variant]
		for key, variant in variant_by_key.items()
		if variant in latest_by_variant
	}


def _resolve_previous_price_variants(item_details):
	"""Resolve grouped editor cells to existing variants without creating any."""
	from yrp.yrp.doctype.item.item import get_variant

	variant_by_key = {}
	for group_index, group in enumerate(item_details or []):
		for item_index, item in enumerate(group.get("items") or []):
			parent_item = item.get("name")
			if not parent_item:
				continue
			base_attributes = {
				key: value
				for key, value in (item.get("attributes") or {}).items()
				if value
			}
			values = item.get("values") or {}
			primary_attribute = item.get("primary_attribute")
			for value_key, value in values.items():
				if not flt((value or {}).get("qty")):
					continue
				attributes = dict(base_attributes)
				if primary_attribute and value_key != "default":
					attributes[primary_attribute] = value_key
				variant = get_variant(parent_item, attributes)
				if variant:
					variant_by_key[f"{group_index}:{item_index}:{value_key}"] = variant
	return variant_by_key
