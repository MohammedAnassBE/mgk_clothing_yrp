<template>
	<div class="ipd-yarn-flow">
		<div v-if="finishedItem" class="finished-context">
			<div>
				<small>Finished item setup</small>
				<strong>{{ localizedItem(finishedItem) }}</strong>
			</div>
			<div v-if="finishedAttributeCards.length" class="finished-attributes">
				<button
					v-for="card in finishedAttributeCards"
					:key="card.attribute"
					type="button"
					:class="{ editable: canEditAttributes }"
					:disabled="!canEditAttributes"
					@click="requestAttributeEdit(card.attribute)"
				>
					<b>{{ card.attribute }}</b>
					<small>{{ card.values.join(", ") || "No values" }}</small>
					<i v-if="canEditAttributes" class="pi pi-pencil" />
				</button>
			</div>
		</div>

		<Message v-if="catalogError" severity="error" :closable="false">{{ catalogError }}</Message>
		<div v-else-if="catalogLoading" class="flow-loading"><i class="pi pi-spin pi-spinner" /> Loading yarn Items and processes…</div>

		<div v-if="!steps.length && !draft && !catalogLoading" class="flow-empty">
			<span><i class="pi pi-sitemap" /></span>
			<div><strong>No yarn process added yet</strong><small>Add the first process that this finished Item needs.</small></div>
			<Button v-if="!readonly" ref="addProcessButtonEl" label="Add first process" icon="pi pi-plus" size="small" @click="startAdd" />
		</div>

		<div v-else class="flow-steps">
			<template v-for="(step, index) in steps" :key="stepKey(step, index)">
				<article class="flow-card">
					<header>
						<span class="step-number">{{ index + 1 }}</span>
						<div class="step-title">
							<strong>{{ step.process_name }}</strong>
							<small>{{ processShapeLabel(step) }}</small>
						</div>
						<div v-if="!readonly" class="step-actions">
							<Button icon="pi pi-pencil" text rounded size="small" aria-label="Edit process" @click="startEdit(index)" />
							<Button icon="pi pi-trash" text rounded size="small" severity="danger" aria-label="Remove process" @click="removeStep(index)" />
						</div>
					</header>
					<div class="item-route">
						<div><small>Input yarn</small><strong>{{ localizedItem(step.input_item) }}</strong><span>{{ itemUom(step.input_item) || "UOM not set" }}</span></div>
						<i class="pi pi-arrow-right" />
						<div><small>Output yarn</small><strong>{{ localizedItem(step.output_item) }}</strong><span>1 input → {{ formatRatio(step.quantity_ratio) }} output</span></div>
					</div>
					<div v-if="isColourChange(step)" class="colour-routes">
						<span v-for="(route, routeIndex) in step.routes" :key="route.name || routeIndex">
							{{ route.from_colour || "—" }} <i class="pi pi-arrow-right" /> {{ route.to_colour || "—" }}
						</span>
					</div>
				</article>
				<div v-if="index < steps.length - 1" class="flow-connector"><span>↓</span><small>output becomes next input</small></div>
			</template>
		</div>

		<div v-if="!readonly && steps.length && !draft" class="add-process-row">
			<Button ref="addProcessButtonEl" label="Add next process" icon="pi pi-plus" size="small" severity="secondary" outlined @click="startAdd" />
		</div>

		<section v-if="draft" ref="processEditorEl" class="process-editor">
			<header>
				<div><small>{{ editingIndex === null ? "New step" : `Edit step ${editingIndex + 1}` }}</small><strong>Define the yarn process</strong></div>
				<span>{{ draftShapeLabel }}</span>
			</header>
			<div class="editor-grid">
				<label data-focus-key="process">
					<span>Process *</span>
					<Select v-model="draft.process_name" :options="processOptions" optionLabel="name" optionValue="name" filter placeholder="Select process" fluid @change="onProcessChanged" />
				</label>
				<label data-focus-key="input-item">
					<span>Input Yarn Item *</span>
					<Select v-model="draft.input_item" :options="yarnItemNames" filter placeholder="Select input yarn" fluid :disabled="editingIndex !== 0 && steps.length > 0" @change="onInputChanged" />
					<small v-if="editingIndex !== 0 && steps.length > 0">Filled from the previous process output.</small>
				</label>
				<label data-focus-key="output-item">
					<span>Output Yarn Item *</span>
					<Select v-model="draft.output_item" :options="outputItemNames" filter placeholder="Select output yarn" fluid :disabled="!draftConversion" />
					<small v-if="draftChangesColour">Colour-changing Processes keep the same Yarn Item.</small>
					<small v-else-if="draftPassThrough">This Process carries the Yarn Item and all attributes unchanged.</small>
				</label>
				<label data-focus-key="ratio">
					<span>Output per 1 input *</span>
					<InputNumber v-model="draft.quantity_ratio" :min="0.000001" :maxFractionDigits="6" fluid />
					<small>Normally 1 input → 1 output.</small>
				</label>
			</div>

			<div v-if="draft.process_name && draftChangesColour" class="transition-editor">
				<header><div><strong>Colour transitions</strong><small>Choose one source Colour and one or more output Colours.</small></div><Button label="Add source colour" icon="pi pi-plus" size="small" text @click="addColourRoute" /></header>
				<div v-for="(route, index) in draft.routes" :key="`${route.from_colour}-${index}`" class="transition-row">
					<span :data-route-source="index"><Select v-model="route.from_colour" :options="draftColours" filter placeholder="From colour" fluid @change="onFromColourChanged(route)" /></span>
					<i class="pi pi-arrow-right" />
					<span :data-route-output="index"><MultiSelect v-model="route.to_colours" :options="outputColourOptions(route)" filter display="chip" :maxSelectedLabels="3" placeholder="Select output colours" fluid /></span>
					<Button v-if="draft.routes.length > 1" icon="pi pi-times" text rounded severity="danger" aria-label="Remove transition" @click="draft.routes.splice(index, 1)" />
				</div>
				<div v-if="draft.input_item && !draftColours.length" class="inline-warning"><i class="pi pi-exclamation-triangle" /> No Colour values exist in the Item Attribute master.</div>
			</div>
			<Message v-if="draftUnsupportedAttributes.length" severity="warn" :closable="false">
				Process {{ draft.process_name }} defines unsupported Value Change Attributes:
				{{ draftUnsupportedAttributes.join(", ") }}. This yarn route supports Colour as its one changed attribute.
			</Message>

			<Message v-if="draftError" severity="warn" :closable="false">{{ draftError }}</Message>
			<footer><Button label="Cancel" icon="pi pi-times" size="small" severity="secondary" outlined @click="cancelDraft" /><Button label="Keep this process" icon="pi pi-check" size="small" @click="saveDraft" /></footer>
		</section>
	</div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue"
