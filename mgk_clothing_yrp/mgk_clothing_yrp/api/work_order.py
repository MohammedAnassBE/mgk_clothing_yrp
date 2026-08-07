"""mgk_clothing_yrp design-approval API for Work Order.

Role-gated approve/reject that stamps base-yrp's `approved_by`/`rejection_reason`
and appends to the `mgk_approval_log` child table. The role for a WO's
process is configured in MGK Settings.process_approval_roles (process_name -> approver_role).

The pure logic (_apply_approve / _apply_reject / _approval_state) is split out
from the get_doc/save wrappers so it is unit-testable on an in-memory doc.
"""

import frappe
from frappe import _
from frappe.utils import cstr, flt, now_datetime

from mgk_clothing_yrp.yarn_process import (
	build_route_io,
	get_process_route_context,
	has_yarn_process_route,
)


def _guard_not_modified(doc, modified):
	"""Reject a stale write, mirroring the standard REST PUT's check_if_latest().

	These whitelisted methods load a FRESH doc (`frappe.get_doc`) then `.save()`,
	which bypasses Frappe's built-in stale-write guard — a freshly-loaded
	`modified` always equals the DB value, so check_if_latest() never fires. The
	`/web` client passes the `modified` it originally loaded; if the document has
	changed since, raise the same error the REST path would (TimestampMismatchError,
	HTTP 417) so the SPA shows its "Refresh" conflict banner instead of clobbering.
	"""
	if modified and cstr(doc.modified) != cstr(modified):
		frappe.throw(
			_("{0} was modified after you opened it. Please refresh and try again.").format(doc.name),
			frappe.TimestampMismatchError,
		)


def get_approver_role(process):
	"""Approver Role configured for this Process in MGK Settings, or None."""
	if not process:
		return None
	settings = frappe.get_single("MGK Settings")
	for row in settings.get("process_approval_roles") or []:
		if row.process_name == process:
			return row.approver_role
	return None


def _require_role(wo):
	role = get_approver_role(wo.process_name)
	if not role:
		frappe.throw(_("Process '{0}' is not configured for design approval in MGK Settings.").format(wo.process_name or ""))
	if role not in frappe.get_roles(frappe.session.user):
		frappe.throw(_("You need the '{0}' role to approve or reject this Work Order.").format(role))


def _append_log(wo, action, reason=None):
	wo.append("mgk_approval_log", {
		"action": action,
		"action_by": frappe.session.user,
		"action_at": now_datetime(),
		"reason": reason,
	})


def _apply_approve(wo):
	wo.approved_by = frappe.session.user
	wo.rejection_reason = None
	_append_log(wo, "Approved")


def _apply_reject(wo, reason):
	wo.rejection_reason = reason
	wo.approved_by = None
	_append_log(wo, "Rejected", reason)


def _approval_state(wo):
	role = get_approver_role(wo.process_name)
	return {
		"needs_approval": bool(role),
		"approver_role": role,
		"can_approve": bool(role) and role in frappe.get_roles(frappe.session.user),
		"approved_by": wo.approved_by,
		"rejection_reason": wo.rejection_reason,
		"docstatus": wo.docstatus,
	}


@frappe.whitelist()
def approve(work_order, modified=None):
	wo = frappe.get_doc("Work Order", work_order)
	wo.check_permission("write")
	_guard_not_modified(wo, modified)
	if wo.docstatus != 0:
		frappe.throw(_("Only a draft Work Order can be approved."))
	_require_role(wo)
	_apply_approve(wo)
	wo.save()
	return {"approved_by": wo.approved_by}


@frappe.whitelist()
def reject(work_order, reason, modified=None):
	if not (reason and reason.strip()):
		frappe.throw(_("A reason is required to reject."))
	wo = frappe.get_doc("Work Order", work_order)
	wo.check_permission("write")
	_guard_not_modified(wo, modified)
	if wo.docstatus != 0:
		frappe.throw(_("Only a draft Work Order can be rejected."))
	_require_role(wo)
	_apply_reject(wo, reason)
	wo.save()
	return {"rejection_reason": wo.rejection_reason}


@frappe.whitelist()
def get_approval_state(work_order):
	"""Everything the client needs to render the gate (role logic stays server-side)."""
	wo = frappe.get_doc("Work Order", work_order)
	wo.check_permission("read")
	return _approval_state(wo)


