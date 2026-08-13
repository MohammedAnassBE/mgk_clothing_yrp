"""MGK Work Order controller override: per-row yarn process costing.

Base yrp's `Work Order.set_receivable_process_costs` looks up a SINGLE
Process Cost keyed on the WO's single `self.item` (via
`get_receivable_process_cost`) and `frappe.throw`s if none is found. MGK
multi-item (mgk_items) Work Orders leave `item` empty, so that path always
throws once receivables exist.

For a yarn Process (`is_yarn_process` on the Process), each Work Order
Receivables row is its own yarn variant, so it must be costed by ITS OWN yarn
template item's Process Cost. The WO-level `process_cost` single-link stays
empty (multi-item). For every NON-yarn Process the override defers entirely to
base behaviour (`super()`), so nothing else changes.

Wired via `override_doctype_class["Work Order"]` in hooks.py.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from yrp.yrp.doctype.work_order.work_order import (
	WorkOrder,
	get_process_cost_rate,
)


class MGKWorkOrder(WorkOrder):
	def before_validate(self):
		"""Require one authoritative IPD and derive the hidden base Item from it."""
		from mgk_clothing_yrp.mgk_clothing_yrp.api.work_order import (
			_work_order_ipd_context,
		)

		ipd, _process, _mode = _work_order_ipd_context(
			self, check_permission=False
		)
		self.item = ipd.item
		super().before_validate()

	def get_submit_readiness_issues(self):
		"""Extend base readiness with MGK multi-IPD and design gates."""
		issues = super().get_submit_readiness_issues()
		ipd_names = {
			row.get("production_detail")
			for row in self.get("mgk_items") or []
			if row.get("production_detail")
			and row.get("production_detail") != self.get("production_detail")
		}
		if ipd_names:
			statuses = {
				row.name: row.approval_status or "Not Approved"
				for row in frappe.get_all(
					"Item Production Detail",
					filters={"name": ["in", sorted(ipd_names)]},
					fields=["name", "approval_status"],
				)
			}
			for ipd_name in sorted(ipd_names):
				status = statuses.get(ipd_name, "Missing")
				if status != "Approved":
					issues.append(
						_("Item Production Detail {0} is not Approved (status: {1}).").format(
							ipd_name, status
						)
					)

		from mgk_clothing_yrp.mgk_clothing_yrp.api.work_order import get_approver_role

		approver_role = get_approver_role(self.process_name)
		if approver_role and not self.get("approved_by"):
			issues.append(
				_("Design approval by role {0} is required for process {1}.").format(
					approver_role, self.process_name
				)
			)
		return issues

	def get_process_cost_readiness_issues(self):
		"""Use one approved Process Cost per receivable yarn Item."""
		process = (
			frappe.get_cached_doc("Process", self.process_name)
			if self.process_name
			else None
		)
		if not process or not process.get("is_yarn_process"):
			return super().get_process_cost_readiness_issues()
		if (
			not self.get("receivables")
			or self.get("is_rework")
			or self.get("rework_type") == "No Cost"
		):
			return []

		missing_items = set()
		for row in self.receivables:
			item = frappe.db.get_value("Item Variant", row.item_variant, "item")
			if item and not self._find_process_cost_for_item(item):
				missing_items.add(item)
		return [
			_("No approved Process Cost for yarn item {0} / process {1} / supplier {2}.").format(
				item,
				self.process_name or _("(not selected)"),
				self.supplier or _("(any supplier)"),
			)
			for item in sorted(missing_items)
		]

	def set_receivable_process_costs(self, require_approved=False):
		"""Cost receivables per-row for yarn processes; defer to base otherwise."""
		# Resolve the WO's Process. Anything that is NOT an is_yarn_process
		# Process (including a WO with no process) uses unchanged base behaviour.
		process = None
		if self.process_name:
			process = frappe.get_cached_doc("Process", self.process_name)
		if not process or not process.get("is_yarn_process"):
			return super().set_receivable_process_costs(
				require_approved=require_approved
			)

		# --- yarn process: per-row costing ---
		if not self.get("receivables"):
			return

		if self.get("rework_type") == "No Cost":
			# Mirror base's No-Cost short-circuit: clear costs, leave WO link empty.
			self.process_cost = None
			for row in self.receivables:
				row.process_cost = None
				row.cost = 0
				row.total_cost = 0
			return

		# Multi-item: the WO-level single Process Cost link stays empty.
		self.process_cost = None

		for row in self.receivables:
			# Each receivable row is a yarn Item Variant; its template Item is the
			# Process Cost key (Process Cost is defined per Item, not per variant).
			yarn_item = frappe.db.get_value("Item Variant", row.item_variant, "item")
			if not yarn_item:
				frappe.throw(
					_("Receivable row {0} has no resolvable Item for variant {1}.").format(
						row.idx, row.item_variant
					)
				)

			pc_name = self._find_process_cost_for_item(yarn_item)
			if not pc_name:
				# Mirror base's is_rework early return: a rework WO with no
				# matching Process Cost is left uncosted rather than blocking.
				if self.get("is_rework"):
					return
				if not require_approved and self.allow_draft_without_process_cost():
					# Match YRP core: draft Work Orders may be prepared before
					# their approved Process Costs exist. A stricter customer app
					# can override the same one-method base policy. Do not retain
					# a stale cost after the Item/process/supplier changes.
					row.process_cost = None
					row.cost = 0
					row.total_cost = 0
					continue
				frappe.throw(
					_(
						"No approved Process Cost for yarn item {0} / process {1} / supplier {2}. "
						"Create one under Process & Setup → Process Cost and get it approved "
						"so this yarn receivable can be costed."
					).format(
						yarn_item,
						self.process_name,
						self.supplier or _("(any supplier)"),
					)
				)

			pc_doc = frappe.get_doc("Process Cost", pc_name)
			rate = get_process_cost_rate(row.item_variant, row.qty, pc_doc)
			row.process_cost = pc_name
			row.cost = round(rate, 3)
			row.total_cost = round(rate * flt(row.qty), 2)

	def _find_process_cost_for_item(self, item):
		"""Approved Process Cost name for `item` on this WO's process/dimensions.

		Mirrors yrp's `Work Order.get_receivable_process_cost` exactly, but keyed
		on the passed-in yarn template `item` instead of the WO's single
		`self.item`. Same filters: process_name, item, is_expired=0,
		from_date<=wo_date, docstatus=1, optional supplier, is_rework match, the
		production-group dimension filters, and workflow_state="Approved" when a
		Process Cost workflow is active. Honors to_date>=wo_date.
		"""
		if not self.process_name or not item or not self.wo_date:
			return None

		meta = frappe.get_meta("Process Cost")
		filters = [
			["process_name", "=", self.process_name],
			["item", "=", item],
			["is_expired", "=", 0],
			["from_date", "<=", self.wo_date],
			["docstatus", "=", 1],
		]
		if self.supplier:
			filters.append(["supplier", "=", self.supplier])
		if meta.get_field("is_rework"):
			filters.append(["is_rework", "=", 1 if self.get("is_rework") else 0])

		from yrp.stock.dimensions import append_production_group_filters

		append_production_group_filters(filters, self, "Process Cost")

		if meta.get_field("workflow_state") and frappe.db.exists(
			"Workflow", {"document_type": "Process Cost", "is_active": 1}
		):
			filters.append(["workflow_state", "=", "Approved"])

		process_costs = frappe.get_all(
			"Process Cost",
			filters=filters,
			fields=["name", "to_date"],
			order_by="from_date desc, creation desc",
		)
		wo_date = getdate(self.wo_date)
		for process_cost in process_costs:
			if process_cost.to_date and getdate(process_cost.to_date) < wo_date:
				continue
			return process_cost.name
		return None