import Button from "primevue/button"
import InputNumber from "primevue/inputnumber"
import Message from "primevue/message"
import MultiSelect from "primevue/multiselect"
import Select from "primevue/select"
import { callMethod, getDocWithOnload } from "@/api/client"
import { useLinkTitles } from "@/composables/useLinkTitles"
import { focusFirstControl } from "@/utils/focusControl"

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	finishedItem: { type: String, default: "" },
	finishedAttributes: { type: Array, default: () => [] },
	productionDetail: { type: String, default: "" },
	finishedAttributeValues: { type: Object, default: () => ({}) },
	readonly: { type: Boolean, default: false },
	canEditAttributes: { type: Boolean, default: false },
})
const emit = defineEmits(["update:modelValue", "summary", "change", "edit-attribute"])
const linkTitles = useLinkTitles()

const steps = ref([])
const processes = ref([])
const yarnItems = ref([])
const catalogLoading = ref(false)
const catalogError = ref("")
const draft = ref(null)
const editingIndex = ref(null)
const draftError = ref("")
const finishedValues = ref({})
const processEditorEl = ref(null)
const addProcessButtonEl = ref(null)

function localizedItem(value) {
	return linkTitles.titleFor("Item", value) || value || "—"
}

const processMap = computed(() => Object.fromEntries(processes.value.map((row) => [row.name, row])))
const yarnItemMap = computed(() => Object.fromEntries(yarnItems.value.map((row) => [row.name, row])))
const yarnItemNames = computed(() => yarnItems.value.map((row) => row.name))
const processOptions = computed(() => {
	const current = editingIndex.value == null ? "" : steps.value[editingIndex.value]?.process_name
	const used = new Set(steps.value.map((step) => step.process_name).filter((name) => name !== current))
	return processes.value.filter((row) => !used.has(row.name))
})
const draftConversion = computed(() => Boolean(processMap.value[draft.value?.process_name]?.is_item_conversion))
const draftChangedAttributes = computed(() => processChangeAttributes(draft.value?.process_name))
const draftChangesColour = computed(() => (
	!draftConversion.value && draftChangedAttributes.value.includes("Colour")
))
const draftUnsupportedAttributes = computed(() => (
	draftConversion.value && draftChangedAttributes.value.length
		? draftChangedAttributes.value
		: draftChangedAttributes.value.filter((attribute) => attribute !== "Colour")
))
const draftPassThrough = computed(() => (
	Boolean(draft.value?.process_name)
	&& !draftConversion.value
	&& !draftChangedAttributes.value.length
))
const draftShapeLabel = computed(() => {
	if (!draft.value?.process_name) return "Select process"
	if (draftConversion.value) return "Item conversion"
	if (draftChangesColour.value) return "Colour change"
	if (draftPassThrough.value) return "Pass-through"
	return "Unsupported attribute change"
})
const draftColours = computed(() => yarnItemMap.value[draft.value?.input_item]?.colours || [])
const outputItemNames = computed(() => {
	if (!draft.value?.input_item) return yarnItemNames.value
	if (!draftConversion.value) return [draft.value.input_item]
	const input = yarnItemMap.value[draft.value.input_item]
	if (!input) return yarnItemNames.value.filter((name) => name !== draft.value.input_item)
	return yarnItems.value
		.filter((row) => row.name !== input.name && compatibleItems(input, row))
		.map((row) => row.name)
})
const finishedAttributeCards = computed(() => (props.finishedAttributes || []).map((row) => ({
	attribute: row.attribute,
	values: finishedValues.value[row.attribute] || [],
})).filter((row) => row.attribute))

