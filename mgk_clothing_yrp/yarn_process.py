"""Ordered yarn-to-yarn transformations maintained on Item Production Detail.

MGK uses only two transformation shapes:

* Item conversion (Doubling): Item A -> Item B, carrying every yarn attribute.
* Colour change (Dyeing): the same Item, From Colour -> To Colour, carrying all
  other attributes.

The IPD's main Item is the finished/context Item (for example, a towel with
Colour and Size). The child rows independently describe the Yarn Item chain.
Work Orders derive their deliverables and receivables directly from those rows;
MGK does not create process-specific records, BOMs, or matrix documents.
"""

from __future__ import annotations

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import flt

COLOUR_ATTRIBUTE = "Colour"


def load_attribute_list(doc, method=None):
	"""Expose the finished Item's mapped values to YRP's Desk Vue cards.

	The IPD stores only each attribute and its mapping link. The actual values
	live in Item Item Attribute Mapping, so they must be placed in ``__onload``
	for the existing ``frappe.production.ui.ItemAttributeList`` component.
	This hook is MGK-only; base YRP remains untouched.
	"""
	attribute_list = []
	for attribute in doc.get("item_attributes") or []:
		if not attribute.get("attribute"):
			continue
		attribute_doc = frappe.get_cached_doc(
			"Item Attribute",
			attribute.attribute,
		)
		if attribute_doc.get("numeric_values"):
			continue

		values = []
		if attribute.get("mapping"):
			mapping = frappe.get_cached_doc(
				"Item Item Attribute Mapping",
				attribute.mapping,
			)
			values = [
				{"attribute_value": row.attribute_value}
				for row in mapping.get("values") or []
			]

		attribute_list.append(
			{
				"name": attribute.name,
				"attr_name": attribute.attribute,
				"attr_values_link": attribute.get("mapping"),
				"attr_values": values,
				"doctype": "Item Item Attribute Mapping",
			}
		)
	doc.set_onload("attr_list", attribute_list)


def _route_rows(doc):
	return sorted(
		list(doc.get("mgk_yarn_process_routes") or []),
		key=lambda row: (int(row.get("sequence") or 0), int(row.get("idx") or 0)),
	)


def _quantity_ratio(row):
	value = row.get("quantity_ratio")
	return 1 if value in (None, "") else flt(value)


def _item_schema(item_name, cache=None, require_yarn=True):
	cache = cache if cache is not None else {}
	cache_key = (item_name, bool(require_yarn))
	if cache_key in cache:
		return cache[cache_key]
	if not item_name or not frappe.db.exists("Item", item_name):
		label = _("Yarn Item") if require_yarn else _("Item")
		frappe.throw(_("{0} {1} does not exist.").format(label, item_name or _("(blank)")))

	item = frappe.get_cached_doc("Item", item_name)
	if require_yarn and not item.get("is_yarn_item"):
		frappe.throw(_("Item {0} must be marked as Is Yarn Item.").format(item_name))
	if require_yarn and item.get("dependent_attribute"):
		frappe.throw(
			_(
				"Yarn Item {0} uses dependent attribute {1}. MGK yarn transformations "
				"support normal Item attributes only."
			).format(item_name, item.dependent_attribute)
		)

	from yrp.yrp.doctype.item.item import get_attribute_values

	attributes = [row.attribute for row in item.get("attributes") or []]
	value_map = get_attribute_values(item_name) or {}
	schema = frappe._dict(
		name=item_name,
		uom=item.get("default_unit_of_measure"),
		attributes=attributes,
		value_options={
			attribute: list(value_map.get(attribute) or [])
			for attribute in attributes
		},
		mappings={row.attribute: row.mapping for row in item.get("attributes") or []},
		primary_attribute=item.get("primary_attribute"),
	)
	cache[cache_key] = schema
	return schema


def _process_doc(process_name):
	if not process_name or not frappe.db.exists("Process", process_name):
		frappe.throw(_("Process {0} does not exist.").format(process_name or _("(blank)")))
	process = frappe.get_cached_doc("Process", process_name)
	if not process.get("is_yarn_process"):
		frappe.throw(_("Process {0} must be marked as Is Yarn Process.").format(process_name))
	if process.get("is_group"):
		frappe.throw(_("Group Process {0} cannot be used as a Work Order step.").format(process_name))
	return process


