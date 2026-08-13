<!--
  ColumnCustomizerModal — per-user list columns (#2). Lets the user pick which
  columns show + reorder them; persists to the `User Listview` doctype (base yrp)
  via save_user_listview / reset_user_listview. Sort + saved filters are deferred.
-->
<template>
	<Dialog
		:visible="visible"
		modal
		header="Customize Columns"
		:style="{ width: '460px' }"
		@update:visible="$emit('update:visible', $event)"
	>
		<p class="cc-hint">Tick the columns to show; drag the handle to reorder them.</p>
		<div class="cc-list">
			<template v-for="(col, i) in localCols" :key="col.fieldname">
				<div v-if="i === 0 || localCols[i - 1].enabled !== col.enabled" class="cc-group-label">
					{{ col.enabled ? "Shown columns" : "Available columns" }}
				</div>
				<div
					class="cc-row"
					:class="{
						'is-dragging': draggingField === col.fieldname,
						'is-drag-before': dragOverField === col.fieldname && dragPlacement === 'before',
						'is-drag-after': dragOverField === col.fieldname && dragPlacement === 'after',
					}"
					:data-fieldname="col.fieldname"
					@dragover.prevent="dragOver($event, col)"
					@drop.prevent="dropOn($event, col)"
				>
					<button
						class="cc-drag-handle"
						type="button"
						draggable="true"
						:aria-label="`Drag ${col.label} to reorder`"
						:title="`Drag ${col.label} to reorder`"
						@dragstart="startDrag($event, col)"
						@dragend="finishDrag"
					>
						<i class="pi pi-bars" aria-hidden="true" />
					</button>
					<Checkbox
						:model-value="col.enabled"
						:binary="true"
						:inputId="'cc-' + col.fieldname"
						@update:model-value="setEnabled(i, $event)"
					/>
					<label :for="'cc-' + col.fieldname" class="cc-label">{{ col.label }}</label>
					<span class="cc-type">{{ col.fieldtype }}</span>
					<div class="cc-move">
						<Button
							icon="pi pi-chevron-up"
							text
							rounded
							size="small"
							:disabled="!canMove(i, -1)"
							@click="move(i, -1)"
						/>
						<Button
							icon="pi pi-chevron-down"
							text
							rounded
							size="small"
							:disabled="!canMove(i, 1)"
							@click="move(i, 1)"
						/>
					</div>
				</div>
			</template>
			<div v-if="!localCols.length" class="cc-empty">No customizable columns.</div>
		</div>
		<template #footer>
			<Button
				label="Reset to Default"
				severity="secondary"
				outlined
				size="small"
				:loading="saving"
				@click="resetColumns"
			/>
			<Button label="Save" icon="pi pi-check" size="small" :loading="saving" @click="saveColumns" />
		</template>
	</Dialog>
</template>

<script setup>
import { ref, watch } from "vue"
import Dialog from "primevue/dialog"
import Button from "primevue/button"
import Checkbox from "primevue/checkbox"
import { callMethod } from "@/api/client"
import { useAppToast } from "@/composables/useToast"

const props = defineProps({
	visible: { type: Boolean, default: false },
	doctype: { type: String, required: true },
	// [{ fieldname, label, fieldtype, enabled }] — every eligible field, ordered.
	columns: { type: Array, default: () => [] },
})
const emit = defineEmits(["update:visible", "saved"])
const toast = useAppToast()

const localCols = ref([])
const saving = ref(false)
const draggingField = ref("")
const dragOverField = ref("")
const dragPlacement = ref("before")

// Rebuild the editable copy each time the modal opens.
watch(
	() => props.visible,
	(open) => {
		if (open) {
			const columns = props.columns.map((c) => ({
				fieldname: c.fieldname,
				label: c.label,
				fieldtype: c.fieldtype,
				enabled: !!c.enabled,
			}))
			localCols.value = [
				...columns.filter((column) => column.enabled),
				...columns.filter((column) => !column.enabled),
			]
		}
	},
)

function setEnabled(i, enabled) {
	const [column] = localCols.value.splice(i, 1)
	if (!column) return
	column.enabled = !!enabled
	const enabledCount = localCols.value.filter((item) => item.enabled).length
	// Newly selected fields join the end of the visible group. Deselected fields
	// move to the start of the available group, keeping the two groups obvious.
	localCols.value.splice(enabledCount, 0, column)
}

function canMove(i, dir) {
	const target = localCols.value[i + dir]
	return !!target && target.enabled === localCols.value[i]?.enabled
}

function move(i, dir) {
	const j = i + dir
	if (!canMove(i, dir)) return
	const arr = localCols.value
	const [item] = arr.splice(i, 1)
	arr.splice(j, 0, item)
}

function startDrag(event, column) {
	draggingField.value = column.fieldname
	dragOverField.value = ""
	event.dataTransfer.effectAllowed = "move"
	event.dataTransfer.setData("text/plain", column.fieldname)
}

