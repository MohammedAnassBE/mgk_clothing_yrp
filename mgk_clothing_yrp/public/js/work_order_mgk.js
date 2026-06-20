// mgk_clothing_yrp — Work Order design-approval gate (Phase 3, Weaving).
// Renders entirely from the server's get_approval_state, so the role logic
// stays server-side (the client never decides who may approve).
frappe.ui.form.on("Work Order", {
	refresh(frm) {
		if (frm.is_new()) return;
		frappe.call({
			method: "mgk_clothing_yrp.mgk_clothing_yrp.api.work_order.get_approval_state",
			args: { work_order: frm.doc.name },
			callback(r) {
				const s = r.message || {};
				if (!s.needs_approval) return; // process not gated in MGK Settings
				if (s.rejection_reason) {
					frm.dashboard.set_headline(__("Design rejected: {0}", [frappe.utils.escape_html(s.rejection_reason)]));
				} else if (s.approved_by) {
					frm.dashboard.set_headline(__("Design approved by {0}", [frappe.utils.escape_html(s.approved_by)]));
				}
				if (s.docstatus === 0 && s.can_approve && !s.approved_by) {
					frm.add_custom_button(__("Approve / Reject"), () => open_mgk_approval_dialog(frm));
				}
			},
		});
	},
});

function open_mgk_approval_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Design Approval"),
		fields: [{ fieldname: "reason", fieldtype: "Small Text", label: __("Rejection Reason (required only to reject)") }],
		primary_action_label: __("Approve"),
		primary_action() {
			d.hide();
			frappe.call({
				method: "mgk_clothing_yrp.mgk_clothing_yrp.api.work_order.approve",
				args: { work_order: frm.doc.name },
				freeze: true,
				callback(r) {
					if (!r.exc) {
						frappe.show_alert({ message: __("Approved"), indicator: "green" });
						frm.reload_doc();
					}
				},
			});
		},
		secondary_action_label: __("Reject"),
		secondary_action() {
			const reason = (d.get_value("reason") || "").trim();
			if (!reason) {
				frappe.msgprint(__("Enter a reason to reject."));
				return;
			}
			d.hide();
			frappe.call({
				method: "mgk_clothing_yrp.mgk_clothing_yrp.api.work_order.reject",
				args: { work_order: frm.doc.name, reason },
				freeze: true,
				callback(r) {
					if (!r.exc) {
						frappe.show_alert({ message: __("Rejected"), indicator: "red" });
						frm.reload_doc();
					}
				},
			});
		},
	});
	d.show();
}

// mgk_clothing_yrp — multi-item Work Order: per-row IPD filter + Calculate Deliverables.
// The single header item/production_detail are hidden (Property Setters); the user
// enters multiple (Item + Item Production Detail) rows in the `mgk_items` child table.
frappe.ui.form.on("Work Order", {
	refresh(frm) {
		// Filter each row's Item Production Detail to that row's Item.
		frm.set_query("production_detail", "mgk_items", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return { filters: row.item ? { item: row.item } : {} };
		});
		// Calculate Deliverables — yarn-mode split editor (one block per mgk_items row).
		frm.add_custom_button(__("Calculate Deliverables"), () => open_calculate_deliverables(frm));
	},
});

// ── Calculate Deliverables (MGK, yarn mode) ─────────────────────────────────
// Fetches the per-row payload from the server, then renders ONE block per
// mgk_items row inside a single Dialog: a read-only yarn-item label, a Select
// per attribute (options from the payload), and a Float weight input. The
// dialog fields are generated dynamically (fieldnames `attr_<idx>_<attribute>`
// and `weight_<idx>`) so a row whose yarn item has no attributes simply gets a
// weight input and no selectors.
function open_calculate_deliverables(frm) {
	frappe.call({
		method: "mgk_clothing_yrp.mgk_clothing_yrp.api.work_order.get_yarn_deliverable_rows",
		args: { work_order: frm.doc.name },
		freeze: true,
		callback(r) {
			const payload = r.message || {};
			if (r.exc) return;
			if (!payload.is_yarn_process) {
				frappe.msgprint({
					title: __("Not a Yarn Process"),
					message: __(
						"The process '{0}' on this Work Order is not a Yarn Process. The IPD-Process-Matrix calculation mode is not yet available.",
						[frappe.utils.escape_html(payload.process_name || "")]
					),
					indicator: "orange",
				});
				return;
			}
			const rows = payload.rows || [];
			if (!rows.length) {
				frappe.msgprint(__("Add at least one Item row to this Work Order first."));
				return;
			}
			render_calculate_dialog(frm, payload, rows);
		},
	});
}

