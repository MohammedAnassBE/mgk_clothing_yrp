// MGK yarn IPD editor. This is intentionally a standard Frappe Desk form;
// the /web SPA does not participate in yarn-process configuration.
frappe.ui.form.on("Item Production Detail", {
	setup(frm) {
		frm.set_query("item", () => ({ filters: { disabled: 0 } }));
		frm.set_query("process_name", "mgk_yarn_process_routes", () => ({
			filters: { is_yarn_process: 1, is_group: 0 },
		}));
		["input_item", "output_item"].forEach((fieldname) => {
			frm.set_query(fieldname, "mgk_yarn_process_routes", () => ({
				filters: { is_yarn_item: 1 },
			}));
		});
		["from_colour", "to_colour"].forEach((fieldname) => {
			frm.set_query(fieldname, "mgk_yarn_process_routes", () => ({
				filters: { attribute_name: "Colour" },
			}));
		});
	},

	refresh(frm) {
		frm.set_intro(
			__(
				"Define the yarn flow for this finished Item. Doubling changes the Yarn Item; Dyeing keeps the Item and changes Colour."
			),
			"blue"
		);
		mount_finished_item_attribute_values(frm);
		mount_yarn_process_editor(frm);
	},
});

frappe.ui.form.on("MGK Yarn Process Route", {
	mgk_yarn_process_routes_add(frm, cdt, cdn) {
		const current = locals[cdt][cdn];
		const max_sequence = Math.max(
			0,
			...(frm.doc.mgk_yarn_process_routes || [])
				.filter((row) => row.name !== current.name)
				.map((row) => parseInt(row.sequence, 10) || 0)
		);
		frappe.model.set_value(cdt, cdn, "sequence", max_sequence + 10);
		frappe.model.set_value(cdt, cdn, "quantity_ratio", 1);
	},

	async process_name(frm, cdt, cdn) {
		await apply_process_shape(cdt, cdn);
	},

	async input_item(frm, cdt, cdn) {
		await apply_process_shape(cdt, cdn);
	},
});

async function apply_process_shape(cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.process_name) return;

	const process = await frappe.db.get_doc("Process", row.process_name);
	if (process.is_item_conversion) {
		await frappe.model.set_value(cdt, cdn, "from_colour", null);
		await frappe.model.set_value(cdt, cdn, "to_colour", null);
		return;
	}

	const changes_colour = (process.value_change_attributes || []).some(
		(entry) => entry.attribute === "Colour"
	);
	if (changes_colour && row.input_item) {
		await frappe.model.set_value(cdt, cdn, "output_item", row.input_item);
	}
}

let yarn_process_catalog = null;

function mount_finished_item_attribute_values(frm) {
	const field = frm.fields_dict.item_attribute_list_values_html;
	if (
		!field ||
		!frappe.production?.ui?.ItemAttributeList ||
		frm.doc.__islocal
	) {
		return;
	}
	if (frm.__mgk_attribute_list?.app) {
		frm.__mgk_attribute_list.app.unmount();
	}
	$(field.wrapper).empty();
	frm.__mgk_attribute_list = new frappe.production.ui.ItemAttributeList({
		wrapper: field.wrapper,
		attr_values: frm.doc.__onload?.attr_list || [],
	});
}

async function get_yarn_process_catalog() {
	if (yarn_process_catalog) return yarn_process_catalog;
	const response = await frappe.call({
		method: "mgk_clothing_yrp.mgk_clothing_yrp.api.experiences.operations_workspace.item_production_detail.get_entry_context",
	});
	const context = response.message || {};
	const items = context.yarn_items || [];
	yarn_process_catalog = {
		processes: context.processes || [],
		yarn_items: items.map((row) => row.name),
		colours: [...new Set(items.flatMap((row) => row.colours || []))],
	};
	return yarn_process_catalog;
}

async function mount_yarn_process_editor(frm) {
	const field = frm.fields_dict.mgk_yarn_process_editor;
	if (!field || !frappe.mgk?.ui?.YarnProcessFlow) return;
	if (frm.__mgk_yarn_flow?.app) {
		frm.__mgk_yarn_flow.app.unmount();
	}
	$(field.wrapper).empty();
	const catalog = await get_yarn_process_catalog();
	const can_write = (frm.perm || []).some((permission) => permission.write);
	frm.__mgk_yarn_flow = new frappe.mgk.ui.YarnProcessFlow(field.wrapper, {
		on_change: (payload) => write_yarn_process_routes(frm, payload),
	});
	frm.__mgk_yarn_flow.load_data({
		...catalog,
		editable: frm.doc.docstatus === 0 && can_write,
		routes: (frm.doc.mgk_yarn_process_routes || []).map((row) => ({
			sequence: row.sequence,
			process_name: row.process_name,
			input_item: row.input_item,
			output_item: row.output_item,
			from_colour: row.from_colour,
			to_colour: row.to_colour,
			quantity_ratio: row.quantity_ratio,
		})),
	});
}

function write_yarn_process_routes(frm, payload) {
	frm.clear_table("mgk_yarn_process_routes");
	(payload.routes || []).forEach((values) => {
		Object.assign(frm.add_child("mgk_yarn_process_routes"), values);
	});
	frm.refresh_field("mgk_yarn_process_routes");
	frm.dirty();
}
