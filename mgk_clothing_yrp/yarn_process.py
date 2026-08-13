"""Ordered yarn-to-yarn transformations maintained on Item Production Detail.

The Process master is authoritative for the transformation shape:

* ``is_item_conversion``: Item A -> Item B, carrying every yarn attribute.
* ``Colour`` in Value Change Attributes: the same Item, From Colour -> To
  Colour, carrying every other attribute.
* No Value Change Attributes: a pass-through process such as Washing, carrying
  the Item and every attribute unchanged.

The IPD's main Item is the finished/context Item (for example, a towel with
Colour and Size). The child rows independently describe the Yarn Item chain.
Those rows are the operator-facing source of truth. Approval, or an explicit
System Manager test action, compiles them into base-YRP ``IPD Process Matrix``
documents; Work Orders then calculate through the shared matrix engine.
"""

from __future__ import annotations

from collections import OrderedDict
from itertools import product

import frappe
from frappe import _
from frappe.utils import flt

COLOUR_ATTRIBUTE = "Colour"
ITEM_CONVERSION = "Item Conversion"
COLOUR_CHANGE = "Colour Change"
PASS_THROUGH = "Pass Through"


def _process_change_attributes(process):
	return list(dict.fromkeys(
		row.attribute
		for row in process.get("value_change_attributes") or []
		if row.attribute
	))


def _process_shape(process):
	"""Resolve one yarn Process without inferring its meaning from Item equality."""
	changed_attributes = _process_change_attributes(process)
	if process.get("is_item_conversion"):
		if changed_attributes:
			frappe.throw(
				_(
					"Yarn Process {0} is an Item Conversion and also defines Value "
					"Change Attributes: {1}. The MGK yarn route supports only one "
					"transformation shape per Process."
				).format(process.name, ", ".join(changed_attributes))
			)
		return ITEM_CONVERSION

	if not changed_attributes:
		return PASS_THROUGH
	if changed_attributes == [COLOUR_ATTRIBUTE]:
		return COLOUR_CHANGE

	frappe.throw(
		_(
			"Yarn Process {0} has unsupported Value Change Attributes: {1}. "
			"The MGK yarn route currently supports Colour as its one changed "
			"attribute; remove the unsupported attributes or use a Process Matrix."
		).format(process.name, ", ".join(changed_attributes))
	)


def _append_matrix_combo(matrix, group_index, side, item, quantity, uom, attrs):
	"""Append one matrix combination and its normalized attribute rows."""
	matrix.append(
		"combinations",
		{
			"group_index": group_index,
			"side": side,
			"combo_index": 1,
			"item": item,
			"quantity": quantity,
			"uom": uom,
		},
	)
	for attribute, value in attrs.items():
		matrix.append(
			"combination_attributes",
			{
				"group_index": group_index,
				"side": side,
				"combo_index": 1,
				"attribute": attribute,
				"attribute_value": value,
			},
		)


def _attribute_combinations(attributes, options):
	"""Yield ordered attribute dictionaries for a matrix cross-product."""
	if not attributes:
		yield {}
		return
	for values in product(*(options[attribute] for attribute in attributes)):
		yield dict(zip(attributes, values, strict=True))


def _deduplicate_states(states, attributes):
	seen = set()
	unique = []
	for state in states:
		key = tuple(state.get(attribute) for attribute in attributes)
		if key in seen:
			continue
		seen.add(key)
		unique.append(dict(state))
	return unique


def _compile_yarn_process_chain(doc, groups=None):
	"""Propagate exact attribute states through the ordered yarn Process train."""
	groups = groups if groups is not None else get_step_groups(doc)
	item_cache = {}
	previous_outputs = None
	compiled = []

	for group in groups:
		process = _process_doc(group.process_name)
		shape = _process_shape(process)
		input_schema = _item_schema(group.input_item, item_cache)
		output_schema = _item_schema(group.output_item, item_cache)
		options = _shared_attribute_options(input_schema, output_schema)
		attributes = list(options)
		upstream_constrained = previous_outputs is not None

		if upstream_constrained:
			input_states = []
			for state in previous_outputs:
				unsupported = [
					attribute
					for attribute in attributes
					if state.get(attribute) not in options[attribute]
				]
				if unsupported:
					frappe.throw(
						_(
							"Yarn Process {0} cannot receive the previous Process output. "
							"The Output Item does not allow the carried value for: {1}."
						).format(group.process_name, ", ".join(unsupported))
					)
				input_states.append(dict(state))
		else:
			input_states = list(_attribute_combinations(attributes, options))

		transitions = []
		if shape == COLOUR_CHANGE:
			for route in group.routes:
				matching = [
					state
					for state in input_states
					if state.get(COLOUR_ATTRIBUTE) == route.from_colour
				]
				if upstream_constrained and not matching:
					frappe.throw(
						_(
							"Yarn Process {0} expects input Colour {1}, but the previous "
							"Process does not produce that Colour."
						).format(group.process_name, route.from_colour)
					)
				for input_attrs in matching:
					output_attrs = dict(input_attrs)
					output_attrs[COLOUR_ATTRIBUTE] = route.to_colour
					transitions.append(
						frappe._dict(
							route=route,
							input_attrs=dict(input_attrs),
							output_attrs=output_attrs,
						)
					)
		else:
			route = group.routes[0]
			for input_attrs in input_states:
				transitions.append(
					frappe._dict(
						route=route,
						input_attrs=dict(input_attrs),
						output_attrs=dict(input_attrs),
					)
				)

		previous_outputs = _deduplicate_states(
			[transition.output_attrs for transition in transitions],
			output_schema.attributes,
		)
		compiled.append(
			frappe._dict(
				group=group,
				shape=shape,
				input_schema=input_schema,
				output_schema=output_schema,
				options=options,
				upstream_constrained=upstream_constrained,
				transitions=transitions,
				output_states=previous_outputs,
			)
		)

	return compiled


