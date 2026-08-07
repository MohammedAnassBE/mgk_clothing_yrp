import { createApp } from "vue";

import YarnProcessFlow from "./YarnProcessFlow.vue";

frappe.provide("frappe.mgk.ui");

function mount_component(component, wrapper) {
	const app = createApp(component);
	if (typeof SetVueGlobals === "function") {
		SetVueGlobals(app);
	}
	return {
		app,
		vue: app.mount($(wrapper).get(0)),
	};
}

frappe.mgk.ui.YarnProcessFlow = class {
	constructor(wrapper, opts = {}) {
		this.$wrapper = $(wrapper);
		this.opts = opts;
		const mounted = mount_component(YarnProcessFlow, this.$wrapper);
		this.app = mounted.app;
		this.vue = mounted.vue;
	}

	load_data(payload) {
		this.vue.load_data(
			JSON.parse(JSON.stringify(payload || {})),
			this.opts.on_change
		);
	}

	get_steps() {
		return JSON.parse(JSON.stringify(this.vue.get_steps()));
	}
};