# ======================================================================
# Calculate Deliverables (MGK)
#
# On a saved Work Order, "Calculate Deliverables" turns each `mgk_items`
# row into a deliverable + receivable pair. A Yarn IPD with an MGK route
# uses explicit transformation mode:
#   - Doubling: route Input Item variant -> route Output Item variant.
#   - Dyeing: route From Colour variant -> route To Colour variant.
# All unchanged attributes carry through and the configured quantity ratio
# scales the output.
#
# Older Yarn IPDs without route rows retain the direct-yarn fallback. Each row
# resolves the IPD's `yarn_item` to an Item Variant from the user-picked
# attribute values, and produces:
#         deliverable.qty = weight                       (received_type = Accepted)
#         receivable.qty  = weight * (1 - wastage% + excess%)
# where wastage/excess come from the Process defaults.
# Non-yarn WOs continue to use the existing IPD-Process-Matrix engine.
# ======================================================================


def _int_or_zero(value):
	"""Coerce a (possibly str/None) index field to int, defaulting to 0."""
	try:
		return int(value)
	except (TypeError, ValueError):
		return 0


def _get_wo_process(wo):
	"""Return the WO's Process doc, throwing if process_name is unset/missing."""
	if not wo.process_name:
		frappe.throw(_("Work Order {0} has no Process Name.").format(wo.name))
	return frappe.get_cached_doc("Process", wo.process_name)


def _yarn_item_for_detail(production_detail):
	"""Resolve the `yarn_item` configured on an Item Production Detail."""
	if not production_detail:
		return None
	return frappe.db.get_value("Item Production Detail", production_detail, "yarn_item")


def _resolve_yarn_variant(yarn_item, attrs):
	"""Resolve (find-or-create, idempotently) the Item Variant for a yarn row.

	`item_variant` on Work Order Deliverables is a Link to the Item Variant
	doctype (reqd) — a plain Item won't satisfy it, the named Item Variant must
	exist.

	- WITH attributes: defer to base-yrp `get_or_create_variant`, whose tuple
	  hash (enable_tuple_attribute=1) makes find-or-create idempotent — re-runs
	  with the same attribute values match the same Item Variant.
	- WITHOUT attributes: `get_or_create_variant(item, {})` is NOT idempotent
	  under tuple mode — `create_variant(item, {})` builds an empty (falsy)
	  tuple so `item_tuple_attribute` is never set, and the lookup only matches
	  a self-named Item Variant. So it would insert a fresh Item Variant on
	  EVERY run (unbounded duplicates). A no-attribute yarn item is only valid
	  here if it already has its canonical self-named Item Variant; resolve to
	  that (idempotent), otherwise throw a clear precondition error rather than
	  minting garbage variants.
	"""
	from yrp.yrp.doctype.item.item import get_or_create_variant

	if attrs:
		return get_or_create_variant(yarn_item, attrs)

	# No attributes: only the canonical self-named Item Variant is acceptable.
	if frappe.db.exists("Item Variant", yarn_item):
		return yarn_item
	frappe.throw(
		_(
			"Yarn Item {0} has no attributes and no canonical Item Variant; "
			"Calculate Deliverables (yarn) needs an attribute-bearing yarn item "
			"(or an item with its self-named Item Variant already set up)."
		).format(yarn_item)
	)


def _assert_yarn_item_supported(item):
	"""Guard the yarn calculation's supported Item shape.

	Dependent-attribute Items (e.g. a `Stage` attribute) need per-stage variant
	resolution (`_build_dependent_variant_attrs`) that the flat attribute picker
	here can't supply — a single value per attribute is meaningless when the
	applicable attributes change per stage. Reject them up front with a clear
	message instead of silently rendering a picker the server can't honour.
	"""
	dependent = frappe.get_cached_value("Item", item, "dependent_attribute")
	if dependent:
		frappe.throw(
			_(
				"Yarn Item {0} has a dependent attribute ({1}); dependent-attribute "
				"yarn items aren't supported by Calculate Deliverables yet."
			).format(item, dependent)
		)