def regenerate_process_matrices(doc):
	"""Compile MGK yarn routes into base-YRP Process Matrix documents.

	The yarn-flow rows are the only editable source for these process matrices.
	Regeneration replaces matrices for exactly the processes present in that
	flow, while leaving matrices for unrelated IPD processes untouched. The
	request transaction rolls every replacement back if any generated matrix
	fails base-YRP validation.
	"""
	from mgk_clothing_yrp.ipd_lock import assert_ipd_editable

	assert_ipd_editable(doc)
	groups = validate_yarn_process_flow(doc)
	if not groups:
		frappe.throw(_("Add at least one Yarn Process before generating the matrix."))

	finished_attributes = {
		row.attribute for row in doc.get("item_attributes") or [] if row.attribute
	}
	process_names = sorted({group.process_name for group in groups})
	existing = frappe.get_all(
		"IPD Process Matrix",
		filters={"ipd": doc.name, "process_name": ["in", process_names]},
		pluck="name",
	)
	for matrix_name in existing:
		frappe.delete_doc(
			"IPD Process Matrix",
			matrix_name,
			ignore_permissions=True,
			force=True,
		)

	created = []
	for step in _compile_yarn_process_chain(doc, groups):
		group = step.group
		input_schema = step.input_schema
		output_schema = step.output_schema
		unsupported_outputs = [
			attribute
			for attribute in output_schema.attributes
			if attribute not in finished_attributes
		]
		if unsupported_outputs:
			frappe.throw(
				_(
					"Yarn Process {0} cannot be compiled: output Item {1} uses "
					"attribute(s) {2}, but those attributes are not present on the "
					"finished Item Production Detail."
				).format(
					group.process_name,
					group.output_item,
					", ".join(unsupported_outputs),
				)
			)

		matrix = frappe.new_doc("IPD Process Matrix")
		matrix.ipd = doc.name
		matrix.process_name = group.process_name
		matrix.input_item = group.input_item
		matrix.output_item = group.output_item
		for attribute in input_schema.attributes:
			matrix.append("input_attributes", {"attribute": attribute})
		for attribute in output_schema.attributes:
			matrix.append("output_attributes", {"attribute": attribute})

		for group_index, transition in enumerate(step.transitions, start=1):
			_append_matrix_combo(
				matrix,
				group_index,
				"Input",
				group.input_item,
				1,
				input_schema.uom,
				transition.input_attrs,
			)
			_append_matrix_combo(
				matrix,
				group_index,
				"Output",
				group.output_item,
				group.quantity_ratio,
				output_schema.uom,
				transition.output_attrs,
			)

		matrix.insert(ignore_permissions=True)
		created.append(matrix.name)

	return created


