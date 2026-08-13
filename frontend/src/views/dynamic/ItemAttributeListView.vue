<!--
  ItemAttributeListView — clean chip-based card grid + inline editor.

  /web port of Desk apps/yrp/yrp/public/js/components/AttributeList.vue,
  re-skinned per user feedback 2026-05-29 and the MGK master UI 2026-08-10:
    • Values render as accent-tinted rounded chips (no bullet list, no
      dashed dividers).
    • Generic surfaces retain inline editing; MGK master view uses `popupEdit`
      so clicking one attribute opens a focused popup like the IPD experience.
    • Edit mode: chips become removable (× per chip) and an input + Add
      button creates new values; Save / Cancel at the bottom of the card.
    • Save flow uses one server endpoint. Item Production Detail supplies a
      dedicated endpoint/context so its private mapping is updated without
      touching the finished Item master mapping.
    • Strict harness rule: no /app/* link — restricted users must stay in
      /web (see conventions.md 2026-05-29).

  Data source: __onload.attr_list, populated by Item.onload server-side
  (Item._load_attribute_list). Each entry:
    { attr_name, attr_values: [{ attribute_value }, …], doctype,
      attr_values_link }   — attr_values_link is the mapping doc name.
-->
<template>
	<div class="item-attr-list" :class="{ 'dialog-mode': displayMode === 'dialog' }">
		<div v-if="loading" class="state-block sm">
			<i class="pi pi-spin pi-spinner" /> <span>Loading…</span>
		</div>
		<div v-else-if="!attrList.length" class="empty-inline">
			No attributes configured yet.
		</div>
		<div v-else class="attr-grid" :class="{ 'popup-edit': popupEdit }">
			<component
				v-for="(attr, idx) in attrList"
				:key="attr.attr_name"
				:is="popupEdit ? 'button' : 'div'"
				class="attr-card"
				:class="{ editing: editingIdx === idx, 'popup-card': popupEdit }"
				:type="popupEdit ? 'button' : undefined"
				:disabled="popupEdit && (!editable || !attr.attr_values_link)"
				:aria-label="popupEdit ? `Update ${attr.attr_name} values` : undefined"
				@click="popupEdit && openPopup(idx, attr)"
			>
				<div v-if="displayMode !== 'dialog'" class="attr-head">
					<span class="attr-title">{{ attr.attr_name }}</span>
					<Button
						v-if="!popupEdit && editable && editingIdx !== idx && attr.attr_values_link"
						icon="pi pi-pencil"
						text
						rounded
						size="small"
						class="attr-edit-btn"
						v-tooltip.top="'Edit values'"
						@click="enterEdit(idx, attr)"
					/>
					<i v-if="popupEdit && editable && attr.attr_values_link" class="pi pi-pencil popup-pencil" />
				</div>

				<!-- VIEW: chips -->
				<div v-if="popupEdit || editingIdx !== idx" class="chip-row">
					<span
						v-for="v in attr.attr_values || []"
						:key="v.attribute_value"
						class="attr-chip"
					>{{ v.attribute_value }}</span>
					<span v-if="!(attr.attr_values || []).length" class="empty-inline sm">
						No values
					</span>
				</div>

				<!-- EDIT: removable chips + add new -->
				<template v-else>
					<div class="chip-row editing">
						<span
							v-for="(v, i) in draftValues"
							:key="'d-' + i"
							class="attr-chip removable"
						>
							{{ v }}
							<button
								class="chip-x"
								type="button"
								v-tooltip.top="'Remove'"
								@click="removeAt(i)"
							>×</button>
						</span>
						<span v-if="!draftValues.length" class="empty-inline sm">
							No values — add one below.
						</span>
					</div>
					<div class="add-row">
						<AutoComplete
							ref="newValueInput"
							v-model="newValue"
							:suggestions="newValueSuggestions"
							@complete="onNewValueComplete(attr, $event)"
							@item-select="addValue"
							@keydown.enter="addValue"
							:placeholder="displayMode === 'dialog' ? `Add another ${attr.attr_name} value…` : 'Pick or type new value…'"
							dropdown
							completeOnFocus
							class="add-input"
							fluid
						/>
						<Button
							:label="displayMode === 'dialog' ? 'Add value' : 'Add'"
							icon="pi pi-plus"
							size="small"
							severity="secondary"
							outlined
							:disabled="!String(newValue || '').trim()"
							@click="addValue"
						/>
					</div>
					<div class="edit-actions">
						<Button
							label="Cancel"
							icon="pi pi-times"
							size="small"
							severity="secondary"
							outlined
							:disabled="saving"
							@click="cancelEdit"
						/>
						<Button
							label="Save"
							icon="pi pi-check"
							size="small"
							:loading="saving"
							@click="onSave(attr)"
						/>
					</div>
				</template>
			</component>
		</div>

		<Dialog
			v-model:visible="popupOpen"
			modal
			:header="activePopupAttribute ? `Update ${activePopupAttribute.attr_name} values` : 'Update attribute values'"
			class="attribute-values-dialog"
			:style="{ width: 'min(560px, calc(100vw - 24px))' }"
			@hide="cancelPopupEdit"
		>
			<div v-if="activePopupAttribute" class="popup-editor">
				<div class="popup-context">
					<div><small>Item</small><strong>{{ localizedItemName }}</strong></div>
					<div><small>Attribute</small><strong>{{ activePopupAttribute.attr_name }}</strong></div>
				</div>

				<div class="popup-values">
					<span
						v-for="(value, index) in draftValues"
						:key="`${value}-${index}`"
						class="attr-chip removable"
					>
						{{ value }}
						<button class="chip-x" type="button" v-tooltip.top="'Remove'" @click="removeAt(index)">×</button>
					</span>
					<span v-if="!draftValues.length" class="empty-inline sm">No values — add one below.</span>
				</div>

				<div class="add-row popup-add-row">
					<AutoComplete
						ref="newValueInput"
						v-model="newValue"
						:suggestions="newValueSuggestions"
						@complete="onNewValueComplete(activePopupAttribute, $event)"
						@item-select="addValue"
						@keydown.enter="addValue"
						:placeholder="`Add another ${activePopupAttribute.attr_name} value…`"
						dropdown
						completeOnFocus
						class="add-input"
						fluid
					/>
					<Button
						label="Add value"
						icon="pi pi-plus"
						size="small"
						severity="secondary"
						outlined
						:disabled="!String(newValue || '').trim()"
						@click="addValue"
					/>
				</div>
			</div>

			<template #footer>
				<Button label="Cancel" icon="pi pi-times" size="small" severity="secondary" outlined :disabled="saving" @click="closePopup" />
				<Button label="Save values" icon="pi pi-check" size="small" :loading="saving" :disabled="!activePopupAttribute" @click="onSave(activePopupAttribute)" />
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, ref, onMounted, watch, nextTick } from "vue"
import Button from "primevue/button"
import InputText from "primevue/inputtext"
import AutoComplete from "primevue/autocomplete"
import Dialog from "primevue/dialog"
import Tooltip from "primevue/tooltip"
import { callMethod, getDocWithOnload, searchLink } from "@/api/client"
import { useAppToast } from "@/composables/useToast"
import { useLinkTitles } from "@/composables/useLinkTitles"

const vTooltip = Tooltip

const props = defineProps({
	itemName: { type: String, required: true },
	// Host DocType whose __onload.attr_list we read and whose mappings we write.
	// "Item" by default; "Item Master Template" shares the identical attr_list
	// onload contract, so the same editor serves both.
	doctype: { type: String, default: "Item" },
	editable: { type: Boolean, default: true },
	attributeName: { type: String, default: "" },
	autoEdit: { type: Boolean, default: false },
	displayMode: { type: String, default: "default" },
	popupEdit: { type: Boolean, default: false },
	saveMethod: {
		type: String,
		default: "mgk_clothing_yrp.mgk_clothing_yrp.api.item_attribute.update_mapping_values",
	},
	saveContext: { type: Object, default: () => ({}) },
})
const emit = defineEmits(["updated", "cancel"])

const toast = useAppToast()
const linkTitles = useLinkTitles()
const localizedItemName = computed(() =>
	props.doctype === "Item"
		? (linkTitles.titleFor("Item", props.itemName) || props.itemName)
		: props.itemName,
)
const loading = ref(false)
const saving = ref(false)
const attrList = ref([])

// ── inline edit state (one card at a time) ──
const editingIdx = ref(-1)
const draftValues = ref([])
const newValue = ref("")
// AutoComplete suggestion buffer for the "New value" picker.
const newValueSuggestions = ref([])
const popupOpen = ref(false)
const activePopupAttribute = ref(null)
const newValueInput = ref(null)

// Filtered list of existing Item Attribute Values for this attribute, minus
// the ones already in the draft list. Free-text entry is still allowed —
// the AutoComplete leaves v-model = typed string when nothing matches.
async function onNewValueComplete(attr, e) {
	const q = e?.query || ""
	try {
		const rows = await searchLink("Item Attribute Value", q, {
			attribute_name: attr.attr_name,
		})
		newValueSuggestions.value = (rows || [])
			.map((r) => r.name)
			.filter((n) => !draftValues.value.includes(n))
	} catch (_) {
		newValueSuggestions.value = []
	}
}

onMounted(load)
watch(() => [props.itemName, props.doctype, props.attributeName], load)

async function load() {
	if (!props.itemName) return
	loading.value = true
	editingIdx.value = -1
	draftValues.value = []
	try {
		const doc = await getDocWithOnload(props.doctype, props.itemName)
		const arr = Array.isArray(doc?.__onload?.attr_list) ? doc.__onload.attr_list : []
		attrList.value = props.attributeName
			? arr.filter((row) => row.attr_name === props.attributeName)
			: arr
		if (props.autoEdit && props.editable && attrList.value[0]?.attr_values_link) {
			await nextTick()
			enterEdit(0, attrList.value[0])
		}
	} catch (e) {
		toast.error("Could not load attributes", e.message)
		attrList.value = []
	} finally {
		loading.value = false
	}
}

async function openPopup(idx, attr) {
	if (!props.popupEdit || !props.editable || !attr?.attr_values_link) return
	activePopupAttribute.value = attr
	enterEdit(idx, attr)
	popupOpen.value = true
	await focusNewValue()
}

function closePopup() {
	popupOpen.value = false
	cancelEdit()
}

function cancelPopupEdit() {
	if (!props.popupEdit) return
	activePopupAttribute.value = null
	editingIdx.value = -1
	draftValues.value = []
	newValue.value = ""
}

async function enterEdit(idx, attr) {
	editingIdx.value = idx
	draftValues.value = (attr.attr_values || []).map((v) => v.attribute_value)
	newValue.value = ""
	await focusNewValue()
}

function cancelEdit() {
	editingIdx.value = -1
	draftValues.value = []
	newValue.value = ""
	if (props.autoEdit) emit("cancel")
}

async function addValue() {
	// `newValue` may be a string (typed) or — after AutoComplete @item-select
	// — a plain string of the picked name (PrimeVue auto-sets v-model). Coerce
	// defensively in case a future suggestions array changes shape to objects.
	const raw = newValue.value
	const v = (typeof raw === "string" ? raw : raw?.name || "").trim()
	if (!v) return
	if (draftValues.value.includes(v)) {
		toast.warn("Duplicate", `"${v}" already in the list.`)
		newValue.value = ""
		await focusNewValue()
		return
	}
	draftValues.value.push(v)
	newValue.value = ""
	newValueSuggestions.value = []
	await focusNewValue()
}

async function focusNewValue() {
	await nextTick()
	const component = Array.isArray(newValueInput.value) ? newValueInput.value[0] : newValueInput.value
	const input = component?.$el?.querySelector?.("input")
	input?.focus?.()
}

function removeAt(i) {
	draftValues.value.splice(i, 1)
}

async function onSave(attr) {
	if (!attr.attr_values_link) {
		toast.error("No mapping doc", "Cannot save — the attribute mapping is missing.")
		return
	}
	saving.value = true
	try {
		const savedValues = [...draftValues.value]
		// Single server-side call: creates missing Item Attribute Value docs +
		// rewrites the mapping's child rows in one transaction. Avoids the
		// timestamp-race a multi-call frontend flow used to hit (each new
		// Attribute Value insert was bumping the parent's `modified` between
		// the last insert and the parent save).
		await callMethod(props.saveMethod, {
			...props.saveContext,
			mapping: attr.attr_values_link,
			attribute_name: attr.attr_name,
			values: draftValues.value,
		})
		toast.success("Saved", `${attr.attr_name} values updated`)
		await load()
		if (props.popupEdit) popupOpen.value = false
		emit("updated", {
			attribute: attr.attr_name,
			values: savedValues,
		})
	} catch (e) {
		toast.error("Save failed", e.message)
	} finally {
		saving.value = false
	}
}

defineExpose({ reload: load })
</script>

<style scoped>
.item-attr-list {
	display: flex;
	flex-direction: column;
	gap: 8px;
}
.attr-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
	gap: 12px;
}
.attr-card {
	background: var(--mgk-card);
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius);
	padding: 12px 14px;
	display: flex;
	flex-direction: column;
	gap: 10px;
	min-width: 0;
	transition: border-color 0.12s, box-shadow 0.12s;
}
.attr-card:hover {
	border-color: var(--mgk-accent-50);
}
.attr-card.editing {
	border-color: var(--mgk-accent);
	box-shadow: 0 0 0 3px var(--mgk-accent-50);
}
.attr-head {
	display: flex;
	align-items: center;
	gap: 8px;
}
.attr-title {
	font-size: 11.5px;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: var(--mgk-muted);
	font-weight: 600;
	flex: 1;
	min-width: 0;
}
.attr-edit-btn {
	flex-shrink: 0;
	color: var(--mgk-muted-2);
}
.attr-edit-btn:hover {
	color: var(--mgk-accent-700);
}
.popup-edit .attr-card.popup-card {
	position: relative;
	width: 100%;
	min-height: 104px;
	padding: 14px 42px 14px 15px;
	background: #fff;
	color: inherit;
	font: inherit;
	text-align: left;
	cursor: pointer;
}
.popup-edit .attr-card.popup-card:hover {
	border-color: #c8897e;
	box-shadow: 0 5px 14px rgba(135, 53, 41, .08);
}
.popup-edit .attr-card.popup-card:focus-visible {
	border-color: #b94d3d;
	outline: 3px solid rgba(185, 77, 61, .14);
}
.popup-edit .attr-card.popup-card:disabled {
	opacity: 1;
	cursor: default;
}
.popup-edit .popup-pencil {
	position: absolute;
	top: 16px;
	right: 16px;
	color: #9d4638;
	font-size: 12px;
}
.popup-edit .attr-chip {
	background: #eef6ff;
	color: #285d9b;
	font-weight: 700;
}
.popup-editor {
	display: grid;
	gap: 16px;
}
.popup-context {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	overflow: hidden;
	border: 1px solid #e5dccf;
	border-radius: 12px;
	background: #fbf7ef;
}
.popup-context > div {
	display: grid;
	gap: 4px;
	padding: 13px 14px;
}
.popup-context > div + div {
	border-left: 1px solid #e5dccf;
}
.popup-context small {
	color: #667085;
	font-size: 10px;
	font-weight: 750;
	letter-spacing: .055em;
	text-transform: uppercase;
}
.popup-context strong {
	color: #1d2739;
	font-size: 13px;
}
.popup-values {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 7px;
	min-height: 54px;
	padding: 11px 12px;
	border: 1px solid var(--mgk-line);
	border-radius: 11px;
	background: #f8fafc;
}
.popup-values .attr-chip {
	padding: 6px 7px 6px 11px;
	font-size: 13px;
}
.popup-add-row {
	align-items: stretch;
}
.popup-add-row :deep(.p-autocomplete-input),
.popup-add-row :deep(.p-button) {
	min-height: 42px;
}

/* Chips */
.chip-row {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	align-items: center;
}
.attr-chip {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	background: var(--mgk-accent-50);
	color: var(--mgk-accent-700);
	border-radius: 999px;
	font-size: 12.5px;
	font-weight: 500;
	padding: 4px 12px;
	line-height: 1.3;
	white-space: nowrap;
}
.attr-chip.removable {
	padding-right: 6px;
}
.chip-x {
	background: transparent;
	border: 0;
	color: var(--mgk-accent-700);
	cursor: pointer;
	font-size: 15px;
	line-height: 1;
	padding: 0 4px;
	border-radius: 999px;
	opacity: 0.7;
}
.chip-x:hover {
	opacity: 1;
	background: var(--mgk-accent);
	color: white;
}