def _yarn_item_attributes(item):
	"""The attribute names Calculate Deliverables drives for a (yarn) Item.

	This is the SINGLE source of truth shared by the picker
	(`_item_attribute_options` / `get_yarn_deliverable_rows`) and the validator
	(`_calculate_yarn_deliverables`), so the server never requires an attribute
	the UI can't present. Excludes the dependent attribute, which is rejected
	up front by `_assert_yarn_item_supported`.
	"""
	from yrp.yrp.doctype.item.item import get_attributes

	dependent = frappe.get_cached_value("Item", item, "dependent_attribute")
	return [a for a in (get_attributes(item) or []) if a != dependent]


def _item_attribute_options(item):
	"""Attribute picker config for a (yarn) Item.

	Returns a list of {attribute, label, options:[...]} — one entry per
	attribute the item carries. Items with no attributes return []; the row
	then resolves straight to the item's self-named Item Variant.

	Drives both selectors and (via `_yarn_item_attributes`) the server-side
	required-attribute check, so picker and validator can never disagree.
	"""
	from yrp.yrp.doctype.item.item import get_attribute_values

	_assert_yarn_item_supported(item)

	attribute_names = _yarn_item_attributes(item)
	if not attribute_names:
		return []

	value_map = get_attribute_values(item) or {}
	options = []
	for attribute in attribute_names:
		values = value_map.get(attribute)
		if not values:
			# No mapping on the item — fall back to all values for the master.
			values = frappe.get_all(
				"Item Attribute Value",
				filters={"attribute_name": attribute},
				pluck="attribute_value",
				order_by="idx asc",
			)
		options.append({
			"attribute": attribute,
			"label": attribute,
			"options": values or [],
		})
	return options


@frappe.whitelist()
def get_yarn_deliverable_rows(work_order):
	"""Popup payload for Calculate Deliverables (yarn mode).

	For each `mgk_items` row, returns the IPD's yarn item, its UOM and the
	attribute picker config. Also reports whether the WO's process is a yarn
	process so the UI can guard which mode to render.
	"""
	wo = frappe.get_doc("Work Order", work_order)
	wo.check_permission("read")

	process = _get_wo_process(wo)
	is_yarn_process = bool(process.get("is_yarn_process"))

	legacy_rows = []
	transformation_rows = []
	missing_routes = []
	has_any_route_configuration = False
	for item_row in wo.get("mgk_items") or []:
		route_rows = get_process_route_context(
			item_row.production_detail,
			wo.process_name,
		) if item_row.production_detail else []
		for route_row in route_rows:
			transformation_rows.append({
				**route_row,
				"idx": item_row.idx,
				"item": item_row.item,
				"production_detail": item_row.production_detail,
			})

		yarn_item = _yarn_item_for_detail(item_row.production_detail)
		row = {
			"idx": item_row.idx,
			"item": item_row.item,
			"production_detail": item_row.production_detail,
			"yarn_item": yarn_item,
			"yarn_item_name": None,
			"uom": None,
			"attributes": [],
		}
		if yarn_item:
			# yrp's Item has no separate item_name field — its `name` IS the label.
			row["yarn_item_name"] = yarn_item
			row["uom"] = frappe.get_cached_value("Item", yarn_item, "default_unit_of_measure")
			row["attributes"] = _item_attribute_options(yarn_item)
		legacy_rows.append(row)

		if not route_rows and item_row.production_detail:
			ipd = frappe.get_cached_doc("Item Production Detail", item_row.production_detail)
			if ipd.get("mgk_yarn_process_routes"):
				has_any_route_configuration = True
			missing_routes.append(item_row.production_detail)

	if missing_routes and (
		transformation_rows or has_any_route_configuration
	):
		frappe.throw(
			_(
				"Process {0} is not configured in Item Production Detail(s): {1}. "
				"Remove those Item rows from this Work Order or add the matching "
				"Yarn Process step in the IPD."
			).format(wo.process_name, ", ".join(sorted(set(missing_routes))))
		)

	return {
		"work_order": wo.name,
		"process_name": wo.process_name,
		"is_yarn_process": is_yarn_process,
		"mode": "transformation" if transformation_rows else "legacy",
		"default_wastage": flt(process.get("default_wastage")),
		"default_excess": flt(process.get("default_excess")),
		"rows": transformation_rows or legacy_rows,
	}