watch(() => props.modelValue, (rows) => {
	steps.value = groupRows(rows || [])
	emitSummary()
}, { immediate: true, deep: true })

watch(
	() => [props.finishedItem, props.productionDetail],
	loadFinishedValues,
	{ immediate: true },
)
watch(
	() => props.finishedAttributeValues,
	(values) => {
		if (values && Object.keys(values).length) {
			finishedValues.value = { ...values }
		}
	},
	{ deep: true },
)

onMounted(loadCatalog)

async function loadCatalog() {
	catalogLoading.value = true
	catalogError.value = ""
	try {
		const result = await callMethod("mgk_clothing_yrp.mgk_clothing_yrp.api.experiences.operations_workspace.item_production_detail.get_entry_context")
		processes.value = result?.processes || []
		yarnItems.value = result?.yarn_items || []
		emitSummary()
	} catch (error) {
		catalogError.value = error?.message || "Could not load yarn Items and processes."
	} finally {
		catalogLoading.value = false
	}
}

async function loadFinishedValues() {
	finishedValues.value = {}
	if (!props.finishedItem) return
	try {
		if (props.productionDetail) {
			const result = await getDocWithOnload(
				"Item Production Detail",
				props.productionDetail,
			)
			const rows = result?.__onload?.attr_list || []
			finishedValues.value = Object.fromEntries(rows.map((row) => [
				row.attr_name,
				(row.attr_values || []).map((value) => value.attribute_value),
			]))
		} else {
			finishedValues.value = await callMethod("yrp.yrp.doctype.item.item.get_attribute_values", { item: props.finishedItem }) || {}
		}
	} catch (_) {
		finishedValues.value = {}
	}
}

function groupRows(rows) {
	const groups = new Map()
	for (const [index, raw] of rows.entries()) {
		const sequence = Number(raw.sequence || ((index + 1) * 10))
		if (!groups.has(sequence)) {
			groups.set(sequence, {
				sequence,
				process_name: raw.process_name || "",
				input_item: raw.input_item || "",
				output_item: raw.output_item || "",
				quantity_ratio: Number(raw.quantity_ratio || 1),
				routes: [],
			})
		}
		groups.get(sequence).routes.push({ ...raw })
	}
	return [...groups.values()].sort((a, b) => a.sequence - b.sequence)
}

function compatibleItems(input, output) {
	if (!input || !output || input.uom !== output.uom) return false
	if (JSON.stringify(input.attributes || []) !== JSON.stringify(output.attributes || [])) return false
	return (input.attributes || []).every((attribute) => {
		const outputValues = new Set(output.value_options?.[attribute] || [])
		return (input.value_options?.[attribute] || []).some((value) => outputValues.has(value))
	})
}

