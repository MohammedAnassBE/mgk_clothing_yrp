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
			@update:modelValue="onModelUpdate"
			:suggestions="suggestions"
			optionLabel="label"
			@complete="onComplete"
			@item-select="onItemSelect"
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
	// Optional custom search: async (query) => Array<{ name }>. When provided,
	// it replaces the default name-like search (used for Addresses where the
	// link is via Dynamic Link rather than a direct field, so a plain filter
	// can't reach the parent party — see `searchAddressForParty`).
	searchHandler: { type: Function, default: null },
})
const emit = defineEmits(["update:modelValue", "item-select", "change"])

// Suggestions are objects { name, label } — `label` (title/search-field text) is
// shown via optionLabel, while `name` is the value stored on select. A search
// handler may still return plain {name} rows (no label) — we normalise those so
// the dropdown always has a label to render.
const suggestions = ref([])

function normaliseRows(rows) {
	return (rows || []).map((r) =>
		typeof r === "string"
			? { name: r, label: r }
			: { name: r.name, label: r.label || r.name },
	)
}

async function onComplete(e) {
	if (!props.searchHandler && !props.targetDoctype) {
		suggestions.value = []
		return
	}
	try {
		const rows = props.searchHandler
			? await props.searchHandler(e.query || "")
			: await searchLink(props.targetDoctype, e.query || "", props.filters)
		suggestions.value = normaliseRows(rows)
	} catch (_) {
		suggestions.value = []
	}
}

// Selecting a suggestion stores its `name` (the Link value), not the object.
function onItemSelect(e) {
	const name = e?.value?.name ?? e?.value ?? ""
	emit("update:modelValue", name)
	emit("item-select", { value: name, originalEvent: e?.originalEvent })
}

// Free-text typing / clearing comes through as a string; an object can slip
// through if PrimeVue echoes the selected suggestion — normalise to the name.
function onModelUpdate(v) {
	emit("update:modelValue", v && typeof v === "object" ? v.name : v)
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