def get_step_groups(doc):
	"""Return ordered process groups; repeated rows at one sequence are Dyeing routes."""
	grouped = OrderedDict()
	for row in _route_rows(doc):
		sequence = int(row.get("sequence") or 0)
		if sequence <= 0:
			frappe.throw(_("Yarn Process row {0}: Sequence must be greater than zero.").format(row.idx))
		group = grouped.setdefault(
			sequence,
			frappe._dict(
				sequence=sequence,
				process_name=row.get("process_name"),
				input_item=row.get("input_item"),
				output_item=row.get("output_item"),
				quantity_ratio=_quantity_ratio(row),
				routes=[],
			),
		)
		core = (
			row.get("process_name"),
			row.get("input_item"),
			row.get("output_item"),
			_quantity_ratio(row),
		)
		group_core = (
			group.process_name,
			group.input_item,
			group.output_item,
			group.quantity_ratio,
		)
		if core != group_core:
			frappe.throw(
				_(
					"Yarn Process sequence {0} must use one Process, Input Item, "
					"Output Item, and Output-per-Input ratio for all its colour routes."
				).format(sequence)
			)
		group.routes.append(row)
	return list(grouped.values())


def validate_yarn_process_flow(doc, method=None):
	"""Validate the two supported shapes and the item-to-item sequence."""
	if not _route_rows(doc):
		return []

	groups = get_step_groups(doc)
	item_cache = {}
	context_item_schema = _item_schema(
		doc.item,
		item_cache,
		require_yarn=False,
	)
	process_sequences = {}

	for group in groups:
		process = _process_doc(group.process_name)
		input_schema = _item_schema(group.input_item, item_cache)
		output_schema = _item_schema(group.output_item, item_cache)

		if group.quantity_ratio <= 0:
			frappe.throw(
				_("Yarn Process sequence {0}: Output per Input must be greater than zero.").format(
					group.sequence
				)
			)
		if not input_schema.uom or not output_schema.uom:
			frappe.throw(
				_(
					"Yarn Process sequence {0}: both Yarn Items need a Default "
					"Unit of Measure."
				).format(group.sequence)
			)
		if input_schema.uom != output_schema.uom:
			frappe.throw(
				_(
					"Yarn Process sequence {0}: Input UOM ({1}) and Output UOM ({2}) "
					"must match."
				).format(group.sequence, input_schema.uom, output_schema.uom)
			)
		if input_schema.attributes != output_schema.attributes:
			frappe.throw(
				_(
					"Yarn Process sequence {0}: Input and Output Yarn Items must have "
					"the same ordered attributes so Colour and other values can carry "
					"through the process. Input: {1}; Output: {2}."
				).format(
					group.sequence,
					", ".join(input_schema.attributes) or _("none"),
					", ".join(output_schema.attributes) or _("none"),
				)
			)
		# The picker carries only values that both the input and output Items
		# allow. Fail at IPD save time if no safe carried value exists.
		_shared_attribute_options(input_schema, output_schema)

		previous_sequence = process_sequences.get(group.process_name)
		if previous_sequence is not None and previous_sequence != group.sequence:
			frappe.throw(
				_("Process {0} can appear at only one sequence in a Yarn IPD.").format(
					group.process_name
				)
			)
		process_sequences[group.process_name] = group.sequence

		is_conversion = group.input_item != group.output_item
		if is_conversion:
			if len(group.routes) != 1:
				frappe.throw(
					_(
						"Yarn Process sequence {0}: an Item-conversion step such as "
						"Doubling needs exactly one row."
					).format(group.sequence)
				)
			route = group.routes[0]
			if route.get("from_colour") or route.get("to_colour"):
				frappe.throw(
					_(
						"Yarn Process sequence {0}: leave From/To Colour blank for "
						"Item conversion. All attribute values are carried automatically."
					).format(group.sequence)
				)
			if not process.get("is_item_conversion"):
				frappe.throw(
					_(
						"Process {0} converts one Yarn Item into another. Enable "
						"Item Conversion on the Process master."
					).format(group.process_name)
				)
		else:
			if process.get("is_item_conversion"):
				frappe.throw(
					_(
						"Process {0} keeps the same Yarn Item and changes Colour. "
						"Disable Item Conversion on the Process master."
					).format(group.process_name)
				)
			changed_attributes = {
				row.attribute for row in process.get("value_change_attributes") or []
			}
			if COLOUR_ATTRIBUTE not in changed_attributes:
				frappe.throw(
					_(
						"Process {0} is a Dyeing step. Add Colour under its "
						"Value Change Attributes."
					).format(group.process_name)
				)
			if COLOUR_ATTRIBUTE not in input_schema.attributes:
				frappe.throw(
					_("Yarn Item {0} needs a Colour attribute for Dyeing.").format(
						group.input_item
					)
				)
			seen_routes = set()
			for route in group.routes:
				if not route.get("from_colour") or not route.get("to_colour"):
					frappe.throw(
						_(
							"Yarn Process sequence {0}: Dyeing rows need both From "
							"Colour and To Colour."
						).format(group.sequence)
					)
				if route.from_colour == route.to_colour:
					frappe.throw(
						_(
							"Yarn Process sequence {0}: From Colour and To Colour "
							"must be different."
						).format(group.sequence)
					)
				route_key = (route.from_colour, route.to_colour)
				if route_key in seen_routes:
					frappe.throw(
						_(
							"Yarn Process sequence {0}: duplicate Dyeing route {1} → {2}."
						).format(group.sequence, *route_key)
					)
				seen_routes.add(route_key)
				for value in route_key:
					if value not in input_schema.value_options.get(
						COLOUR_ATTRIBUTE, []
					):
						frappe.throw(
							_(
								"Colour {0} is not allowed on Yarn Item {1}. Add it "
								"to the Item's Colour mapping first."
							).format(value, group.input_item)
						)

	for current, following in zip(groups, groups[1:], strict=False):
		if current.output_item != following.input_item:
			frappe.throw(
				_(
					"Yarn Process flow breaks between sequence {0} and {1}: output "
					"Item {2} must be the next Input Item, but the next row uses {3}."
				).format(
					current.sequence,
					following.sequence,
					current.output_item,
					following.input_item,
				)
			)

	# Starting Yarn is derived from the ordered flow; it is not a second source
	# of truth for the operator to keep in sync.
	doc.yarn_item = groups[0].input_item
	_sync_ipd_item_attributes(doc, context_item_schema)
	return groups