function isConversion(step) {
	const process = processMap.value[step.process_name]
	return process ? Boolean(process.is_item_conversion) : step.input_item !== step.output_item
}

function processChangeAttributes(processName) {
	const values = processMap.value[processName]?.value_change_attributes
	return Array.isArray(values) ? values.filter(Boolean) : []
}

function isColourChange(step) {
	return !isConversion(step) && processChangeAttributes(step.process_name).includes("Colour")
}

function processShapeLabel(step) {
	const changedAttributes = processChangeAttributes(step.process_name)
	if (isConversion(step)) return changedAttributes.length ? "Unsupported combined change" : "Item conversion"
	if (isColourChange(step)) return "Colour change"
	if (!changedAttributes.length) return "Pass-through"
	return "Unsupported attribute change"
}

function stepKey(step, index) {
	return `${step.sequence}-${step.process_name}-${index}`
}

function itemUom(item) {
	return yarnItemMap.value[item]?.uom || ""
}

function formatRatio(value) {
	return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 6 }).format(Number(value || 1))
}

function requestAttributeEdit(attribute) {
	if (props.canEditAttributes) emit("edit-attribute", attribute)
}

function blankDraft() {
	const previous = steps.value[steps.value.length - 1]
	return {
		sequence: (steps.value.length + 1) * 10,
		process_name: "",
		input_item: previous?.output_item || "",
		output_item: "",
		quantity_ratio: 1,
		routes: [{ from_colour: "", to_colours: [], source_rows: {} }],
	}
}

async function startAdd() {
	draftError.value = ""
	editingIndex.value = null
	draft.value = blankDraft()
	await focusProcessField("process")
}

async function startEdit(index) {
	draftError.value = ""
	editingIndex.value = index
	const step = steps.value[index]
	draft.value = JSON.parse(JSON.stringify(step))
	if (isColourChange(step)) {
		draft.value.routes = groupColourRoutes(draft.value.routes)
	} else {
		const storedFields = { ...(draft.value.routes?.[0] || {}) }
		delete storedFields.to_colours
		delete storedFields.source_rows
		draft.value.routes = [{ ...storedFields, from_colour: "", to_colour: "" }]
	}
	await focusProcessField("process")
}

async function cancelDraft() {
	draft.value = null
	editingIndex.value = null
	draftError.value = ""
	await nextTick()
	addProcessButtonEl.value?.$el?.focus?.()
}

function onProcessChanged() {
	if (!draft.value) return
	if (draftConversion.value) {
		if (draft.value.output_item === draft.value.input_item) draft.value.output_item = ""
		const old = expandColourRoutes(draft.value.routes)[0] || {}
		draft.value.routes = [{ ...old, from_colour: "", to_colour: "" }]
	} else if (draftChangesColour.value) {
		draft.value.output_item = draft.value.input_item
		draft.value.routes = groupColourRoutes(draft.value.routes)
	} else {
		draft.value.output_item = draft.value.input_item
		const old = expandColourRoutes(draft.value.routes)[0] || draft.value.routes?.[0] || {}
		delete old.to_colours
		delete old.source_rows
		draft.value.routes = [{ ...old, from_colour: "", to_colour: "" }]
	}
}

function onInputChanged() {
	if (!draft.value) return
	if (draftConversion.value) return
	draft.value.output_item = draft.value.input_item
	if (!draftChangesColour.value) return
	for (const route of draft.value.routes || []) {
		if (!draftColours.value.includes(route.from_colour)) route.from_colour = ""
		route.to_colours = (route.to_colours || []).filter((value) => (
			draftColours.value.includes(value) && value !== route.from_colour
		))
	}
}

async function addColourRoute() {
	draft.value?.routes.push({ from_colour: "", to_colours: [], source_rows: {} })
	await focusFirstControl(processEditorEl, { selector: `[data-route-source="${draft.value.routes.length - 1}"]` })
}

function onFromColourChanged(route) {
	route.to_colours = (route.to_colours || []).filter(
		(value) => value !== route.from_colour,
	)
}

function outputColourOptions(route) {
	return draftColours.value.filter((value) => value !== route.from_colour)
}

