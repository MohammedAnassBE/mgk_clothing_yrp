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