def _sync_ipd_item_attributes(doc, item_schema):
	doc.set("item_attributes", [])
	for attribute in item_schema.attributes:
		doc.append(
			"item_attributes",
			{
				"attribute": attribute,
				"mapping": item_schema.mappings.get(attribute),
			},
		)
	doc.primary_item_attribute = item_schema.primary_attribute or None
	doc.dependent_attribute = None
	doc.dependent_attribute_mapping = None


def _shared_attribute_options(input_schema, output_schema):
	options = OrderedDict()
	for attribute in input_schema.attributes:
		input_values = input_schema.value_options.get(attribute, [])
		output_values = set(output_schema.value_options.get(attribute, []))
		common = [value for value in input_values if value in output_values]
		if not common:
			frappe.throw(
				_(
					"Input Item {0} and Output Item {1} have no common values for "
					"attribute {2}."
				).format(input_schema.name, output_schema.name, attribute)
			)
		options[attribute] = common
	return options


def has_yarn_process_route(ipd, process_name):
	if not ipd or not process_name:
		return False
	doc = frappe.get_cached_doc("Item Production Detail", ipd)
	return any(group.process_name == process_name for group in get_step_groups(doc))


def get_process_route_context(ipd, process_name):
	"""Desk Work Order popup rows for one IPD/process."""
	doc = frappe.get_cached_doc("Item Production Detail", ipd)
	group = next(
		(group for group in get_step_groups(doc) if group.process_name == process_name),
		None,
	)
	if not group:
		return []

	item_cache = {}
	input_schema = _item_schema(group.input_item, item_cache)
	output_schema = _item_schema(group.output_item, item_cache)
	options = _shared_attribute_options(input_schema, output_schema)
	is_conversion = group.input_item != group.output_item
	attribute_names = list(options) if is_conversion else [
		attribute for attribute in options if attribute != COLOUR_ATTRIBUTE
	]
	attributes = [
		{
			"attribute": attribute,
			"label": attribute,
			"options": options[attribute],
		}
		for attribute in attribute_names
	]

	rows = []
	for route in group.routes:
		input_label = group.input_item
		output_label = group.output_item
		if not is_conversion:
			input_label += f" · {route.from_colour}"
			output_label += f" · {route.to_colour}"
		rows.append(
			{
				"route_name": route.name,
				"sequence": group.sequence,
				"process_name": group.process_name,
				"transformation_type": "Item Conversion" if is_conversion else "Colour Change",
				"input_item": group.input_item,
				"output_item": group.output_item,
				"input_label": input_label,
				"output_label": output_label,
				"from_colour": route.get("from_colour"),
				"to_colour": route.get("to_colour"),
				"input_uom": input_schema.uom,
				"output_uom": output_schema.uom,
				"quantity_ratio": group.quantity_ratio,
				"attributes": attributes,
			}
		)
	return rows