def load_attribute_list(doc, method=None):
	"""Expose this IPD's finished-Item values to the attribute cards.

	Each IPD row points to its own ``Item Item Attribute Mapping`` document. The
	Item's mapping is only the starting template and must never be changed by an
	IPD edit. Values are placed in ``__onload`` for both the Desk component and
	the MGK Registered Experience. This hook is MGK-only; base YRP is untouched.
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


def _mapping_values(mapping_name):
	if not mapping_name or not frappe.db.exists(
		"Item Item Attribute Mapping", mapping_name
	):
		return []
	mapping = frappe.get_doc("Item Item Attribute Mapping", mapping_name)
	return [row.attribute_value for row in mapping.get("values") or []]


def _new_ipd_mapping(attribute_name, source_mapping=None):
	"""Clone an Item mapping as an independent mapping owned by one IPD."""
	mapping = frappe.get_doc(
		{
			"doctype": "Item Item Attribute Mapping",
			"attribute_name": attribute_name,
			"values": [
				{"attribute_value": value}
				for value in _mapping_values(source_mapping)
			],
		}
	)
	# The user's authority to maintain these values comes from write access to
	# the owning IPD. The mapping is an implementation child of that workflow,
	# even though the reusable base DocType has its own role table.
	mapping.insert(ignore_permissions=True)
	return mapping.name


def _mapping_is_shared(mapping_name, ipd_name=None):
	"""Return whether a mapping belongs to an Item/master or another IPD."""
	if not mapping_name or not frappe.db.exists(
		"Item Item Attribute Mapping", mapping_name
	):
		return True

	# Any row in the master-attribute child table means this mapping still
	# belongs to a master document. Do not assume only today's two parenttypes.
	if frappe.db.exists(
		"Item Item Attribute",
		{"mapping": mapping_name},
	):
		return True

	other_ipds = frappe.get_all(
		"IPD Item Attribute",
		filters={
			"mapping": mapping_name,
			"parenttype": "Item Production Detail",
		},
		pluck="parent",
	)
	return any(parent != ipd_name for parent in other_ipds)


def _route_rows(doc):
	return sorted(
		list(doc.get("mgk_yarn_process_routes") or []),
		key=lambda row: (int(row.get("sequence") or 0), int(row.get("idx") or 0)),
	)


def _quantity_ratio(row):
	value = row.get("quantity_ratio")
	return 1 if value in (None, "") else flt(value)


def get_item_attribute_options(item_name, attributes=None):
	"""Return the effective selectable values for each Item attribute.

	A non-empty Item mapping is restrictive. An empty mapping means the Item has
	not narrowed that attribute yet, so the operator may choose from every value
	defined for the corresponding Item Attribute.
	"""
	item = frappe.get_cached_doc("Item", item_name)
	attribute_names = attributes or [
		row.attribute for row in item.get("attributes") or []
	]

	from yrp.yrp.doctype.item.item import get_attribute_values

	mapped_options = get_attribute_values(item_name, attribute_names) or {}
	effective_options = {}
	for attribute in attribute_names:
		mapped_values = list(mapped_options.get(attribute) or [])
		effective_options[attribute] = mapped_values or frappe.get_all(
			"Item Attribute Value",
			filters={"attribute_name": attribute},
			pluck="attribute_value",
			order_by="attribute_value asc",
		)
	return effective_options


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

	attributes = [row.attribute for row in item.get("attributes") or []]
	schema = frappe._dict(
		name=item_name,
		uom=item.get("default_unit_of_measure"),
		attributes=attributes,
		value_options=get_item_attribute_options(item_name, attributes),
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
	"""Validate Process-driven shapes and the item-to-item sequence."""
	if not _route_rows(doc):
		# An IPD may be drafted before its route is complete. Its finished-Item
		# values must still be isolated from the Item master from the first save.
		ensure_ipd_attribute_mappings(doc)
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
		shape = _process_shape(process)
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

		items_differ = group.input_item != group.output_item
		if shape == ITEM_CONVERSION:
			if not items_differ:
				frappe.throw(
					_(
						"Process {0} is an Item Conversion. Select a different "
						"Output Yarn Item."
					).format(group.process_name)
				)
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
		else:
			if items_differ:
				frappe.throw(
					_(
						"Process {0} is not an Item Conversion. Its Output Yarn "
						"Item must stay the same as its Input Yarn Item."
					).format(group.process_name)
				)

			if shape == PASS_THROUGH:
				if len(group.routes) != 1:
					frappe.throw(
						_(
							"Pass-through Process {0} needs exactly one yarn route."
						).format(group.process_name)
					)
				route = group.routes[0]
				if route.get("from_colour") or route.get("to_colour"):
					frappe.throw(
						_(
							"Process {0} has no Value Change Attributes. Leave the "
							"transition values blank so every attribute carries unchanged."
						).format(group.process_name)
					)
				continue

			if COLOUR_ATTRIBUTE not in _process_change_attributes(process):
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
							_("Colour {0} is not available for Yarn Item {1}.").format(
								value, group.input_item
							)
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

	# Validate the attribute-state train as part of every IPD save, not only
	# during approval/matrix regeneration.
	_compile_yarn_process_chain(doc, groups)

	# Starting Yarn is derived from the ordered flow; it is not a second source
	# of truth for the operator to keep in sync.
	doc.yarn_item = groups[0].input_item
	_sync_ipd_item_attributes(doc, context_item_schema)
	return groups


def _sync_ipd_item_attributes(doc, item_schema):
	"""Keep the Item's attribute names but give this IPD private value maps."""
	previous_item = None
	if not doc.is_new():
		previous_item = frappe.db.get_value(
			"Item Production Detail", doc.name, "item"
		)
	preserve_existing = not previous_item or previous_item == doc.item
	existing_mappings = {
		row.attribute: row.get("mapping")
		for row in doc.get("item_attributes") or []
		if row.get("attribute")
	}
	changed = False
	resolved_mappings = {}
	for attribute in item_schema.attributes:
		current_mapping = (
			existing_mappings.get(attribute) if preserve_existing else None
		)
		if _mapping_is_shared(current_mapping, doc.name):
			current_mapping = _new_ipd_mapping(
				attribute,
				item_schema.mappings.get(attribute),
			)
			changed = True
		resolved_mappings[attribute] = current_mapping

	if set(existing_mappings) != set(item_schema.attributes):
		changed = True
	elif any(
		existing_mappings.get(attribute) != resolved_mappings.get(attribute)
		for attribute in item_schema.attributes
	):
		changed = True

	doc.set("item_attributes", [])
	for attribute in item_schema.attributes:
		doc.append(
			"item_attributes",
			{
				"attribute": attribute,
				"mapping": resolved_mappings.get(attribute),
			},
		)
	doc.primary_item_attribute = item_schema.primary_attribute or None
	doc.dependent_attribute = None
	doc.dependent_attribute_mapping = None
	return changed


