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
			ref="autoCompleteRef"
			:modelValue="inputValue"
			@update:modelValue="onModelUpdate"
			:suggestions="suggestions"
			optionLabel="label"
			@complete="onComplete"
			@item-select="onItemSelect"
			@change="onChange"
			@focus="onFocus"
			@blur="onBlur"
			:disabled="disabled"
			:invalid="invalid"
			:placeholder="placeholder || ('Search ' + (targetDoctype || '') + '…')"
			:dropdown="dropdown"
			:delay="searchDelay"
			class="fld fld-link"
			fluid
		>
			<!-- Q14: honest empty state — searching vs no-matches vs a retryable
			     search error, so a flaky-network failure never reads as "nothing
			     exists". -->
			<template #empty>
				<div class="lf-empty">
					<span v-if="searching"><i class="pi pi-spin pi-spinner" /> Searching…</span>
					<span
						v-else-if="errored"
						class="lf-retry"
						@mousedown.prevent="retrySearch"
					><i class="pi pi-refresh" /> Couldn’t search — retry</span>
					<span v-else>No matches</span>
				</div>
			</template>
		</AutoComplete>
		<Button
			v-if="linkedPath"
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
import { computed, ref, watch } from "vue"
import AutoComplete from "primevue/autocomplete"
import Button from "primevue/button"
import Tooltip from "primevue/tooltip"
import { searchLink } from "@/api/client"
import { getRegistryByDoctype } from "@/config/doctypes"
import { useDisplayLanguage } from "@/composables/useDisplayLanguage"
import { useLinkTitles } from "@/composables/useLinkTitles"

const vTooltip = Tooltip
const autoCompleteRef = ref(null)

const props = defineProps({
	modelValue: { type: [String, Number], default: "" },
	// Resolved target doctype (parent resolves Dynamic Links before passing).
	targetDoctype: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
	invalid: { type: Boolean, default: false },
	filters: { type: Object, default: () => ({}) },
	// Show the select-style dropdown chevron. Default true (existing pickers).
	// Pass false for a clean "Link field" look — a search/typeahead input with no
	// select chevron (suggestions still appear on focus + as you type).
	dropdown: { type: Boolean, default: true },
	// Optional custom search: async (query) => Array<{ name }>. When provided,
	// it replaces the default name-like search (used for Addresses where the
	// link is via Dynamic Link rather than a direct field, so a plain filter
	// can't reach the parent party — see `searchAddressForParty`).
	searchHandler: { type: Function, default: null },
	// Debounce server-backed Link searches. PrimeVue emits `complete` only after
	// this quiet period, so normal typing produces one request instead of one
	// request per keypress.
	searchDelay: { type: Number, default: 350 },
	// Registered Experiences own their internal route vocabulary. When supplied,
	// this resolver is authoritative and returns a router path such as
	// `/master/suppliers/S-0010`; an empty result hides the arrow safely.
	routeResolver: { type: Function, default: null },
})
const emit = defineEmits(["update:modelValue", "item-select", "change"])
const { language } = useDisplayLanguage()
const linkTitles = useLinkTitles()

// Autocomplete text is a local search query. The parent model holds only a
// confirmed Frappe Link name, never partial text such as "Sam".
const inputValue = ref("")
const hasUncommittedQuery = ref(false)
const committedLabel = computed(() =>
	linkTitles.titleFor(props.targetDoctype, props.modelValue) || String(props.modelValue ?? ""),
)
watch(
	[() => props.modelValue, () => props.targetDoctype, language, committedLabel],
	async ([value, doctype]) => {
		if (value && doctype) await linkTitles.prime([{ doctype, name: value }])
		if (!hasUncommittedQuery.value) inputValue.value = committedLabel.value
	},
	{ immediate: true },
)

// Suggestions are objects { name, label } — `label` (title/search-field text) is
// shown via optionLabel, while `name` is the value stored on select. A search
// handler may still return plain {name} rows (no label) — we normalise those so
// the dropdown always has a label to render.
const rawSuggestions = ref([])
const suggestions = computed(() => normaliseRows(rawSuggestions.value))
// Q14: search lifecycle so the empty panel can tell pending / failed / no-match
// apart. `lastQuery` lets the error state offer a retry of the same search.
const searching = ref(false)
const errored = ref(false)
let lastQuery = ""
let searchSequence = 0