function dragOver(event, target) {
	const source = localCols.value.find((column) => column.fieldname === draggingField.value)
	if (!source || source.fieldname === target.fieldname || source.enabled !== target.enabled) {
		event.dataTransfer.dropEffect = "none"
		dragOverField.value = ""
		return
	}
	const bounds = event.currentTarget.getBoundingClientRect()
	dragOverField.value = target.fieldname
	dragPlacement.value = event.clientY < bounds.top + bounds.height / 2 ? "before" : "after"
	event.dataTransfer.dropEffect = "move"
}

function dropOn(event, target) {
	const sourceIndex = localCols.value.findIndex((column) => column.fieldname === draggingField.value)
	const targetIndex = localCols.value.findIndex((column) => column.fieldname === target.fieldname)
	if (sourceIndex < 0 || targetIndex < 0) return finishDrag()
	const source = localCols.value[sourceIndex]
	if (source.fieldname === target.fieldname || source.enabled !== target.enabled) return finishDrag()

	const [column] = localCols.value.splice(sourceIndex, 1)
	const adjustedTarget = localCols.value.findIndex((item) => item.fieldname === target.fieldname)
	const insertionIndex = adjustedTarget + (dragPlacement.value === "after" ? 1 : 0)
	localCols.value.splice(insertionIndex, 0, column)
	finishDrag()
}

function finishDrag() {
	draggingField.value = ""
	dragOverField.value = ""
	dragPlacement.value = "before"
}

async function saveColumns() {
	if (!props.doctype) return
	saving.value = true
	try {
		const columns = localCols.value.map((c) => ({
			fieldname: c.fieldname,
			enabled: c.enabled ? 1 : 0,
		}))
		await callMethod("yrp.yrp.doctype.user_listview.user_listview.save_user_listview", {
			doctype_name: props.doctype,
			columns: JSON.stringify(columns),
		})
		toast.success("Columns saved", "Your column layout was updated.")
		emit("update:visible", false)
		emit("saved")
	} catch (e) {
		toast.error("Save failed", e.message)
	} finally {
		saving.value = false
	}
}

async function resetColumns() {
	if (!props.doctype) return
	saving.value = true
	try {
		await callMethod("yrp.yrp.doctype.user_listview.user_listview.reset_user_listview", {
			doctype_name: props.doctype,
		})
		toast.success("Columns reset", "Reverted to the default columns.")
		emit("update:visible", false)
		emit("saved")
	} catch (e) {
		toast.error("Reset failed", e.message)
	} finally {
		saving.value = false
	}
}
</script>

<style scoped>
.cc-hint {
	font-size: 12px;
	color: var(--mgk-muted);
	margin: 0 0 10px;
}
.cc-list {
	display: flex;
	flex-direction: column;
	gap: 2px;
	max-height: 420px;
	overflow-y: auto;
}
.cc-group-label {
	position: sticky;
	top: 0;
	z-index: 1;
	padding: 8px 8px 5px;
	background: var(--p-dialog-background, #fff);
	color: var(--mgk-muted);
	font-size: 10.5px;
	font-weight: 700;
	letter-spacing: 0.06em;
	text-transform: uppercase;
}
.cc-row {
	position: relative;
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 6px 8px;
	border-radius: var(--radius-sm);
}
.cc-row:hover {
	background: var(--mgk-slate-50);
}
.cc-row.is-dragging {
	opacity: 0.45;
}
.cc-row.is-drag-before::before,
.cc-row.is-drag-after::after {
	position: absolute;
	left: 7px;
	right: 7px;
	height: 2px;
	border-radius: 2px;
	background: var(--mgk-accent);
	content: "";
}
.cc-row.is-drag-before::before {
	top: -2px;
}
.cc-row.is-drag-after::after {
	bottom: -2px;
}
.cc-drag-handle {
	display: inline-grid;
	flex: 0 0 24px;
	width: 24px;
	height: 28px;
	place-items: center;
	padding: 0;
	border: 0;
	background: transparent;
	color: var(--mgk-muted);
	cursor: grab;
}
.cc-drag-handle:hover,
.cc-drag-handle:focus-visible {
	color: var(--mgk-accent);
}
.cc-drag-handle:active {
	cursor: grabbing;
}
.cc-label {
	flex: 1;
	font-size: 13px;
	color: var(--mgk-ink);
	cursor: pointer;
}
.cc-type {
	font-size: 10.5px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	color: var(--mgk-muted);
	background: var(--mgk-slate-50);
	padding: 1px 6px;
	border-radius: 6px;
}
.cc-move {
	display: flex;
}
.cc-empty {
	padding: 16px;
	text-align: center;
	color: var(--mgk-muted);
	font-size: 13px;
}
</style>