@frappe.whitelist()
def calculate_deliverables(work_order, rows, modified=None):
	"""Dispatcher: pick the calculation mode from the WO's Process.

	`rows` is a JSON list (str or list already-parsed) of per-split inputs.
	Configured MGK route -> transformation; legacy yarn -> direct yarn;
	otherwise -> the existing matrix mode.
	`modified` is the client's loaded timestamp for the stale-write guard.
	"""
	rows = frappe.parse_json(rows) if isinstance(rows, str) else rows

	wo = frappe.get_doc("Work Order", work_order)
	wo.check_permission("write")
	_guard_not_modified(wo, modified)
	if wo.docstatus != 0:
		frappe.throw(_("Calculate Deliverables can only update a draft Work Order."))

	process = _get_wo_process(wo)
	has_configured_route = False
	has_any_route_configuration = False
	missing_process_details = []
	for row in wo.get("mgk_items") or []:
		if not row.production_detail:
			continue
		ipd = frappe.get_cached_doc(
			"Item Production Detail",
			row.production_detail,
		)
		has_any_route_configuration = (
			has_any_route_configuration
			or bool(ipd.get("mgk_yarn_process_routes"))
		)
		detail_has_process = has_yarn_process_route(
			row.production_detail,
			wo.process_name,
		)
		has_configured_route = has_configured_route or detail_has_process
		if not detail_has_process:
			missing_process_details.append(row.production_detail)
	if has_configured_route:
		if missing_process_details:
			frappe.throw(
				_(
					"Process {0} is not configured in Item Production "
					"Detail(s): {1}."
				).format(
					wo.process_name,
					", ".join(sorted(set(missing_process_details))),
				)
			)
		return _calculate_yarn_transformations(wo, rows)
	if has_any_route_configuration:
		frappe.throw(
			_(
				"Process {0} is not configured on this Work Order's Yarn "
				"Process Flow."
			).format(wo.process_name)
		)
	if process.get("is_yarn_process"):
		return _calculate_yarn_deliverables(wo, process, rows)

	return _calculate_matrix_deliverables(wo, rows)


def _prepare_yarn_transformation_items(wo, rows):
	"""Build calculated Work Order input/output rows from configured IPD routes."""
	if not rows:
		frappe.throw(_("Enter at least one route with an input quantity greater than zero."))

	detail_set = {
		row.production_detail
		for row in wo.get("mgk_items") or []
		if row.production_detail
	}
	deliverables_by_variant = {}
	receivables_by_variant = {}

	for raw in rows:
		if not isinstance(raw, dict):
			frappe.throw(_("Each Yarn Process calculation row must be an object."))

		production_detail = raw.get("production_detail")
		if not production_detail or production_detail not in detail_set:
			frappe.throw(
				_("Item Production Detail {0} is not part of Work Order {1}.").format(
					production_detail or _("(blank)"),
					wo.name,
				)
			)
		route_name = raw.get("route_name")
		if not route_name:
			frappe.throw(
				_("Select a Yarn Process route for Item Production Detail {0}.").format(
					production_detail
				)
			)

		ipd = frappe.get_doc("Item Production Detail", production_detail)
		io = build_route_io(
			ipd,
			wo.process_name,
			route_name,
			raw.get("attribute_values") or {},
			raw.get("weight") or raw.get("qty"),
		)
		input_variant = _resolve_yarn_variant(io["input_item"], io["input_attrs"])
		output_variant = _resolve_yarn_variant(io["output_item"], io["output_attrs"])

		deliverable_key = (input_variant, io["input_uom"])
		deliverable = deliverables_by_variant.setdefault(
			deliverable_key,
			{
				"item_variant": input_variant,
				"qty": 0,
				"pending_quantity": 0,
				"uom": io["input_uom"],
				"received_type": "Accepted",
				"is_calculated": 1,
			},
		)
		deliverable["qty"] += io["input_qty"]
		deliverable["pending_quantity"] += io["input_qty"]

		receivable_key = (output_variant, io["output_uom"])
		receivable = receivables_by_variant.setdefault(
			receivable_key,
			{
				"item_variant": output_variant,
				"qty": 0,
				"pending_quantity": 0,
				"uom": io["output_uom"],
			},
		)
		receivable["qty"] += io["output_qty"]
		receivable["pending_quantity"] += io["output_qty"]

	return list(deliverables_by_variant.values()), list(receivables_by_variant.values())