function groupColourRoutes(routes) {
	const groups = new Map()
	for (const [index, route] of (routes || []).entries()) {
		const fromColour = route.from_colour || ""
		const key = fromColour || `__blank_${index}`
		if (!groups.has(key)) {
			groups.set(key, {
				from_colour: fromColour,
				to_colours: [],
				source_rows: {},
			})
		}
		const group = groups.get(key)
		const outputColours = Array.isArray(route.to_colours)
			? route.to_colours
			: (route.to_colour ? [route.to_colour] : [])
		for (const outputColour of outputColours) {
			if (!group.to_colours.includes(outputColour)) {
				group.to_colours.push(outputColour)
			}
			group.source_rows[outputColour] = route.source_rows?.[outputColour] || route
		}
	}
	return [...groups.values()].length
		? [...groups.values()]
		: [{ from_colour: "", to_colours: [], source_rows: {} }]
}

function expandColourRoutes(routes) {
	return (routes || []).flatMap((route) => {
		const outputColours = Array.isArray(route.to_colours)
			? route.to_colours
			: (route.to_colour ? [route.to_colour] : [])
		return outputColours.map((outputColour) => {
			const storedFields = { ...(route.source_rows?.[outputColour] || {}) }
			delete storedFields.to_colours
			delete storedFields.source_rows
			return {
				...storedFields,
				from_colour: route.from_colour,
				to_colour: outputColour,
			}
		})
	})
}

function validateDraft() {
	const row = draft.value
	if (!row?.process_name) return "Select the process."
	if (!row.input_item) return "Select the input Yarn Item."
	if (!row.output_item) return "Select the output Yarn Item."
	if (!(Number(row.quantity_ratio) > 0)) return "Output per input must be greater than zero."
	if (draftUnsupportedAttributes.value.length) {
		return `Process ${row.process_name} has unsupported Value Change Attributes: ${draftUnsupportedAttributes.value.join(", ")}.`
	}
	if (draftConversion.value) {
		if (row.input_item === row.output_item) return "An Item-conversion process needs a different output Yarn Item."
		if (!outputItemNames.value.includes(row.output_item)) return "Choose an output Yarn Item with matching UOM and attributes."
		return ""
	}
	if (draftPassThrough.value) {
		if (row.input_item !== row.output_item) return "A pass-through Process must keep the same Yarn Item."
		return ""
	}
	if (!draftColours.value.length) return "Add Colour values in the Item Attribute master before adding Dyeing."
	if (!row.routes?.length) return "Add at least one colour transition."
	const keys = []
	const sourceColours = new Set()
	for (const route of row.routes) {
		if (!route.from_colour) return "Select the source Colour for every transition."
		if (!(route.to_colours || []).length) return "Select at least one output Colour for every source Colour."
		if (sourceColours.has(route.from_colour)) return "Use one row per source Colour. Select all its outputs in the same row."
		sourceColours.add(route.from_colour)
		for (const outputColour of route.to_colours) {
			if (route.from_colour === outputColour) return "Source and output Colours must be different."
			keys.push(`${route.from_colour}\u0000${outputColour}`)
		}
	}
	if (new Set(keys).size !== keys.length) return "Remove the duplicate colour transition."
	return ""
}

async function saveDraft() {
	draftError.value = validateDraft()
	if (draftError.value) {
		await focusInvalidProcessField()
		return
	}
	const nextStep = JSON.parse(JSON.stringify(draft.value))
	const oldOutput = editingIndex.value == null ? "" : steps.value[editingIndex.value]?.output_item
	if (!draftChangesColour.value) {
		const storedFields = { ...(nextStep.routes?.[0] || {}) }
		delete storedFields.to_colours
		delete storedFields.source_rows
		nextStep.routes = [{ ...storedFields, from_colour: "", to_colour: "" }]
	} else {
		nextStep.routes = expandColourRoutes(nextStep.routes)
	}
	if (editingIndex.value == null) steps.value.push(nextStep)
	else steps.value.splice(editingIndex.value, 1, nextStep)
	steps.value.sort((a, b) => a.sequence - b.sequence)
	if (editingIndex.value != null) {
		const following = steps.value[editingIndex.value + 1]
		if (following && (!oldOutput || following.input_item === oldOutput)) {
			following.input_item = nextStep.output_item
			if (!isConversion(following)) following.output_item = nextStep.output_item
		}
	}
	resequence()
	emitRows()
	await cancelDraft()
}

function focusProcessField(key) {
	return focusFirstControl(processEditorEl, { selector: `[data-focus-key="${key}"]` })
}