def build_route_io(ipd_doc, process_name, route_name, attribute_values, input_qty):
	"""Resolve one user-selected IPD route into item/attribute/quantity I/O."""
	attribute_values = frappe.parse_json(attribute_values) if isinstance(attribute_values, str) else (
		attribute_values or {}
	)
	group = next(
		(group for group in get_step_groups(ipd_doc) if group.process_name == process_name),
		None,
	)
	if not group:
		frappe.throw(
			_("Process {0} is not configured on Item Production Detail {1}.").format(
				process_name, ipd_doc.name
			)
		)
	route = next((route for route in group.routes if route.name == route_name), None)
	if not route:
		frappe.throw(
			_("Yarn Process route {0} is not part of Item Production Detail {1}.").format(
				route_name, ipd_doc.name
			)
		)

	item_cache = {}
	input_schema = _item_schema(group.input_item, item_cache)
	output_schema = _item_schema(group.output_item, item_cache)
	options = _shared_attribute_options(input_schema, output_schema)
	is_conversion = group.input_item != group.output_item
	required = list(options) if is_conversion else [
		attribute for attribute in options if attribute != COLOUR_ATTRIBUTE
	]
	missing = [attribute for attribute in required if not attribute_values.get(attribute)]
	if missing:
		frappe.throw(
			_("Select {0} for route {1} → {2}.").format(
				", ".join(missing), group.input_item, group.output_item
			)
		)
	unknown = [attribute for attribute in attribute_values if attribute not in required]
	if unknown:
		frappe.throw(_("Unexpected Yarn attribute(s): {0}.").format(", ".join(unknown)))
	for attribute in required:
		if attribute_values[attribute] not in options[attribute]:
			frappe.throw(
				_("Value {0} is not allowed for attribute {1} on this route.").format(
					attribute_values[attribute], attribute
				)
			)

	if is_conversion:
		input_attrs = {attribute: attribute_values[attribute] for attribute in required}
		output_attrs = dict(input_attrs)
	else:
		input_attrs = {attribute: attribute_values[attribute] for attribute in required}
		output_attrs = dict(input_attrs)
		input_attrs[COLOUR_ATTRIBUTE] = route.from_colour
		output_attrs[COLOUR_ATTRIBUTE] = route.to_colour

	qty = flt(input_qty)
	if qty <= 0:
		frappe.throw(_("Input quantity must be greater than zero."))
	return {
		"input_item": group.input_item,
		"output_item": group.output_item,
		"input_attrs": input_attrs,
		"output_attrs": output_attrs,
		"input_qty": qty,
		"output_qty": qty * group.quantity_ratio,
		"input_uom": input_schema.uom,
		"output_uom": output_schema.uom,
		"quantity_ratio": group.quantity_ratio,
	}
