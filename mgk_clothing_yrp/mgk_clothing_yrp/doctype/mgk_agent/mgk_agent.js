// Copyright (c) 2026, MGK Clothing and contributors
// For license information, please see license.txt

// Mirrors yrp's Supplier form script so Frappe's universal Address & Contact
// widgets render. The server-side `load_address_and_contact` (mgk_agent.py)
// only populates __onload; this client call paints the Address/Contact cards
// and their "New Address / New Contact" buttons on a saved record.
frappe.ui.form.on("MGK Agent", {
	refresh(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: "name", doctype: "MGK Agent" };
		if (frm.doc.__islocal) {
			hide_field(["address_html", "contact_html"]);
			frappe.contacts.clear_address_and_contact(frm);
		} else {
			unhide_field(["address_html", "contact_html"]);
			frappe.contacts.render_address_and_contact(frm);
		}
	},
});
