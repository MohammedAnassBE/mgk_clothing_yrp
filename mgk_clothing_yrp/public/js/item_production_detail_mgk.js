// mgk_clothing_yrp — restrict the Yarn Item link to Items flagged "Is Yarn Item".
// The is_yarn_item flag is an MGK custom field on Item; only flagged items are
// selectable in the Item Production Detail's yarn_item link field.
frappe.ui.form.on("Item Production Detail", {
	refresh(frm) {
		frm.set_query("yarn_item", () => {
			return { filters: { is_yarn_item: 1 } };
		});
	},
});