function render_calculate_dialog(frm, payload, rows) {
	// Build dialog fields dynamically: one Section Break per row, holding a
	// read-only yarn-item display + one Select per attribute + a Float weight.
	const fields = [];
	rows.forEach((row, i) => {
		const yarn_label = row.yarn_item_name || row.yarn_item || "";
		fields.push({
			fieldtype: "Section Break",
			label: row.yarn_item
				? __("Row {0}: {1}", [row.idx, frappe.utils.escape_html(yarn_label)])
				: __("Row {0}: {1}", [row.idx, frappe.utils.escape_html(row.item || "")]),
		});

		if (!row.yarn_item) {
			// No yarn item configured on the IPD — show a note, no inputs to gather.
			fields.push({
				fieldtype: "HTML",
				fieldname: `note_${i}`,
				options: `<div class="text-muted small">${__(
					"No Yarn Item is configured on Item Production Detail {0}; this row will be skipped.",
					[frappe.utils.escape_html(row.production_detail || "")]
				)}</div>`,
			});
			return;
		}

		// Read-only yarn item display.
		fields.push({
			fieldtype: "Data",
			fieldname: `yarn_${i}`,
			label: __("Yarn Item"),
			read_only: 1,
			default: yarn_label,
		});

		// One Select per attribute (options from the payload). A yarn item with
		// no attributes contributes no selectors — just the weight below.
		(row.attributes || []).forEach((attr) => {
			fields.push({
				fieldtype: "Select",
				fieldname: `attr_${i}_${attr.attribute}`,
				label: attr.label || attr.attribute,
				options: (attr.options || []).join("\n"),
				reqd: 1,
			});
		});

		fields.push({ fieldtype: "Column Break" });
		fields.push({
			fieldtype: "Float",
			fieldname: `weight_${i}`,
			label: __("Weight ({0})", [row.uom || ""]),
			reqd: 1,
			precision: 3,
		});
	});

	const wastage = flt_num(payload.default_wastage);
	const excess = flt_num(payload.default_excess);
	const factor = (1 - wastage / 100 + excess / 100).toFixed(4);

	const d = new frappe.ui.Dialog({
		title: __("Calculate Deliverables"),
		fields: fields,
		size: "large",
		primary_action_label: __("Calculate"),
		primary_action() {
			const values = d.get_values(); // returns null + highlights if reqd missing
			if (!values) return;
			const out = [];
			rows.forEach((row, i) => {
				if (!row.yarn_item) return; // skipped — no yarn item on the IPD
				const weight = flt_num(values[`weight_${i}`]);
				if (weight <= 0) {
					frappe.throw(
						__("Weight must be greater than zero for {0}.", [
							row.yarn_item_name || row.yarn_item,
						])
					);
				}
				const attribute_values = {};
				(row.attributes || []).forEach((attr) => {
					attribute_values[attr.attribute] = values[`attr_${i}_${attr.attribute}`];
				});
				out.push({
					production_detail: row.production_detail,
					yarn_item: row.yarn_item,
					attribute_values: attribute_values,
					weight: weight,
				});
			});
			if (!out.length) {
				frappe.msgprint(__("No rows with a configured Yarn Item to calculate."));
				return;
			}
			frappe.call({
				method: "mgk_clothing_yrp.mgk_clothing_yrp.api.work_order.calculate_deliverables",
				args: { work_order: frm.doc.name, rows: JSON.stringify(out) },
				freeze: true,
				freeze_message: __("Calculating deliverables…"),
				callback(r) {
					if (r.exc) return; // server message already shown by Frappe
					const res = r.message || {};
					d.hide();
					frappe.show_alert({
						message: __("Calculated {0} deliverable(s) and {1} receivable(s).", [
							res.deliverables,
							res.receivables,
						]),
						indicator: "green",
					});
					frm.reload_doc();
				},
			});
		},
	});

	// Surface the wastage/excess factor so the user knows what scales receivables.
	d.$wrapper
		.find(".modal-header .modal-title")
		.after(
			`<div class="text-muted small" style="margin-top:4px">${__(
				"Wastage {0}% · Excess {1}% → receivable = weight × {2}",
				[wastage, excess, factor]
			)}</div>`
		);

	d.show();
}

// Small numeric coercion helper (Frappe's flt may not be globally aliased here).
function flt_num(v) {
	const n = parseFloat(v);
	return isNaN(n) ? 0 : n;
}