def _calculate_yarn_transformations(wo, rows):
	"""Persist explicit Yarn Item/Colour transformations for one Work Order."""
	new_deliverables, new_receivables = _prepare_yarn_transformation_items(wo, rows)
	if not new_deliverables or not new_receivables:
		frappe.throw(_("No Yarn Process inputs or outputs were calculated."))

	kept_deliverables = [
		row
		for row in (wo.get("deliverables") or [])
		if not row.get("is_calculated")
	]
	base_index = 0
	for row in kept_deliverables:
		base_index = max(
			base_index,
			_int_or_zero(row.get("table_index")),
			_int_or_zero(row.get("row_index")),
		)
	if kept_deliverables:
		base_index += 1
	for offset, row in enumerate(new_deliverables):
		row["table_index"] = base_index + offset
		row["row_index"] = str(base_index + offset)
	for offset, row in enumerate(new_receivables):
		row["table_index"] = offset
		row["row_index"] = str(offset)

	wo.set("deliverables", [])
	for row in kept_deliverables:
		wo.append("deliverables", row.as_dict())
	for row in new_deliverables:
		wo.append("deliverables", row)
	wo.set("receivables", new_receivables)

	# Prevent Work Order.before_validate from rebuilding the flat rows from
	# stale grouped-editor JSON.
	wo.deliverable_details = None
	wo.receivable_details = None
	wo.save()

	return {
		"work_order": wo.name,
		"mode": "transformation",
		"deliverables": len(new_deliverables),
		"receivables": len(new_receivables),
	}


def _calculate_yarn_deliverables(wo, process, rows):
	"""Direct-yarn deliverable/receivable calculation.

	Per row: resolve the yarn Item Variant from (yarn_item + picked attribute
	values), append a deliverable (qty = weight, received_type = Accepted) and
	a receivable (qty = weight * (1 - wastage% + excess%)). Idempotent: any
	previously-calculated rows are dropped first so re-running recalculates
	cleanly while preserving manual rows.
	"""
	if not rows:
		frappe.throw(_("Enter at least one row with a weight greater than zero."))

	default_wastage = flt(process.get("default_wastage"))
	default_excess = flt(process.get("default_excess"))
	factor = 1 - default_wastage / 100.0 + default_excess / 100.0
	if factor <= 0:
		# e.g. wastage > 100% — a non-positive factor would yield a zero/negative
		# receivable qty, which is nonsense. Stop with a clear message.
		frappe.throw(
			_(
				"Wastage {0}% / Excess {1}% give a non-positive conversion factor "
				"({2}); the receivable quantity would be zero or negative. "
				"Check the Process wastage and excess."
			).format(default_wastage, default_excess, flt(factor, 4))
		)

	# Resolve mgk_items rows by production_detail. Both frontends always send
	# production_detail, so we resolve solely on it (and verify the IPD belongs
	# to this WO); there is no idx fallback to keep untested.
	detail_set = {row.production_detail for row in wo.get("mgk_items") or [] if row.production_detail}

	new_deliverables = []
	new_receivables = []

	for raw in rows:
		production_detail = raw.get("production_detail")
		if production_detail and production_detail not in detail_set:
			frappe.throw(
				_("Item Production Detail {0} is not part of Work Order {1}.").format(
					production_detail, wo.name
				)
			)

		yarn_item = raw.get("yarn_item") or _yarn_item_for_detail(production_detail)
		if not yarn_item:
			frappe.throw(
				_("No Yarn Item is configured on Item Production Detail {0}.").format(
					production_detail
				)
			)

		weight = flt(raw.get("weight"))
		if weight <= 0:
			frappe.throw(_("Weight must be greater than zero for {0}.").format(yarn_item))

		# Validate the supplied attribute values against EXACTLY the attribute set
		# the picker presents (`_yarn_item_attributes`) — never `get_attributes`,
		# which would also demand the dependent attribute the picker omits. Reject
		# unsupported (dependent-attribute) yarn items up front.
		_assert_yarn_item_supported(yarn_item)
		attribute_values = raw.get("attribute_values") or {}
		required_attributes = _yarn_item_attributes(yarn_item)
		attrs = {k: v for k, v in attribute_values.items() if v}
		missing = [a for a in required_attributes if not attrs.get(a)]
		if missing:
			frappe.throw(
				_("Select a value for {0} on Yarn Item {1}.").format(
					", ".join(missing), yarn_item
				)
			)

		variant = _resolve_yarn_variant(yarn_item, attrs)
		uom = frappe.get_cached_value("Item", yarn_item, "default_unit_of_measure")

		deliverable_qty = weight
		receivable_qty = weight * factor

		new_deliverables.append({
			"item_variant": variant,
			"qty": deliverable_qty,
			"pending_quantity": deliverable_qty,
			"uom": uom,
			"received_type": "Accepted",
			"is_calculated": 1,
		})
		# NOTE: Work Order Receivables has no `is_calculated` field, so we cannot
		# tag receivables. In the yarn flow receivables are produced solely by this
		# calculation, so on re-run we replace the receivables table wholesale.
		new_receivables.append({
			"item_variant": variant,
			"qty": receivable_qty,
			"pending_quantity": receivable_qty,
			"uom": uom,
		})

	# Idempotent re-run for DELIVERABLES: drop previously-calculated rows
	# (is_calculated == 1), keep manual ones (e.g. received-goods rows).
	kept_deliverables = [r for r in (wo.get("deliverables") or []) if not r.get("is_calculated")]

	# Re-index the new calculated rows so their row_index/table_index start AFTER
	# the highest kept index — otherwise "0".."N" would collide with kept rows'
	# original indices and mis-group the deliverables pivot.
	base_index = 0
	for r in kept_deliverables:
		base_index = max(base_index, _int_or_zero(r.get("table_index")), _int_or_zero(r.get("row_index")))
	if kept_deliverables:
		base_index += 1
	for offset, row in enumerate(new_deliverables):
		row["table_index"] = base_index + offset
		row["row_index"] = str(base_index + offset)

	wo.set("deliverables", [])
	for row in kept_deliverables:
		wo.append("deliverables", row.as_dict())
	for row in new_deliverables:
		wo.append("deliverables", row)

	# RECEIVABLES carry no is_calculated flag and are calc-only in this flow, so
	# we replace the whole table — indices can safely start at 0.
	for offset, row in enumerate(new_receivables):
		row["table_index"] = offset
		row["row_index"] = str(offset)
	wo.set("receivables", new_receivables)

	# Work Order.before_validate -> sync_vue_item_details() rebuilds the flat
	# deliverables/receivables tables from the grouped-JSON fields whenever those
	# fields are truthy (even a stale "[]"), which would wipe the rows we just
	# appended. Clear them so the directly-appended flat rows survive the save;
	# the form's onload regenerates the grouped JSON from the flat rows on load.
	wo.deliverable_details = None
	wo.receivable_details = None

	wo.save()

	return {
		"work_order": wo.name,
		"deliverables": len(new_deliverables),
		"receivables": len(new_receivables),
	}