async function focusAddAction() {
	await nextTick()
	const button = addProcessButtonEl.value?.$el || addProcessButtonEl.value
	button?.focus?.()
	return typeof document !== "undefined" && document.activeElement === button
}

function focusInvalidProcessField() {
	const row = draft.value
	if (!row?.process_name) return focusProcessField("process")
	if (!row.input_item) return focusProcessField("input-item")
	if (!row.output_item) return focusProcessField("output-item")
	if (!(Number(row.quantity_ratio) > 0)) return focusProcessField("ratio")
	if (draftUnsupportedAttributes.value.length) return focusProcessField("process")
	const badSource = row.routes?.findIndex((route) => !route.from_colour) ?? -1
	if (badSource >= 0) return focusFirstControl(processEditorEl, { selector: `[data-route-source="${badSource}"]` })
	const badOutput = row.routes?.findIndex((route) => !(route.to_colours || []).length) ?? -1
	if (badOutput >= 0) return focusFirstControl(processEditorEl, { selector: `[data-route-output="${badOutput}"]` })
	return focusProcessField("process")
}

function removeStep(index) {
	steps.value.splice(index, 1)
	rechainFrom(Math.max(0, index - 1))
	resequence()
	emitRows()
}

function rechainFrom(index) {
	for (let i = Math.max(1, index + 1); i < steps.value.length; i++) {
		steps.value[i].input_item = steps.value[i - 1].output_item
		if (!isConversion(steps.value[i])) steps.value[i].output_item = steps.value[i].input_item
	}
}

function resequence() {
	steps.value.forEach((step, index) => { step.sequence = (index + 1) * 10 })
}

function emitRows() {
	const rows = []
	for (const step of steps.value) {
		const colourChange = isColourChange(step)
		const routes = colourChange ? step.routes : [step.routes?.[0] || {}]
		for (const route of routes) {
			rows.push({
				...route,
				sequence: step.sequence,
				process_name: step.process_name,
				input_item: step.input_item,
				output_item: step.output_item,
				from_colour: colourChange ? route.from_colour : "",
				to_colour: colourChange ? route.to_colour : "",
				quantity_ratio: Number(step.quantity_ratio || 1),
			})
		}
	}
	emit("update:modelValue", rows)
	emit("change")
	emitSummary()
}

function emitSummary() {
	const first = steps.value[0]
	const last = steps.value[steps.value.length - 1]
	emit("summary", {
		processCount: steps.value.length,
		routeCount: steps.value.reduce((total, step) => total + (isColourChange(step) ? Math.max(1, step.routes.length) : 1), 0),
		startingYarn: first?.input_item || "",
		finalYarn: last?.output_item || "",
	})
}

defineExpose({ focusAddAction })
</script>

