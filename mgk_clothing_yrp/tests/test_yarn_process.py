import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, nowdate, nowtime

from mgk_clothing_yrp.mgk_clothing_yrp.api.work_order import (
	_matrix_variant_attributes,
	_prepare_yarn_transformation_items,
	calculate_deliverables,
)
from mgk_clothing_yrp.yarn_process import (
	build_route_io,
	get_process_route_context,
	load_attribute_list,
)


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
			mgk_items=[frappe._dict(production_detail=ipd.name)],
		)
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
			"mgk_items": [
				{"item": self.yarn_80, "production_detail": ipd.name}
			],
		})
		wo.name = "_Test Yarn Work Order"
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
