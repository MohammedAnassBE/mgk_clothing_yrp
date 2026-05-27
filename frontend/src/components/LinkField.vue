<!--
  LinkField — a Link / Dynamic Link input: PrimeVue AutoComplete + a "go to
  linked document" button (mirrors the Frappe Desk link arrow). The button opens
  the linked record's /web detail (or the Desk form, for doctypes not in the /web
  registry) in a NEW TAB, so the current form/edit isn't lost.

  The parent resolves the target doctype (incl. Dynamic Links → the controlling
  field's value) and passes it as `target-doctype`. Search is internal.
-->
<template>
	<div class="link-field">
		<AutoComplete
			:modelValue="modelValue"
			@update:modelValue="$emit('update:modelValue', $event)"
			:suggestions="suggestions"
			@complete="onComplete"
			@item-select="$emit('item-select', $event)"
			@change="$emit('change', $event)"
			:disabled="disabled"
			:invalid="invalid"
			:placeholder="placeholder || ('Search ' + (targetDoctype || '') + '…')"
			dropdown
			completeOnFocus
			class="fld fld-link"
			fluid
		/>
		<Button
			v-if="modelValue && targetDoctype"
			icon="pi pi-arrow-up-right"
			text
			rounded
			size="small"
			class="link-goto"
			v-tooltip.top="'Open ' + modelValue"
			@click="openLinked"
		/>
	</div>
</template>

<script setup>
import { ref } from "vue"
import AutoComplete from "primevue/autocomplete"
import Button from "primevue/button"
import Tooltip from "primevue/tooltip"
import { searchLink } from "@/api/client"
import { getRegistryByDoctype } from "@/config/doctypes"

const vTooltip = Tooltip

const props = defineProps({
	modelValue: { type: [String, Number], default: "" },
	// Resolved target doctype (parent resolves Dynamic Links before passing).
	targetDoctype: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
	invalid: { type: Boolean, default: false },
	filters: { type: Object, default: () => ({}) },
})
defineEmits(["update:modelValue", "item-select", "change"])

const suggestions = ref([])

async function onComplete(e) {
	if (!props.targetDoctype) {
		suggestions.value = []
		return
	}
	try {
		const rows = await searchLink(props.targetDoctype, e.query || "", props.filters)
		suggestions.value = rows.map((r) => r.name)
	} catch (_) {
		suggestions.value = []
	}
}

// Open the linked record (new tab): /web detail if the doctype is in the registry,
// else the Desk form. New tab keeps the current form/edit intact.
function openLinked() {
	if (!props.modelValue || !props.targetDoctype) return
	const reg = getRegistryByDoctype(props.targetDoctype)
	const path = reg
		? `/web/${reg.route}/${encodeURIComponent(props.modelValue)}`
		: `/app/${encodeURIComponent(props.targetDoctype.toLowerCase().replace(/ /g, "-"))}/${encodeURIComponent(props.modelValue)}`
	window.open(window.location.origin + path, "_blank", "noopener")
}
</script>

<style scoped>
.link-field {
	display: flex;
	align-items: center;
	gap: 4px;
}
.link-field .fld-link {
	flex: 1;
	min-width: 0;
}
.link-goto {
	flex-shrink: 0;
	color: var(--mgk-accent-700);
}
</style>