<style scoped>
.ipd-yarn-flow { display: grid; gap: 16px; }
.finished-context { display: flex; align-items: flex-start; gap: 20px; padding: 16px; border: 1px solid #eadfcf; border-radius: 12px; background: #fffaf1; }
.finished-context > div:first-child { min-width: 190px; }
.finished-context small, .finished-context strong { display: block; }
.finished-context small { color: #6b7280; font-size: 12px; }
.finished-context strong { margin-top: 3px; color: #17233a; }
.finished-attributes { display: flex; flex-wrap: wrap; gap: 8px; }
.finished-attributes > button { position: relative; min-width: 110px; padding: 8px 34px 8px 10px; border: 1px solid transparent; border-radius: 9px; background: #fff; text-align: left; }
.finished-attributes > button:disabled { opacity: 1; }
.finished-attributes > button.editable { cursor: pointer; }
.finished-attributes > button.editable:hover { border-color: #c99b55; }
.finished-attributes b { display: block; color: #99651c; font-size: 12px; }
.finished-attributes i { position: absolute; top: 50%; right: 11px; color: #9b671f; font-size: 11px; transform: translateY(-50%); }
.flow-loading, .flow-empty { display: flex; align-items: center; gap: 12px; min-height: 92px; padding: 18px; border: 1px dashed #d6cbbc; border-radius: 12px; color: #667085; }
.flow-empty > span { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 11px; background: #f4e7ce; color: #9b671f; }
.flow-empty > div { display: grid; gap: 3px; }
.flow-empty > div strong { color: #17233a; }
.flow-empty > div small { font-size: 12px; }
.flow-empty > :last-child { margin-left: auto; }
.flow-steps { display: grid; }
.flow-card { overflow: hidden; border: 1px solid #dfe4ea; border-radius: 13px; background: #fff; box-shadow: 0 5px 18px rgba(23, 32, 51, .04); }
.flow-card > header { display: flex; align-items: center; gap: 10px; padding: 13px 15px; border-bottom: 1px solid #edf0f3; background: #f9fafb; }
.step-number { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; background: #14233c; color: #fff; font-size: 12px; font-weight: 800; }
.step-title { display: grid; }
.step-title strong { color: #17233a; }
.step-title small { color: #667085; font-size: 11px; }
.step-actions { display: flex; margin-left: auto; }
.item-route { display: grid; grid-template-columns: minmax(0, 1fr) 34px minmax(0, 1fr); align-items: center; gap: 8px; padding: 16px; }
.item-route > div { display: grid; gap: 3px; min-width: 0; }
.item-route small { color: #667085; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
.item-route strong { overflow-wrap: anywhere; color: #0d7f73; }
.item-route span { color: #667085; font-size: 11px; }
.item-route > i { color: #9ca3af; text-align: center; }
.colour-routes { display: flex; flex-wrap: wrap; gap: 7px; padding: 0 16px 16px; }
.colour-routes span { display: inline-flex; align-items: center; gap: 6px; padding: 6px 9px; border-radius: 999px; background: #eef6ff; color: #285d9b; font-size: 12px; font-weight: 700; }
.colour-routes i { font-size: 9px; }
.flow-connector { display: grid; place-items: center; height: 52px; color: #8b6b3c; }
.flow-connector span { font-size: 20px; line-height: 1; }
.flow-connector small { font-size: 10px; }
.add-process-row { display: flex; justify-content: center; }
.process-editor { display: grid; gap: 16px; padding: 18px; border: 2px solid #d9c8ab; border-radius: 14px; background: #fffdf9; }
.process-editor > header { display: flex; align-items: center; gap: 12px; }
.process-editor > header > div { display: grid; }
.process-editor > header small { color: #a04231; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .07em; }
.process-editor > header strong { color: #17233a; font-size: 16px; }
.process-editor > header > span { margin-left: auto; padding: 5px 9px; border-radius: 999px; background: #f4e7ce; color: #8c5b19; font-size: 11px; font-weight: 800; }
.editor-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.editor-grid label { display: grid; gap: 6px; min-width: 0; }
.editor-grid label > span { color: #4d5b70; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }
.editor-grid label > small { color: #667085; font-size: 11px; }
.transition-editor { display: grid; gap: 10px; padding: 14px; border-radius: 12px; background: #f7f9fc; }
.transition-editor > header { display: flex; align-items: center; gap: 10px; }
.transition-editor > header > div { display: grid; }
.transition-editor > header small { color: #667085; font-size: 11px; }
.transition-editor > header > :last-child { margin-left: auto; }
.transition-row { display: grid; grid-template-columns: minmax(0, 1fr) 24px minmax(0, 1fr) 36px; align-items: center; gap: 7px; }
.transition-row > i { color: #9ca3af; text-align: center; }
.inline-warning { display: flex; align-items: center; gap: 7px; color: #9a6314; font-size: 12px; }
.process-editor > footer { display: flex; justify-content: flex-end; gap: 8px; }
@media (max-width: 720px) {
	.finished-context { display: grid; }
	.editor-grid { grid-template-columns: 1fr; }
	.item-route { grid-template-columns: 1fr; }
	.item-route > i { transform: rotate(90deg); }
	.transition-editor > header { display: grid; align-items: flex-start; gap: 8px; }
	.transition-editor > header > :last-child { justify-self: start; margin-left: 0; }
	.transition-row {
		grid-template-columns: minmax(0, 1fr) 36px;
		grid-template-areas:
			"source remove"
			"arrow arrow"
			"outputs outputs";
	}
	.transition-row > :first-child { grid-area: source; }
	.transition-row > i { grid-area: arrow; transform: rotate(90deg); }
	.transition-row > :nth-child(3) { grid-area: outputs; min-width: 0; max-width: 100%; }
	.transition-row > :nth-child(4) { grid-area: remove; }
	.transition-row :deep(.p-multiselect-label) { display: flex; flex-wrap: wrap; gap: 4px; white-space: normal; }
	.flow-empty { align-items: flex-start; flex-wrap: wrap; }
	.flow-empty > :last-child { width: 100%; margin-left: 0; }
}
</style>