function normaliseRows(rows) {
	return (rows || []).map((r) =>
		typeof r === "string"
			? { name: r, label: r }
			: { ...r, name: r.name, label: linkTitles.suggestionLabel(r) || r.name },
	)
}

async function runSearch(query) {
	const requestId = ++searchSequence
	lastQuery = query
	if (!props.searchHandler && !props.targetDoctype) {
		rawSuggestions.value = []
		searching.value = false
		errored.value = false
		return
	}
	searching.value = true
	errored.value = false
	try {
		const rows = props.searchHandler
			? await props.searchHandler(query)
			: await searchLink(props.targetDoctype, query, props.filters)
		if (requestId !== searchSequence) return
		linkTitles.remember(props.targetDoctype, rows)
		rawSuggestions.value = rows || []
	} catch (_) {
		if (requestId !== searchSequence) return
		rawSuggestions.value = []
		errored.value = true
	} finally {
		if (requestId === searchSequence) searching.value = false
	}
}

function onComplete(e) {
	runSearch(e.query || "")
}
function retrySearch() {
	runSearch(lastQuery)
}

// Selecting a suggestion stores its `name` (the Link value), not the object.
function onItemSelect(e) {
	const selected = e?.value
	const name = selected?.name ?? selected ?? ""
	if (selected && typeof selected === "object") linkTitles.remember(props.targetDoctype, [selected])
	hasUncommittedQuery.value = false
	inputValue.value = linkTitles.suggestionLabel(selected) || name
	emit("update:modelValue", name)
	emit("item-select", { value: name, originalEvent: e?.originalEvent })
}

// Free-text typing stays local. An object can briefly arrive when PrimeVue
// echoes a selected suggestion; `onItemSelect` performs the actual commit.
function onModelUpdate(v) {
	inputValue.value = v && typeof v === "object" ? v.name : (v ?? "")
	hasUncommittedQuery.value = String(inputValue.value ?? "") !== String(committedLabel.value ?? "")
}

function onFocus() {
	hasUncommittedQuery.value = false
}

// PrimeVue's raw `change` event also fires while text is being typed. That text
// is only an autocomplete query — it is not a confirmed Frappe Link value and
// must never trigger fetch_from/autofill/dependent API calls. Every consumer
// handles committed values through `item-select`; retain `change` only for an
// explicit clear so dependent fields can be reset.
function onChange(event) {
	const value = event?.value ?? event?.target?.value ?? ""
	if (value === "" || value == null) {
		inputValue.value = ""
		hasUncommittedQuery.value = false
		if (props.modelValue !== "" && props.modelValue != null) {
			emit("update:modelValue", "")
			emit("change", { value: "", originalEvent: event?.originalEvent || event })
		}
	}
}

// Free text is not a valid Link. If focus leaves without selecting a
// suggestion, restore the last committed value (or blank) instead of leaving a
// misleading name in the field.
function onBlur() {
	hasUncommittedQuery.value = false
	inputValue.value = committedLabel.value
}

const linkedPath = computed(() => {
	if (!props.modelValue || !props.targetDoctype) return ""
	if (hasUncommittedQuery.value) return ""
	if (props.routeResolver) {
		const route = props.routeResolver(props.targetDoctype, props.modelValue)
		return route ? `/web${route.startsWith("/") ? route : `/${route}`}` : ""
	}
	const reg = getRegistryByDoctype(props.targetDoctype)
	return reg
		? `/web/${reg.route}/${encodeURIComponent(props.modelValue)}`
		: `/app/${encodeURIComponent(props.targetDoctype.toLowerCase().replace(/ /g, "-"))}/${encodeURIComponent(props.modelValue)}`
})

// Open the linked record in a new tab so the current form/edit is retained.
// A Registered Experience route resolver takes precedence over generic routes.
function openLinked() {
	if (!linkedPath.value) return
	window.open(window.location.origin + linkedPath.value, "_blank", "noopener")
}

function focus() {
	const input = autoCompleteRef.value?.$el?.querySelector?.("input")
	if (!input || props.disabled) return false
	input.focus()
	input.select?.()
	return true
}

defineExpose({ focus })
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

/* Q14: empty-panel states. */
.lf-empty {
	padding: 8px 12px;
	font-size: 12.5px;
	color: var(--mgk-muted);
}
.lf-empty .pi {
	font-size: 11px;
	margin-right: 4px;
}
.lf-retry {
	color: var(--mgk-accent-700);
	font-weight: 600;
	cursor: pointer;
}
.lf-retry:hover {
	text-decoration: underline;
}
</style>
