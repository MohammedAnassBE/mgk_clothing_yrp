// mgk_clothing_yrp — Purchase Order (Phase 1, Greige Yarn procurement).
//
// The `mgk_handling_supplier` Custom Field already shows/hides and toggles
// mandatory via its `depends_on` / `mandatory_depends_on`. This script only
// clears a stale handling-supplier value when the user switches routing back
// to "Direct", so a hidden value can't survive on the saved doc.

frappe.ui.form.on("Purchase Order", {
	mgk_goods_routing(frm) {
		if (frm.doc.mgk_goods_routing !== "Through Vendor" && frm.doc.mgk_handling_supplier) {
			frm.set_value("mgk_handling_supplier", null);
		}
	},
});