# ======================================================================
# IPD-Process-Matrix mode (non-yarn)
#
# Delegates to base-yrp's MAINTAINED engine entrypoint:
#   yrp.yrp.doctype.item_production_detail.item_production_detail
#       .calculate_major_deliverables(ipd, variant_demands,
#           process_names=[process], include_outputs=1)
# which scales the IPD Process Matrix for this WO's process and returns
# rows tagged side="Input" (deliverables) / side="Output" (receivables).
#
# This mirrors the canonical yrp_essdee wrapper
#   (yrp_essdee.yrp_essdee.yrp_essdee.api.work_order.calculate_deliverables)
# but PORTS the helper logic rather than importing it, because yrp_essdee is
# NOT installed on this site. The port omits everything Essdee-specific:
#   * yrp_essdee assumes a single-IPD, lot-style WO and resolves the IPD +
#     variant demands from the WO's `lot` / `lot_order_details`. Base-yrp's
#     Work Order has NO `lot` field, and MGK WOs are multi-item via the
#     `mgk_items` child table (each row = item + Item Production Detail, with
#     NO quantity and NO item_variant). So the lot-derived demand resolution
#     cannot be ported and is replaced by `_matrix_ipd_for_wo` /
#     `_matrix_variant_demands_from_rows` below.
#
# What is faithfully ported from the yrp_essdee reference:
#   * the calculate_major_deliverables call signature + include_outputs=1
#   * the side-split into deliverables / receivables
#   * `_to_work_order_items` -> `_matrix_to_work_order_items`
#   * `_assign_editor_indices` -> `_matrix_assign_editor_indices`
#     (table_index / row_index grouping, primary-attribute aware)
#   * the persistence fix: clear deliverable_details / receivable_details
#     before save() so the appended flat rows survive before_validate's
#     sync_vue_item_details() rebuild.
#
# COSTING: receivable rows are intentionally left uncosted here. The MGK
# controller override (overrides/work_order_class.MGKWorkOrder
# .set_receivable_process_costs) costs receivables on save; for a NON-yarn
# process it falls through to base behaviour (WO-level Process Cost), which is
# the correct/unchanged path. So we do NOT stamp process_cost per-row here.
# ======================================================================


