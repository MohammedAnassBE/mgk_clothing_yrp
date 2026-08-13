from types import SimpleNamespace

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, nowdate, nowtime

from mgk_clothing_yrp.mgk_clothing_yrp.api.work_order import (
	_matrix_variant_attributes,
	_prepare_yarn_transformation_items,
	calculate_deliverables,
	get_yarn_deliverable_rows,
)
from mgk_clothing_yrp.mgk_clothing_yrp.api.item_attribute import (
	update_ipd_mapping_values,
)
from mgk_clothing_yrp.mgk_clothing_yrp.api.bom_mapping import (
	create_mapping,
	get_mapping_context,
)
from mgk_clothing_yrp.mgk_clothing_yrp.api.experiences.operations_workspace.item_production_detail import (
	approve as approve_ipd,
	get_entry_context,
	regenerate_matrix,
	reject as reject_ipd,
)
from mgk_clothing_yrp.yarn_process import (
	build_route_io,
	get_item_attribute_options,
	get_process_route_context,
	load_attribute_list,
	regenerate_process_matrices,
)
from yrp.yrp.utils.ipd_engine import _lookup_mode_b


class TestYarnProcessFlow(FrappeTestCase):
	def setUp(self):
		suffix = frappe.generate_hash(length=8)
		colour_mapping = self._make_mapping(
			"Colour",
			["Orange", "Blue", "Green"],
		)
		size_mapping = self._make_mapping(
			"Size",
			["M", "L"],
		)
		self.yarn_40 = self._make_item(
			f"_Test 40s Yarn {suffix}",
			"Yarn Item Group",
			"Kg",
			[{"attribute": "Colour", "mapping": colour_mapping}],
			is_yarn_item=1,
		)
		self.yarn_60 = self._make_item(
			f"_Test 60s Yarn {suffix}",
			"Yarn Item Group",
			"Kg",
			[{"attribute": "Colour", "mapping": colour_mapping}],
			is_yarn_item=1,
		)
		self.yarn_80 = self._make_item(
			f"_Test 80s Yarn {suffix}",
			"Yarn Item Group",
			"Kg",
			[{"attribute": "Colour", "mapping": colour_mapping}],
			is_yarn_item=1,
		)
		self.towel = self._make_item(
			f"_Test Towel {suffix}",
			"Products",
			"Pieces",
			[
				{"attribute": "Colour", "mapping": colour_mapping},
				{"attribute": "Size", "mapping": size_mapping},
			],
			primary_attribute="Size",
		)
		self.doubling = self._make_process(
			f"_Test Doubling {suffix}",
			is_item_conversion=1,
		)
		self.dyeing = self._make_process(
			f"_Test Dyeing {suffix}",
			is_item_conversion=0,
			value_change_attributes=[{"attribute": "Colour"}],
		)
		self.washing = self._make_process(
			f"_Test Washing {suffix}",
			is_item_conversion=0,
		)

	def _make_mapping(self, attribute, values):
		mapping = frappe.get_doc({
			"doctype": "Item Item Attribute Mapping",
			"attribute_name": attribute,
			"values": [
				{"attribute_value": value}
				for value in values
			],
		})
		mapping.insert(ignore_permissions=True)
		return mapping.name

	def _make_item(
		self,
		name,
		item_group,
		uom,
		attributes,
		is_yarn_item=0,
		primary_attribute=None,
	):
		item = frappe.get_doc({
			"doctype": "Item",
			"name1": name,
			"item_group": item_group,
			"default_unit_of_measure": uom,
			"is_stock_item": 1,
			"is_yarn_item": is_yarn_item,
			"primary_attribute": primary_attribute,
			"attributes": attributes,
		})
		item.insert(ignore_permissions=True)
		return item.name

	def _make_process(self, name, **values):
		process = frappe.get_doc({
			"doctype": "Process",
			"process_name": name,
			"is_yarn_process": 1,
			"input_uom": "Kg",
			"output_uom": "Kg",
			**values,
		})
		process.insert(ignore_permissions=True)
		return process.name

	def _make_supplier(self, label, is_company_location=0):
		supplier = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": f"{label} {frappe.generate_hash(length=6)}",
			"is_company_location": is_company_location,
		})
		supplier.insert(ignore_permissions=True)
		return supplier.name

	def _make_warehouse(self, supplier, label):
		warehouse = frappe.get_doc({
			"doctype": "Warehouse",
			"name1": f"{label} {frappe.generate_hash(length=6)}",
			"supplier": supplier,
		})
		warehouse.insert(ignore_permissions=True)
		return warehouse.name

	def _make_address(self, label):
		address = frappe.get_doc({
			"doctype": "Address",
			"address_title": f"{label} {frappe.generate_hash(length=6)}",
			"address_type": "Office",
			"address_line1": "Test Address",
			"city": "Test City",
			"country": "India",
		})
		address.insert(ignore_permissions=True)
		return address.name

	def _ensure_received_type(self):
		if not frappe.db.exists("Received Type", "Accepted"):
			frappe.get_doc({
				"doctype": "Received Type",
				"received_type_name": "Accepted",
				"is_default": 1,
			}).insert(ignore_permissions=True)
		frappe.db.set_single_value(
			"YRP Stock Settings",
			"default_received_type",
			"Accepted",
		)

	def _ensure_tax_slab(self):
		if not frappe.db.exists("Tax Slab", "0"):
			frappe.get_doc({
				"doctype": "Tax Slab",
				"percentage": "0",
				"enabled": 1,
			}).insert(ignore_permissions=True)
		return "0"

	def _approve_workflow_doc(self, doc):
		doc.insert(ignore_permissions=True)
		apply_workflow(doc, "Submit")
		return apply_workflow(doc, "Approve")

	def _make_item_price(self, item, supplier, rate=25):
		return self._approve_workflow_doc(frappe.get_doc({
			"doctype": "Item Price",
			"item_name": item,
			"supplier": supplier,
			"uom": frappe.db.get_value(
				"Item",
				item,
				"default_unit_of_measure",
			),
			"from_date": "2000-01-01",
			"tax": self._ensure_tax_slab(),
			"item_price_values": [{
				"moq": 0,
				"price": rate,
				"lead_time": 0,
			}],
		}))

	def _make_process_cost(self, process_name, item, supplier, rate=12):
		return self._approve_workflow_doc(frappe.get_doc({
			"doctype": "Process Cost",
			"item": item,
			"uom": frappe.db.get_value(
				"Item",
				item,
				"default_unit_of_measure",
			),
			"supplier": supplier,
			"process_name": process_name,
			"from_date": "2000-01-01",
			"tax_slab": self._ensure_tax_slab(),
			"process_cost_values": [{
				"min_order_qty": 0,
				"price": rate,
			}],
		}))

	def _make_delivery_challan(self, work_order):
		deliverable = work_order.deliverables[0]
		delivery_challan = frappe.get_doc({
			"doctype": "Delivery Challan",
			"work_order": work_order.name,
			"from_location": work_order.delivery_location,
			"supplier": work_order.supplier,
			"process_name": work_order.process_name,
			"item": work_order.item,
			"items": [{
				"item_variant": deliverable.item_variant,
				"qty": deliverable.qty,
				"delivered_quantity": deliverable.qty,
				"uom": deliverable.uom,
				"stock_uom": deliverable.uom,
				"conversion_factor": 1,
				"ref_doctype": "Work Order Deliverables",
				"ref_docname": deliverable.name,
				"table_index": 0,
				"row_index": "0",
			}],
		})
		delivery_challan.insert(ignore_permissions=True)
		delivery_challan.submit()
		return delivery_challan

	def _make_work_order_grn(self, work_order, delivery_challan):
		receivable = work_order.receivables[0]
		grn = frappe.get_doc({
			"doctype": "Goods Received Note",
			"against": "Work Order",
			"against_id": work_order.name,
			"delivery_challan": delivery_challan.name,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
			"item": work_order.item,
			"items": [{
				"item_variant": receivable.item_variant,
				"quantity": receivable.qty,
				"uom": receivable.uom,
				"stock_uom": receivable.uom,
				"conversion_factor": 1,
				"received_type": "Accepted",
				"ref_doctype": "Work Order Receivables",
				"ref_docname": receivable.name,
				"table_index": 0,
				"row_index": "0",
			}],
		})
		grn.insert(ignore_permissions=True)
		grn.submit()
		return grn

	def _make_ipd(self, routes):
		ipd = frappe.get_doc({
			"doctype": "Item Production Detail",
			"item": self.towel,
			"mgk_yarn_process_routes": routes,
		})
		ipd.insert(ignore_permissions=True)
		return ipd

	def _calculate_work_order(
		self,
		ipd,
		process_name,
		route_name,
		attribute_values,
		qty=100,
	):
		if not frappe.db.exists("IPD Process Matrix", {"ipd": ipd.name}):
			regenerate_process_matrices(ipd)
		supplier = frappe.db.get_value("Supplier", {}, "name")
		address = frappe.db.get_value("Address", {}, "name")
		wo = frappe.get_doc({
			"doctype": "Work Order",
			"naming_series": "WO-",
			"wo_date": nowdate(),
			"supplier": supplier,
			"delivery_location": supplier,
			"supplier_address": address,
			"delivery_address": address,
			"planned_start_date": nowdate(),
			"planned_end_date": add_days(nowdate(), 1),
			"process_name": process_name,
			"production_detail": ipd.name,
			"mgk_items": [
				{"item": ipd.item, "production_detail": ipd.name}
			],
		})
		wo.insert(ignore_permissions=True)
		calculate_deliverables(
			wo.name,
			[
				{
					"production_detail": ipd.name,
					"route_name": route_name,
					"attribute_values": attribute_values,
					"weight": qty,
				}
			],
			modified=wo.modified,
		)
		return frappe.get_doc("Work Order", wo.name)

	def test_doubling_then_dyeing_carries_intermediate_item(self):
		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
			{
				"sequence": 20,
				"process_name": self.dyeing,
				"input_item": self.yarn_80,
				"output_item": self.yarn_80,
				"from_colour": "Orange",
				"to_colour": "Blue",
				"quantity_ratio": 1,
			},
		])

		self.assertEqual(ipd.yarn_item, self.yarn_40)
		self.assertEqual(
			[row.attribute for row in ipd.item_attributes],
			["Colour", "Size"],
		)
		self.assertEqual(
			frappe.db.count("IPD Process Matrix", {"ipd": ipd.name}),
			0,
		)
		matrices = regenerate_process_matrices(ipd)
		self.assertEqual(len(matrices), 2)
		self.assertEqual(
			set(
				frappe.get_all(
					"IPD Process Matrix",
					filters={"ipd": ipd.name},
					pluck="process_name",
				)
			),
			{self.doubling, self.dyeing},
		)

		doubling_route = ipd.mgk_yarn_process_routes[0]
		doubling_io = build_route_io(
			ipd,
			self.doubling,
			doubling_route.name,
			{"Colour": "Orange"},
			100,
		)
		self.assertEqual(doubling_io["input_item"], self.yarn_40)
		self.assertEqual(doubling_io["output_item"], self.yarn_80)
		self.assertEqual(doubling_io["output_attrs"], {"Colour": "Orange"})
		self.assertEqual(doubling_io["output_qty"], 100)

		dyeing_context = get_process_route_context(ipd.name, self.dyeing)
		self.assertEqual(len(dyeing_context), 1)
		self.assertEqual(dyeing_context[0]["input_item"], self.yarn_80)
		self.assertEqual(dyeing_context[0]["from_colour"], "Orange")
		self.assertEqual(dyeing_context[0]["to_colour"], "Blue")

		doubling_wo = self._calculate_work_order(
			ipd,
			self.doubling,
			doubling_route.name,
			{"Colour": "Orange"},
		)
		dyeing_wo = self._calculate_work_order(
			ipd,
			self.dyeing,
			ipd.mgk_yarn_process_routes[1].name,
			{},
		)
		self.assertEqual(
			doubling_wo.receivables[0].item_variant,
			dyeing_wo.deliverables[0].item_variant,
		)

	def test_process_catalog_and_washing_are_driven_by_value_change_attributes(self):
		catalog = get_entry_context()
		processes = {row["name"]: row for row in catalog["processes"]}
		self.assertEqual(
			processes[self.dyeing]["value_change_attributes"],
			["Colour"],
		)
		self.assertEqual(
			processes[self.washing]["value_change_attributes"],
			[],
		)

		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.washing,
				"input_item": self.yarn_40,
				"output_item": self.yarn_40,
				"quantity_ratio": 1,
			},
		])
		route = ipd.mgk_yarn_process_routes[0]
		context = get_process_route_context(ipd.name, self.washing)
		self.assertEqual(len(context), 1)
		self.assertEqual(context[0]["transformation_type"], "Pass Through")
		self.assertEqual(
			[attribute["attribute"] for attribute in context[0]["attributes"]],
			["Colour"],
		)

		io = build_route_io(
			ipd,
			self.washing,
			route.name,
			{"Colour": "Orange"},
			100,
		)
		self.assertEqual(io["input_attrs"], {"Colour": "Orange"})
		self.assertEqual(io["output_attrs"], {"Colour": "Orange"})

		matrix_name = regenerate_process_matrices(ipd)[0]
		matrix = frappe.get_doc("IPD Process Matrix", matrix_name)
		matrix_values = {
			(row.group_index, row.side, row.attribute): row.attribute_value
			for row in matrix.combination_attributes
		}
		self.assertEqual(matrix_values[(1, "Input", "Colour")], "Orange")
		self.assertEqual(matrix_values[(1, "Output", "Colour")], "Orange")

	def test_washing_matrix_and_work_order_use_only_previous_dyeing_outputs(self):
		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.dyeing,
				"input_item": self.yarn_40,
				"output_item": self.yarn_40,
				"from_colour": "Orange",
				"to_colour": "Blue",
				"quantity_ratio": 1,
			},
			{
				"sequence": 10,
				"process_name": self.dyeing,
				"input_item": self.yarn_40,
				"output_item": self.yarn_40,
				"from_colour": "Orange",
				"to_colour": "Green",
				"quantity_ratio": 1,
			},
			{
				"sequence": 20,
				"process_name": self.washing,
				"input_item": self.yarn_40,
				"output_item": self.yarn_40,
				"quantity_ratio": 1,
			},
		])
		washing_route = next(
			row
			for row in ipd.mgk_yarn_process_routes
			if row.process_name == self.washing
		)

		# Finished-Item values are context, not a reason to discard intermediate
		# Yarn colours produced by Dyeing.
		colour_mapping = next(
			row.mapping for row in ipd.item_attributes if row.attribute == "Colour"
		)
		update_ipd_mapping_values(
			ipd.name,
			"Colour",
			["Orange"],
			mapping=colour_mapping,
		)
		ipd.reload()

		matrices = regenerate_process_matrices(ipd)
		self.assertEqual(len(matrices), 2)
		washing_matrix = frappe.get_doc(
			"IPD Process Matrix",
			frappe.db.get_value(
				"IPD Process Matrix",
				{"ipd": ipd.name, "process_name": self.washing},
			),
		)
		matrix_colours = {
			(row.side, row.attribute_value)
			for row in washing_matrix.combination_attributes
			if row.attribute == "Colour"
		}
		self.assertEqual(
			matrix_colours,
			{
				("Input", "Blue"),
				("Output", "Blue"),
				("Input", "Green"),
				("Output", "Green"),
			},
		)

		context = get_process_route_context(ipd.name, self.washing)
		self.assertEqual(len(context), 1)
		self.assertTrue(context[0]["chain_constrained"])
		self.assertEqual(
			context[0]["attributes"],
			[
				{
					"attribute": "Colour",
					"label": "Colour",
					"options": ["Blue", "Green"],
				}
			],
		)
		with self.assertRaisesRegex(
			frappe.ValidationError,
			"not produced by the previous Process",
		):
			build_route_io(
				ipd,
				self.washing,
				washing_route.name,
				{"Colour": "Orange"},
				100,
			)

		supplier = frappe.db.get_value("Supplier", {}, "name")
		address = frappe.db.get_value("Address", {}, "name")
		popup_work_order = frappe.get_doc({
			"doctype": "Work Order",
			"naming_series": "WO-",
			"wo_date": nowdate(),
			"supplier": supplier,
			"delivery_location": supplier,
			"supplier_address": address,
			"delivery_address": address,
			"planned_start_date": nowdate(),
			"planned_end_date": add_days(nowdate(), 1),
			"process_name": self.washing,
			"production_detail": ipd.name,
		})
		popup_work_order.insert(ignore_permissions=True)
		popup = get_yarn_deliverable_rows(popup_work_order.name)
		self.assertEqual(
			popup["options"][0]["rows"][0]["attributes"][0]["options"],
			["Blue", "Green"],
		)

		washing_wo = self._calculate_work_order(
			ipd,
			self.washing,
			washing_route.name,
			{"Colour": "Blue"},
		)
		self.assertEqual(
			_matrix_variant_attributes(washing_wo.deliverables[0].item_variant),
			{"Colour": "Blue"},
		)
		self.assertEqual(
			_matrix_variant_attributes(washing_wo.receivables[0].item_variant),
			{"Colour": "Blue"},
		)

	def test_ipd_onload_exposes_finished_item_attribute_values(self):
		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])

		load_attribute_list(ipd)
		attributes = {
			row["attr_name"]: [
				value["attribute_value"]
				for value in row["attr_values"]
			]
			for row in ipd.get_onload()["attr_list"]
		}
		self.assertEqual(
			attributes["Colour"],
			["Orange", "Blue", "Green"],
		)
		self.assertEqual(attributes["Size"], ["M", "L"])

	def test_ipd_approval_and_manual_matrix_regeneration(self):
		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])

		manual_state = regenerate_matrix(ipd.name, modified=ipd.modified)
		self.assertEqual(manual_state["approval_status"], "Not Approved")
		self.assertEqual(manual_state["matrix_count"], 1)

		ipd.reload()
		approved_state = approve_ipd(ipd.name, modified=ipd.modified)
		self.assertEqual(approved_state["approval_status"], "Approved")
		self.assertEqual(approved_state["approved_by"], frappe.session.user)
		self.assertEqual(approved_state["matrix_count"], 1)

		ipd.reload()
		rejected_state = reject_ipd(ipd.name, modified=ipd.modified)
		self.assertEqual(rejected_state["approval_status"], "Not Approved")
		self.assertIsNone(rejected_state["approved_by"])
		self.assertEqual(rejected_state["matrix_count"], 1)

	def test_approved_ipd_locks_definition_and_bom_combinations(self):
		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])
		ipd.append("item_bom", {
			"item": self.yarn_40,
			"qty_of_product": 1,
			"qty_of_bom_item": 2,
			"uom": "Kg",
		})
		ipd.save(ignore_permissions=True)
		ipd.reload()
		mapping_name = create_mapping(
			ipd.name,
			bom_row=ipd.item_bom[0].name,
		)

		# Approval fields cannot be forged through a normal document save.
		ipd.reload()
		ipd.approval_status = "Approved"
		with self.assertRaisesRegex(frappe.ValidationError, "Use the Approve IPD"):
			ipd.save(ignore_permissions=True)

		ipd.reload()
		approve_ipd(ipd.name, modified=ipd.modified)
		ipd.reload()

		ipd.mgk_yarn_process_routes[0].quantity_ratio = 2
		with self.assertRaisesRegex(frappe.ValidationError, "Approved and locked"):
			ipd.save(ignore_permissions=True)

		colour_mapping = next(
			row.mapping for row in ipd.item_attributes if row.attribute == "Colour"
		)
		with self.assertRaisesRegex(frappe.ValidationError, "Approved and locked"):
			update_ipd_mapping_values(
				ipd.name,
				"Colour",
				["Orange"],
				mapping=colour_mapping,
			)

		bom_mapping = frappe.get_doc(
			"Item BOM Attribute Mapping", mapping_name
		)
		bom_mapping.item_attributes[0].same_attribute = 1
		bom_mapping.flags.ignore_validate = True
		with self.assertRaisesRegex(frappe.ValidationError, "Approved and locked"):
			bom_mapping.save(ignore_permissions=True)

		matrix = frappe.get_doc(
			"IPD Process Matrix",
			frappe.db.get_value("IPD Process Matrix", {"ipd": ipd.name}),
		)
		matrix.combinations[0].quantity = 2
		with self.assertRaisesRegex(frappe.ValidationError, "Approved and locked"):
			matrix.save(ignore_permissions=True)

		ipd.reload()
		with self.assertRaisesRegex(frappe.ValidationError, "Approved and locked"):
			regenerate_matrix(ipd.name, modified=ipd.modified)
		with self.assertRaisesRegex(frappe.ValidationError, "Approved and locked"):
			frappe.delete_doc(
				"Item Production Detail",
				ipd.name,
				ignore_permissions=True,
			)

		# Rejection is the one supported unlock transition.
		ipd.reload()
		reject_ipd(ipd.name, modified=ipd.modified)
		ipd.reload()
		ipd.mgk_yarn_process_routes[0].quantity_ratio = 2
		ipd.save(ignore_permissions=True)
		self.assertEqual(ipd.approval_status, "Not Approved")
		self.assertEqual(ipd.mgk_yarn_process_routes[0].quantity_ratio, 2)

	def test_draft_calculation_without_cost_or_ipd_approval_returns_warnings(self):
		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])
		regenerate_process_matrices(ipd)
		supplier = frappe.db.get_value("Supplier", {}, "name")
		address = frappe.db.get_value("Address", {}, "name")
		work_order = frappe.get_doc(
			{
				"doctype": "Work Order",
				"naming_series": "WO-",
				"wo_date": nowdate(),
				"supplier": supplier,
				"delivery_location": supplier,
				"supplier_address": address,
				"delivery_address": address,
				"planned_start_date": nowdate(),
					"planned_end_date": add_days(nowdate(), 1),
					"process_name": self.doubling,
					"production_detail": ipd.name,
					"mgk_items": [
					{"item": ipd.item, "production_detail": ipd.name}
				],
			}
		)
		work_order.insert(ignore_permissions=True)

		result = calculate_deliverables(
			work_order.name,
			[
				{
					"production_detail": ipd.name,
					"route_name": ipd.mgk_yarn_process_routes[0].name,
					"attribute_values": {"Colour": "Orange"},
					"weight": 25,
				}
			],
			modified=work_order.modified,
		)
		work_order.reload()

		self.assertEqual(work_order.docstatus, 0)
		self.assertEqual(len(work_order.deliverables), 1)
		self.assertEqual(len(work_order.receivables), 1)
		self.assertTrue(any("not Approved" in issue for issue in result["warnings"]))
		self.assertTrue(any("No approved Process Cost" in issue for issue in result["warnings"]))

	def test_work_order_production_detail_drives_popup_and_calculation(self):
		"""The Work Order field owns IPD context; the popup only enters quantities."""
		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])
		regenerate_process_matrices(ipd)
		supplier = frappe.db.get_value("Supplier", {}, "name")
		address = frappe.db.get_value("Address", {}, "name")
		work_order = frappe.get_doc({
			"doctype": "Work Order",
			"naming_series": "WO-",
			"wo_date": nowdate(),
			"supplier": supplier,
			"delivery_location": supplier,
			"supplier_address": address,
			"delivery_address": address,
			"planned_start_date": nowdate(),
			"planned_end_date": add_days(nowdate(), 1),
			"process_name": self.doubling,
			"production_detail": ipd.name,
		})
		work_order.insert(ignore_permissions=True)
		self.assertEqual(work_order.item, self.towel)

		context = get_yarn_deliverable_rows(work_order.name)
		matching = [
			option
			for option in context["options"]
			if option["production_detail"] == ipd.name
		]
		self.assertEqual(context["mode"], "transformation")
		self.assertEqual(context["selected_production_details"], [ipd.name])
		self.assertEqual(len(context["options"]), 1)
		self.assertEqual(len(matching), 1)
		self.assertEqual(matching[0]["item"], self.towel)
		self.assertEqual(matching[0]["rows"][0]["route_name"], ipd.mgk_yarn_process_routes[0].name)
		self.assertEqual(
			{
				row["attribute"]: row["values"]
				for row in matching[0]["ipd_attributes"]
			},
			{
				"Colour": ["Orange", "Blue", "Green"],
				"Size": ["M", "L"],
			},
		)

		result = calculate_deliverables(
			work_order.name,
			[
				{
					"production_detail": ipd.name,
					"route_name": ipd.mgk_yarn_process_routes[0].name,
					"attribute_values": {"Colour": "Orange"},
					"weight": 25,
				},
				{
					"production_detail": ipd.name,
					"route_name": ipd.mgk_yarn_process_routes[0].name,
					"attribute_values": {"Colour": "Blue"},
					"weight": 10,
				},
			],
			modified=work_order.modified,
		)
		work_order.reload()

		self.assertEqual(
			[(row.item, row.production_detail) for row in work_order.mgk_items],
			[(self.towel, ipd.name)],
		)
		self.assertEqual(len(work_order.deliverables), 2)
		self.assertEqual(len(work_order.receivables), 2)
		self.assertEqual(
			{
				_matrix_variant_attributes(row.item_variant)["Colour"]: row.qty
				for row in work_order.deliverables
			},
			{"Orange": 25, "Blue": 10},
		)
		self.assertEqual(result["mode"], "transformation")

	def test_calculation_rejects_ipd_other_than_work_order_production_detail(self):
		selected_ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])
		other_ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.dyeing,
				"input_item": self.yarn_80,
				"output_item": self.yarn_80,
				"from_colour": "Orange",
				"to_colour": "Blue",
				"quantity_ratio": 1,
			},
		])
		supplier = frappe.db.get_value("Supplier", {}, "name")
		address = frappe.db.get_value("Address", {}, "name")
		work_order = frappe.get_doc({
			"doctype": "Work Order",
			"naming_series": "WO-",
			"wo_date": nowdate(),
			"supplier": supplier,
			"delivery_location": supplier,
			"supplier_address": address,
			"delivery_address": address,
			"planned_start_date": nowdate(),
			"planned_end_date": add_days(nowdate(), 1),
			"process_name": self.doubling,
			"production_detail": selected_ipd.name,
		})
		work_order.insert(ignore_permissions=True)

		with self.assertRaisesRegex(frappe.ValidationError, "must match Work Order"):
			calculate_deliverables(
				work_order.name,
				[{
					"production_detail": other_ipd.name,
					"route_name": other_ipd.mgk_yarn_process_routes[0].name,
					"attribute_values": {},
					"weight": 25,
				}],
				modified=work_order.modified,
			)
		work_order.reload()
		self.assertEqual(work_order.mgk_items, [])
		self.assertEqual(work_order.production_detail, selected_ipd.name)

	def test_ipd_attribute_values_are_isolated_from_item_master(self):
		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])
		other_ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])

		item = frappe.get_doc("Item", self.towel)
		item_colour_mapping = next(
			row.mapping for row in item.attributes if row.attribute == "Colour"
		)
		ipd_colour_mapping = next(
			row.mapping for row in ipd.item_attributes if row.attribute == "Colour"
		)
		other_ipd_colour_mapping = next(
			row.mapping
			for row in other_ipd.item_attributes
			if row.attribute == "Colour"
		)

		self.assertNotEqual(ipd_colour_mapping, item_colour_mapping)
		self.assertNotEqual(other_ipd_colour_mapping, item_colour_mapping)
		self.assertNotEqual(ipd_colour_mapping, other_ipd_colour_mapping)

		update_ipd_mapping_values(
			ipd.name,
			"Colour",
			["Orange"],
			mapping=ipd_colour_mapping,
		)

		self.assertEqual(
			[
				row.attribute_value
				for row in frappe.get_doc(
					"Item Item Attribute Mapping", ipd_colour_mapping
				).values
			],
			["Orange"],
		)
		for unchanged_mapping in (
			item_colour_mapping,
			other_ipd_colour_mapping,
		):
			self.assertEqual(
				[
					row.attribute_value
					for row in frappe.get_doc(
						"Item Item Attribute Mapping", unchanged_mapping
					).values
				],
				["Orange", "Blue", "Green"],
			)

	def test_ipd_bom_mapping_is_created_from_the_saved_child_row(self):
		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])
		ipd.append("item_bom", {
			"item": self.yarn_40,
			"qty_of_product": 1,
			"qty_of_bom_item": 2,
			"uom": "Kg",
		})
		ipd.save(ignore_permissions=True)
		ipd.reload()
		bom_row = ipd.item_bom[0]

		# The saved child row is authoritative: a tampered client-side bom_item
		# argument must not redirect the mapping to a different Item.
		mapping_name = create_mapping(
			ipd.name,
			bom_item=self.yarn_60,
			bom_row=bom_row.name,
		)
		mapping = frappe.get_doc("Item BOM Attribute Mapping", mapping_name)
		ipd.reload()
		bom_row = ipd.item_bom[0]

		self.assertEqual(mapping.item, self.towel)
		self.assertEqual(mapping.bom_item, self.yarn_40)
		self.assertEqual(
			[row.attribute for row in mapping.item_attributes],
			["Colour", "Size"],
		)
		self.assertEqual(
			[row.attribute for row in mapping.bom_item_attributes],
			["Colour"],
		)
		self.assertEqual(bom_row.based_on_attribute_mapping, 1)
		self.assertEqual(bom_row.attribute_mapping, mapping_name)
		self.assertEqual(
			get_mapping_context(mapping_name),
			{
				"ipd": ipd.name,
				"item": self.towel,
				"item_attributes": ["Colour", "Size"],
				"item_attribute_values": {
					"Colour": ["Orange", "Blue", "Green"],
					"Size": ["M", "L"],
				},
			},
		)

		# Re-opening Manage combinations must reuse the same mapping.
		self.assertEqual(
			create_mapping(ipd.name, bom_row=bom_row.name),
			mapping_name,
		)

	def test_base_yrp_bom_mapping_copies_same_attribute_to_bom(self):
		mapping = SimpleNamespace(
			item_attributes=[
				frappe._dict(attribute="Size", same_attribute=0),
				frappe._dict(attribute="Colour", same_attribute=1),
			],
			bom_item_attributes=[
				frappe._dict(attribute="Colour", same_attribute=1),
			],
			values=[
				frappe._dict(
					index=0,
					type="item",
					attribute="Size",
					attribute_value="M",
					quantity=1.25,
				),
			],
		)

		self.assertEqual(
			_lookup_mode_b(mapping, {"Size": "M", "Colour": "Orange"}),
			{
				"qty_of_bom_item": 1.25,
				"bom_attrs": {"Colour": "Orange"},
			},
		)

	def test_ipd_bom_mapping_rejects_a_child_row_from_another_ipd(self):
		first_ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])
		first_ipd.append("item_bom", {
			"item": self.yarn_40,
			"qty_of_product": 1,
			"qty_of_bom_item": 1,
			"uom": "Kg",
		})
		first_ipd.save(ignore_permissions=True)
		first_ipd.reload()
		second_ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])

		with self.assertRaises(frappe.ValidationError):
			create_mapping(
				second_ipd.name,
				bom_row=first_ipd.item_bom[0].name,
			)

	def test_one_dyeing_step_can_output_multiple_colours(self):
		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.dyeing,
				"input_item": self.yarn_40,
				"output_item": self.yarn_40,
				"from_colour": "Orange",
				"to_colour": "Blue",
				"quantity_ratio": 1,
			},
			{
				"sequence": 10,
				"process_name": self.dyeing,
				"input_item": self.yarn_40,
				"output_item": self.yarn_40,
				"from_colour": "Orange",
				"to_colour": "Green",
				"quantity_ratio": 1,
			},
		])

		context = get_process_route_context(ipd.name, self.dyeing)
		self.assertEqual(len(context), 2)
		self.assertEqual(
			{(row["from_colour"], row["to_colour"]) for row in context},
			{("Orange", "Blue"), ("Orange", "Green")},
		)

		wo = frappe._dict(
			name="_Test Multi Colour Dyeing WO",
			process_name=self.dyeing,
			production_detail=ipd.name,
			mgk_items=[frappe._dict(production_detail=ipd.name)],
		)
		regenerate_process_matrices(ipd)
		deliverables, receivables = _prepare_yarn_transformation_items(
			wo,
			[
				{
					"production_detail": ipd.name,
					"route_name": context[0]["route_name"],
					"attribute_values": {},
					"weight": 60,
				},
				{
					"production_detail": ipd.name,
					"route_name": context[1]["route_name"],
					"attribute_values": {},
					"weight": 40,
				},
			],
		)
		self.assertEqual(len(deliverables), 1)
		self.assertEqual(deliverables[0]["qty"], 100)
		self.assertEqual(
			{
				_matrix_variant_attributes(row["item_variant"])["Colour"]: row["qty"]
				for row in receivables
			},
			{"Blue": 60, "Green": 40},
		)

	def test_empty_item_colour_mapping_uses_all_colour_master_values(self):
		suffix = frappe.generate_hash(length=8)
		fallback_colours = [
			f"_Test Fallback A {suffix}",
			f"_Test Fallback B {suffix}",
		]
		for value in fallback_colours:
			frappe.get_doc(
				{
					"doctype": "Item Attribute Value",
					"attribute_name": "Colour",
					"attribute_value": value,
				}
			).insert(ignore_permissions=True)

		empty_mapping = self._make_mapping("Colour", [])
		empty_yarn = self._make_item(
			f"_Test Empty Colour Yarn {suffix}",
			"Yarn Item Group",
			"Kg",
			[{"attribute": "Colour", "mapping": empty_mapping}],
			is_yarn_item=1,
		)

		options = get_item_attribute_options(empty_yarn)
		self.assertTrue(set(fallback_colours).issubset(options["Colour"]))

		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.dyeing,
				"input_item": empty_yarn,
				"output_item": empty_yarn,
				"from_colour": fallback_colours[0],
				"to_colour": fallback_colours[1],
				"quantity_ratio": 1,
			},
		])
		self.assertEqual(
			(
				ipd.mgk_yarn_process_routes[0].from_colour,
				ipd.mgk_yarn_process_routes[0].to_colour,
			),
			tuple(fallback_colours),
		)

	def test_po_grn_ipd_doubling_and_dyeing_end_to_end(self):
		"""Exercise the same submitted records an operator creates in Desk."""
		from yrp.stock.utils import get_stock_balance
		from yrp.yrp.doctype.item.item import get_or_create_variant

		self._ensure_received_type()
		raw_supplier = self._make_supplier("_Test Yarn Purchase Supplier")
		source_location = self._make_supplier(
			"_Test MGK Source Location",
			is_company_location=1,
		)
		doubling_supplier = self._make_supplier("_Test Doubling Supplier")
		dyeing_supplier = self._make_supplier("_Test Dyeing Supplier")
		source_warehouse = self._make_warehouse(
			source_location,
			"_Test MGK Source Warehouse",
		)
		self._make_warehouse(
			doubling_supplier,
			"_Test Doubling Warehouse",
		)
		self._make_warehouse(
			dyeing_supplier,
			"_Test Dyeing Warehouse",
		)
		source_address = self._make_address("_Test MGK Source Address")
		doubling_address = self._make_address("_Test Doubling Address")
		dyeing_address = self._make_address("_Test Dyeing Address")

		raw_yarn_variant = get_or_create_variant(
			self.yarn_40,
			{"Colour": "Orange"},
		)
		self._make_item_price(self.yarn_40, raw_supplier)

		purchase_order = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": raw_supplier,
			"delivery_warehouse": source_warehouse,
			"items": [{
				"item_variant": raw_yarn_variant,
				"qty": 100,
				"uom": "Kg",
				"stock_uom": "Kg",
				"conversion_factor": 1,
				"rate": 25,
				"table_index": 0,
				"row_index": "0",
			}],
		})
		purchase_order.insert(ignore_permissions=True)
		purchase_order.submit()

		purchase_grn = frappe.get_doc({
			"doctype": "Goods Received Note",
			"against": "Purchase Order",
			"against_id": purchase_order.name,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
			"to_warehouse": source_warehouse,
			"items": [{
				"item_variant": raw_yarn_variant,
				"quantity": 100,
				"uom": "Kg",
				"stock_uom": "Kg",
				"conversion_factor": 1,
				"rate": 25,
				"received_type": "Accepted",
				"ref_doctype": "Purchase Order Item",
				"ref_docname": purchase_order.items[0].name,
			}],
		})
		purchase_grn.insert(ignore_permissions=True)
		purchase_grn.submit()
		self.assertEqual(
			flt(get_stock_balance(raw_yarn_variant, source_warehouse)),
			100,
		)

		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
			{
				"sequence": 20,
				"process_name": self.dyeing,
				"input_item": self.yarn_80,
				"output_item": self.yarn_80,
				"from_colour": "Orange",
				"to_colour": "Blue",
				"quantity_ratio": 1,
			},
		])
		self.assertEqual(ipd.item, self.towel)
		self.assertEqual(
			[row.attribute for row in ipd.item_attributes],
			["Colour", "Size"],
		)
		approve_ipd(ipd.name, modified=ipd.modified)
		ipd.reload()

		self._make_process_cost(
			self.doubling,
			self.yarn_80,
			doubling_supplier,
		)
		doubling_wo = frappe.get_doc({
			"doctype": "Work Order",
			"naming_series": "WO-",
			"wo_date": nowdate(),
			"supplier": doubling_supplier,
			"delivery_location": source_location,
			"supplier_address": doubling_address,
			"delivery_address": source_address,
			"planned_start_date": nowdate(),
			"planned_end_date": add_days(nowdate(), 1),
			"process_name": self.doubling,
			"item": self.towel,
			"production_detail": ipd.name,
			"mgk_items": [{
				"item": self.towel,
				"production_detail": ipd.name,
			}],
		})
		doubling_wo.insert(ignore_permissions=True)
		calculate_deliverables(
			doubling_wo.name,
			[{
				"production_detail": ipd.name,
				"route_name": ipd.mgk_yarn_process_routes[0].name,
				"attribute_values": {"Colour": "Orange"},
				"weight": 100,
			}],
			modified=doubling_wo.modified,
		)
		doubling_wo = frappe.get_doc("Work Order", doubling_wo.name)
		doubling_wo.submit()
		doubling_dc = self._make_delivery_challan(doubling_wo)
		self._make_work_order_grn(doubling_wo, doubling_dc)

		doubled_yarn_variant = doubling_wo.receivables[0].item_variant
		self.assertEqual(
			flt(get_stock_balance(doubled_yarn_variant, source_warehouse)),
			100,
		)

		self._make_process_cost(
			self.dyeing,
			self.yarn_80,
			dyeing_supplier,
		)
		dyeing_wo = frappe.get_doc({
			"doctype": "Work Order",
			"naming_series": "WO-",
			"wo_date": nowdate(),
			"supplier": dyeing_supplier,
			"delivery_location": source_location,
			"supplier_address": dyeing_address,
			"delivery_address": source_address,
			"planned_start_date": nowdate(),
			"planned_end_date": add_days(nowdate(), 1),
			"process_name": self.dyeing,
			"item": self.towel,
			"production_detail": ipd.name,
			"mgk_items": [{
				"item": self.towel,
				"production_detail": ipd.name,
			}],
		})
		dyeing_wo.insert(ignore_permissions=True)
		calculate_deliverables(
			dyeing_wo.name,
			[{
				"production_detail": ipd.name,
				"route_name": ipd.mgk_yarn_process_routes[1].name,
				"attribute_values": {},
				"weight": 100,
			}],
			modified=dyeing_wo.modified,
		)
		dyeing_wo = frappe.get_doc("Work Order", dyeing_wo.name)

		self.assertEqual(
			doubling_wo.receivables[0].item_variant,
			dyeing_wo.deliverables[0].item_variant,
		)
		dyeing_wo.submit()
		dyeing_dc = self._make_delivery_challan(dyeing_wo)
		self._make_work_order_grn(dyeing_wo, dyeing_dc)

		dyed_yarn_variant = dyeing_wo.receivables[0].item_variant
		self.assertEqual(
			_matrix_variant_attributes(dyed_yarn_variant),
			{"Colour": "Blue"},
		)
		self.assertEqual(
			flt(get_stock_balance(dyed_yarn_variant, source_warehouse)),
			100,
		)

	def test_dyeing_then_doubling_outputs_coloured_80s_variant(self):
		ipd = self._make_ipd([
			{
				"sequence": 10,
				"process_name": self.dyeing,
				"input_item": self.yarn_40,
				"output_item": self.yarn_40,
				"from_colour": "Orange",
				"to_colour": "Blue",
				"quantity_ratio": 1,
			},
			{
				"sequence": 20,
				"process_name": self.doubling,
				"input_item": self.yarn_40,
				"output_item": self.yarn_80,
				"quantity_ratio": 1,
			},
		])

		dyeing_route, doubling_route = ipd.mgk_yarn_process_routes
		dyeing_io = build_route_io(
			ipd,
			self.dyeing,
			dyeing_route.name,
			{},
			100,
		)
		self.assertEqual(dyeing_io["input_attrs"], {"Colour": "Orange"})
		self.assertEqual(dyeing_io["output_attrs"], {"Colour": "Blue"})

		wo = frappe.get_doc({
			"doctype": "Work Order",
			"process_name": self.doubling,
			"production_detail": ipd.name,
			"mgk_items": [
				{"item": self.yarn_80, "production_detail": ipd.name}
			],
		})
		wo.name = "_Test Yarn Work Order"
		regenerate_process_matrices(ipd)
		deliverables, receivables = _prepare_yarn_transformation_items(
			wo,
			[
				{
					"production_detail": ipd.name,
					"route_name": doubling_route.name,
					"attribute_values": {"Colour": "Blue"},
					"weight": 100,
				}
			],
		)

		self.assertEqual(len(deliverables), 1)
		self.assertEqual(len(receivables), 1)
		self.assertEqual(deliverables[0]["qty"], 100)
		self.assertEqual(receivables[0]["qty"], 100)
		self.assertEqual(
			frappe.db.get_value(
				"Item Variant",
				deliverables[0]["item_variant"],
				"item",
			),
			self.yarn_40,
		)
		self.assertEqual(
			frappe.db.get_value(
				"Item Variant",
				receivables[0]["item_variant"],
				"item",
			),
			self.yarn_80,
		)
		self.assertEqual(
			_matrix_variant_attributes(receivables[0]["item_variant"]),
			{"Colour": "Blue"},
		)

		dyeing_wo = self._calculate_work_order(
			ipd,
			self.dyeing,
			dyeing_route.name,
			{},
		)
		doubling_wo = self._calculate_work_order(
			ipd,
			self.doubling,
			doubling_route.name,
			{"Colour": "Blue"},
		)
		self.assertEqual(
			dyeing_wo.receivables[0].item_variant,
			doubling_wo.deliverables[0].item_variant,
		)
		self.assertEqual(
			_matrix_variant_attributes(
				doubling_wo.receivables[0].item_variant
			),
			{"Colour": "Blue"},
		)

	def test_broken_process_chain_is_rejected(self):
		with self.assertRaisesRegex(
			frappe.ValidationError,
			"Yarn Process flow breaks",
		):
			self._make_ipd([
				{
					"sequence": 10,
					"process_name": self.dyeing,
					"input_item": self.yarn_40,
					"output_item": self.yarn_40,
					"from_colour": "Orange",
					"to_colour": "Blue",
					"quantity_ratio": 1,
				},
				{
					"sequence": 20,
					"process_name": self.doubling,
					"input_item": self.yarn_60,
					"output_item": self.yarn_80,
					"quantity_ratio": 1,
				},
			])