/* Edit add-row */
.add-row {
	display: flex;
	gap: 6px;
	align-items: center;
}
.add-input {
	flex: 1;
	min-width: 0;
}

/* Edit actions */
.edit-actions {
	display: flex;
	gap: 8px;
	justify-content: flex-end;
}
.item-attr-list.dialog-mode {
	gap: 14px;
}
.dialog-mode .attr-grid {
	grid-template-columns: minmax(0, 1fr);
}
.dialog-mode .attr-card,
.dialog-mode .attr-card.editing {
	gap: 16px;
	width: 100%;
	padding: 0;
	border: 0;
	border-radius: 0;
	background: transparent;
	box-shadow: none;
}
.dialog-mode .chip-row {
	min-height: 42px;
	padding: 11px 12px;
	border: 1px solid var(--mgk-line);
	border-radius: 11px;
	background: #f8fafc;
}
.dialog-mode .attr-chip {
	padding: 6px 10px 6px 12px;
	font-size: 13px;
}
.dialog-mode .add-row {
	align-items: stretch;
}
.dialog-mode .add-row :deep(.p-autocomplete-input) {
	min-height: 42px;
}
.dialog-mode .add-row :deep(.p-button) {
	min-height: 42px;
}
.dialog-mode .edit-actions {
	margin-top: 2px;
	padding-top: 14px;
	border-top: 1px solid var(--mgk-line);
}
.dialog-mode .edit-actions :deep(.p-button) {
	min-width: 106px;
}

@media (max-width: 520px) {
	.popup-context {
		grid-template-columns: 1fr;
	}
	.popup-context > div + div {
		border-top: 1px solid #e5dccf;
		border-left: 0;
	}
	.popup-add-row {
		flex-direction: column;
	}
	.popup-add-row :deep(.p-button) {
		width: 100%;
	}
	.dialog-mode .add-row {
		align-items: stretch;
		flex-direction: column;
	}
	.dialog-mode .add-row :deep(.p-button) {
		width: 100%;
	}
	.dialog-mode .edit-actions :deep(.p-button) {
		flex: 1;
	}
}

.state-block.sm,
.empty-inline,
.empty-inline.sm {
	color: var(--mgk-muted);
	font-size: 13px;
	padding: 6px 0;
}
.empty-inline.sm {
	padding: 2px 0;
	font-size: 12px;
}
</style>