def _calculate_matrix_deliverables(wo, rows):
	"""Non-yarn (IPD-Process-Matrix) Calculate Deliverables.

	Resolves the WO's single IPD and the per-variant demands, then calls
	base-yrp `calculate_major_deliverables` and populates the WO's
	deliverables (side="Input") and receivables (side="Output").

	HONEST GAP: MGK's `mgk_items` child table carries no quantities and no item
	variants, and the matrix UI was deferred by the user — so the demand
	(`[{item_variant, qty}]`) can only come from the `rows` payload. If the
	payload doesn't carry resolvable demands, or the WO's IPD can't be uniquely
	resolved (multiple distinct IPDs across `mgk_items`), we raise a specific
	error instead of fabricating a UI or inventing demands.
	"""
	if not wo.process_name:
		frappe.throw(_("Process Name is required to calculate deliverables."))

	ipd_name = _matrix_ipd_for_wo(wo)
	variant_demands = _matrix_variant_demands_from_rows(rows)
	if not variant_demands:
		frappe.throw(
			_(
				"Matrix-mode Calculate Deliverables for process '{0}' needs an "
				"IPD plus per-variant demands ([{{item_variant, qty}}]). The "
				"mgk_items child table carries no quantities or item variants, and "
				"the supplied rows did not include any (item_variant + qty). "
				"Matrix-mode demand entry is not yet wired for multi-item mgk_items "
				"Work Orders — send rows with item_variant and qty, or use a yarn "
				"process."
			).format(wo.process_name)
		)

	# --- CALL THE BASE / MAINTAINED FUNCTION ---
	from yrp.yrp.doctype.item_production_detail.item_production_detail import (
		calculate_major_deliverables,
	)

	calculated_rows = calculate_major_deliverables(
		ipd_name,
		variant_demands,
		process_names=[wo.process_name],
		include_outputs=1,
	)

	deliverables = _matrix_to_work_order_items(
		[row for row in calculated_rows if row.get("side") == "Input"],
		"deliverable",
	)
	receivables = _matrix_to_work_order_items(
		[row for row in calculated_rows if row.get("side") == "Output"],
		"receivable",
	)
	if not deliverables:
		frappe.throw(_("No deliverables were calculated for {0}.").format(wo.process_name))
	if not receivables:
		frappe.throw(_("No receivables were calculated for {0}.").format(wo.process_name))

	wo.set("deliverables", deliverables)
	wo.set("receivables", receivables)

	# Persistence fix (see _calculate_yarn_deliverables): before_validate ->
	# sync_vue_item_details() rebuilds the flat tables from the grouped-JSON
	# fields when those are truthy, wiping the rows we just set. Clear them so
	# the appended flat rows survive the save.
	wo.deliverable_details = None
	wo.receivable_details = None

	wo.save()

	return {
		"work_order": wo.name,
		"ipd": ipd_name,
		"deliverables": len(deliverables),
		"receivables": len(receivables),
	}


def _matrix_ipd_for_wo(wo):
	"""Resolve the single Item Production Detail driving this matrix WO.

	Preference order:
	  1. The WO's own `production_detail` (base-yrp WO field), when set.
	  2. A single distinct `production_detail` across all `mgk_items` rows.
	Raises a clear error when the IPD is absent, or when `mgk_items` spans
	multiple distinct IPDs (matrix mode is single-IPD; a multi-IPD WO needs the
	deferred matrix-mode spec to say which IPD/demand applies).
	"""
	if wo.get("production_detail"):
		return wo.production_detail

	details = sorted({
		row.production_detail
		for row in wo.get("mgk_items") or []
		if row.production_detail
	})
	if len(details) == 1:
		return details[0]
	if not details:
		frappe.throw(
			_(
				"No Item Production Detail is set on Work Order {0} (neither the "
				"WO's production_detail nor any mgk_items row). Matrix-mode "
				"Calculate Deliverables needs an IPD to scale the IPD Process "
				"Matrix."
			).format(wo.name)
		)
	frappe.throw(
		_(
			"Work Order {0} spans multiple Item Production Details ({1}). "
			"Matrix-mode Calculate Deliverables is single-IPD; multi-IPD "
			"mgk_items Work Orders are not yet wired (deferred matrix-mode spec)."
		).format(wo.name, ", ".join(details))
	)