def ensure_ipd_attribute_mappings(doc):
	"""Ensure every finished-Item attribute uses an IPD-private mapping."""
	if not doc.item:
		return False
	return _sync_ipd_item_attributes(
		doc,
		_item_schema(doc.item, require_yarn=False),
	)


def delete_ipd_attribute_mappings(doc, method=None):
	"""Remove private mapping documents after their owning IPD is deleted."""
	for row in doc.get("item_attributes") or []:
		mapping_name = row.get("mapping")
		if _mapping_is_shared(mapping_name, doc.name):
			continue
		frappe.delete_doc(
			"Item Item Attribute Mapping",
			mapping_name,
			ignore_permissions=True,
		)


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

	step = next(
		(
			step
			for step in _compile_yarn_process_chain(doc)
			if step.group.process_name == process_name
		),
		None,
	)
	if not step:
		return []
	input_schema = step.input_schema
	output_schema = step.output_schema
	shape = step.shape
	attribute_names = list(step.options) if shape != COLOUR_CHANGE else [
		attribute for attribute in step.options if attribute != COLOUR_ATTRIBUTE
	]

	rows = []
	for route in group.routes:
		route_transitions = [
			transition
			for transition in step.transitions
			if transition.route.name == route.name
		]
		allowed_combinations = _deduplicate_states(
			[
				{
					attribute: transition.input_attrs[attribute]
					for attribute in attribute_names
				}
				for transition in route_transitions
			],
			attribute_names,
		)
		attributes = [
			{
				"attribute": attribute,
				"label": attribute,
				"options": list(dict.fromkeys(
					combination[attribute]
					for combination in allowed_combinations
				)),
			}
			for attribute in attribute_names
		]
		input_label = group.input_item
		output_label = group.output_item
		if shape == COLOUR_CHANGE:
			input_label += f" · {route.from_colour}"
			output_label += f" · {route.to_colour}"
		rows.append(
			{
				"route_name": route.name,
				"sequence": group.sequence,
				"process_name": group.process_name,
				"transformation_type": shape,
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
				"allowed_attribute_combinations": allowed_combinations,
				"chain_constrained": step.upstream_constrained,
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

	step = next(
		(
			step
			for step in _compile_yarn_process_chain(ipd_doc)
			if step.group.process_name == process_name
		),
		None,
	)
	if not step:
		frappe.throw(
			_("Process {0} has no compiled Yarn route.").format(process_name)
		)
	input_schema = step.input_schema
	output_schema = step.output_schema
	shape = step.shape
	required = list(step.options) if shape != COLOUR_CHANGE else [
		attribute for attribute in step.options if attribute != COLOUR_ATTRIBUTE
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
	transition = next(
		(
			transition
			for transition in step.transitions
			if transition.route.name == route.name
			and all(
				transition.input_attrs.get(attribute) == attribute_values[attribute]
				for attribute in required
			)
		),
		None,
	)
	if not transition:
		frappe.throw(
			_(
				"The selected Yarn attribute combination is not produced by the "
				"previous Process for route {0}."
			).format(route.name)
		)
	input_attrs = dict(transition.input_attrs)
	output_attrs = dict(transition.output_attrs)

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
