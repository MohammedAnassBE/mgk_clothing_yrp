"""Detach existing MGK IPD attribute mappings from their Item masters."""

import frappe

from mgk_clothing_yrp.yarn_process import ensure_ipd_attribute_mappings


def execute():
	for name in frappe.get_all("Item Production Detail", pluck="name"):
		doc = frappe.get_doc("Item Production Detail", name)
		if ensure_ipd_attribute_mappings(doc):
			doc.save(ignore_permissions=True)