def _matrix_variant_demands_from_rows(rows):
	"""Build base-engine variant demands ([{item_variant, qty}]) from the payload.

	The matrix engine scales by per-variant demand. MGK's mgk_items table has
	no quantities, so the demand must be supplied in `rows` as objects carrying
	`item_variant` and a positive `qty`/`quantity`/`weight`. Rows without an
	item_variant or with non-positive qty are ignored; returning [] signals the
	caller to raise the specific "needs IPD/demand" error.
	"""
	demands = []
	for row in rows or []:
		if not isinstance(row, dict):
			continue
		item_variant = row.get("item_variant")
		if not item_variant:
			continue
		qty = flt(row.get("qty") or row.get("quantity") or row.get("weight"))
		if qty <= 0:
			continue
		demands.append({"item_variant": item_variant, "qty": qty})
	return demands


def _matrix_to_work_order_items(calculated_rows, row_type):
	"""Map base-engine rows to Work Order Deliverables/Receivables child rows.

	Ported from yrp_essdee `_to_work_order_items`. Deliverables are flagged
	is_calculated=1; receivables are left UNcosted (process_cost/cost/total_cost
	stay unset) because the MGK controller override costs them on save.
	"""
	items = []
	for row in calculated_rows or []:
		qty = flt(row.get("required_qty") or row.get("qty"))
		if qty <= 0:
			continue
		item_variant = row.get("item_variant")
		out = {
			"item_variant": item_variant,
			"qty": qty,
			"pending_quantity": qty,
			"uom": row.get("uom") or _matrix_variant_uom(item_variant),
			"set_combination": {},
		}
		if row_type == "deliverable":
			out["is_calculated"] = 1
		items.append(out)
	_matrix_assign_editor_indices(items)
	return items


def _matrix_assign_editor_indices(rows):
	"""Assign table_index / row_index so the deliverables/receivables pivots group.

	Ported from yrp_essdee `_assign_editor_indices`. Groups rows into tables by
	the parent item's attribute shape, and into logical rows by attribute
	values (primary-attribute aware), so the grouped-JSON UI rebuild lays them
	out correctly.
	"""
	from yrp.yrp.doctype.item.item import get_attribute_details

	table_indexes = {}
	row_indexes = {}
	for row in rows:
		item_variant = row.get("item_variant")
		if not item_variant:
			continue
		parent_item = frappe.get_cached_value("Item Variant", item_variant, "item")
		if not parent_item:
			continue
		attr_details = get_attribute_details(parent_item)
		table_key = (
			tuple(sorted(attr_details.get("attributes") or [])),
			attr_details.get("primary_attribute") or "",
			tuple(sorted(attr_details.get("primary_attribute_values") or [])),
		)
		if table_key not in table_indexes:
			table_indexes[table_key] = len(table_indexes)

		attrs = _matrix_variant_attributes(item_variant)
		primary_attribute = attr_details.get("primary_attribute")
		if primary_attribute:
			logical_attrs = tuple(
				(attr, attrs.get(attr) or "")
				for attr in attr_details.get("attributes") or []
			)
			row_key = (table_key, parent_item, logical_attrs, row.get("uom") or "")
		else:
			row_key = (table_key, parent_item, tuple(sorted(attrs.items())), row.get("uom") or "")
		if row_key not in row_indexes:
			row_indexes[row_key] = len(row_indexes)

		row["table_index"] = table_indexes[table_key]
		row["row_index"] = row_indexes[row_key]


def _matrix_variant_attributes(item_variant):
	"""Attribute name -> value map for an Item Variant (ported helper)."""
	rows = frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": item_variant, "parenttype": "Item Variant"},
		fields=["attribute", "attribute_value"],
		order_by="idx asc",
	)
	return {row.attribute: row.attribute_value for row in rows}


def _matrix_variant_uom(item_variant):
	"""Default UOM for an Item Variant's template Item (ported helper)."""
	if not item_variant:
		return None
	item = frappe.get_cached_value("Item Variant", item_variant, "item")
	return frappe.get_cached_value("Item", item, "default_unit_of_measure") if item else None
