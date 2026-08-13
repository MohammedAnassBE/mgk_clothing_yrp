"""Add MGK-only Item and Purchase Order book-classification fields."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


CUSTOM_FIELDS = {
	"Item": [
		{
			"fieldname": "mgk_is_karigan",
			"fieldtype": "Check",
			"label": "Is Karigan",
			"insert_after": "is_yarn_item",
			"default": "0",
			"module": "MGK Clothing YRP",
			"description": "Allow this Item in MGK Karigan Purchase Orders.",
		},
		{
			"fieldname": "mgk_is_salavai_cone",
			"fieldtype": "Check",
			"label": "Is Salavai Cone",
			"insert_after": "mgk_is_karigan",
			"default": "0",
			"module": "MGK Clothing YRP",
			"description": "Allow this Item in MGK Salavai Cone Purchase Orders.",
		},
	],
	"Purchase Order": [
		{
			"fieldname": "mgk_is_karigan_order",
			"fieldtype": "Check",
			"label": "Is Karigan Order",
			"insert_after": "mgk_handling_supplier",
			"default": "0",
			"in_standard_filter": 1,
			"module": "MGK Clothing YRP",
			"description": "Classifies this Purchase Order in the Karigan Order Book.",
		},
		{
			"fieldname": "mgk_is_salavai_cone_order",
			"fieldtype": "Check",
			"label": "Is Salavai Cone Order",
			"insert_after": "mgk_is_karigan_order",
			"default": "0",
			"in_standard_filter": 1,
			"module": "MGK Clothing YRP",
			"description": "Classifies this Purchase Order in the Salavai Cone Order Book.",
		},
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.clear_cache(doctype="Item")
	frappe.clear_cache(doctype="Purchase Order")
