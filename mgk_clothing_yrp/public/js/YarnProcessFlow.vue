<template>
	<div class="mgk-yarn-flow">
		<div v-if="!steps.length" class="yf-empty">
			{{ __("No yarn processes yet. Add Doubling or Dyeing to define the flow.") }}
		</div>

		<div class="yf-flow">
			<template v-for="(step, index) in steps" :key="step.sequence">
				<article class="yf-card">
					<header class="yf-card-head">
						<span class="yf-sequence">{{ index + 1 }}</span>
						<div>
							<div class="yf-process">{{ step.process_name || __("(no process)") }}</div>
							<span class="yf-badge" :class="isConversion(step) ? 'is-conversion' : 'is-colour'">
								{{ isConversion(step) ? __("Item Conversion") : __("Colour Change") }}
							</span>
						</div>
						<div v-if="editable" class="yf-actions">
							<button type="button" class="btn btn-xs btn-default" @click="editStep(index)">
								{{ __("Edit") }}
							</button>
							<button type="button" class="yf-remove" :title="__('Remove step')" @click="removeStep(index)">
								×
							</button>
						</div>
					</header>

					<div class="yf-route">
						<strong>{{ step.input_item || "—" }}</strong>
						<span class="yf-arrow">→</span>
						<strong>{{ step.output_item || "—" }}</strong>
						<span class="yf-ratio">{{ ratioLabel(step) }}</span>
					</div>

					<div v-if="!isConversion(step)" class="yf-colours">
						<span
							v-for="(route, routeIndex) in step.routes"
							:key="routeIndex"
							class="yf-colour-route"
						>
							{{ route.from_colour || "—" }}
							<span class="yf-arrow">→</span>
							{{ route.to_colour || "—" }}
						</span>
					</div>
					<p v-else class="yf-note">
						{{ __("All common yarn attributes carry to the output Item.") }}
					</p>
				</article>
				<div v-if="index < steps.length - 1" class="yf-connector">
					<span>↓</span>
					<small>{{ __("output becomes next input") }}</small>
				</div>
			</template>
		</div>

		<div v-if="editable && availableProcesses.length && !draft" class="yf-addbar">
			<label>
				<span>{{ __("Add a process") }}</span>
				<select v-model="selectedProcess" class="form-control">
					<option value="">{{ __("Select…") }}</option>
					<option v-for="process in availableProcesses" :key="process.name" :value="process.name">
						{{ process.name }}
					</option>
				</select>
			</label>
			<button type="button" class="btn btn-primary btn-sm" :disabled="!selectedProcess" @click="addStep">
				{{ __("Add & define") }}
			</button>
		</div>

		<section v-if="draft" class="yf-editor">
			<div class="yf-editor-title">
				<span>{{ editingIndex === null ? __("Add Yarn Process") : __("Edit Yarn Process") }}</span>
				<span class="yf-badge" :class="draftConversion ? 'is-conversion' : 'is-colour'">
					{{ draftConversion ? __("Item Conversion") : __("Colour Change") }}
				</span>
			</div>

			<div class="yf-grid">
				<label>
					<span>{{ __("Process") }}</span>
					<select v-model="draft.process_name" class="form-control" @change="processChanged">
						<option v-for="process in processes" :key="process.name" :value="process.name">
							{{ process.name }}
						</option>
					</select>
				</label>
				<label>
					<span>{{ __("Input Yarn Item") }}</span>
					<select v-model="draft.input_item" class="form-control" @change="inputChanged">
						<option value="">{{ __("Select…") }}</option>
						<option v-for="item in yarnItems" :key="item" :value="item">{{ item }}</option>
					</select>
				</label>
				<label>
					<span>{{ __("Output Yarn Item") }}</span>
					<select v-model="draft.output_item" class="form-control" :disabled="!draftConversion">
						<option value="">{{ __("Select…") }}</option>
						<option v-for="item in yarnItems" :key="item" :value="item">{{ item }}</option>
					</select>
				</label>
				<label>
					<span>{{ __("Output per Input") }}</span>
					<input v-model.number="draft.quantity_ratio" type="number" min="0.000001" step="0.01" class="form-control" />
				</label>
			</div>

			<div v-if="!draftConversion" class="yf-transition-editor">
				<div class="yf-transition-head">{{ __("Colour transitions") }}</div>
				<div v-for="(route, index) in draft.routes" :key="index" class="yf-transition-row">
					<select v-model="route.from_colour" class="form-control">
						<option value="">{{ __("From colour…") }}</option>
						<option v-for="colour in colours" :key="colour" :value="colour">{{ colour }}</option>
					</select>
					<span class="yf-arrow">→</span>
					<select v-model="route.to_colour" class="form-control">
						<option value="">{{ __("To colour…") }}</option>
						<option v-for="colour in colours" :key="colour" :value="colour">{{ colour }}</option>
					</select>
					<button
						v-if="draft.routes.length > 1"
						type="button"
						class="yf-remove"
						:title="__('Remove transition')"
						@click="draft.routes.splice(index, 1)"
					>
						×
					</button>
				</div>
				<button type="button" class="btn btn-xs btn-default" @click="addColourRoute">
					+ {{ __("Another colour transition") }}
				</button>
			</div>

			<div class="yf-editor-actions">
				<button type="button" class="btn btn-primary btn-sm" @click="saveDraft">
					{{ __("Save step") }}
				</button>
				<button type="button" class="btn btn-default btn-sm" @click="cancelDraft">
					{{ __("Cancel") }}
				</button>
			</div>
		</section>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";

const steps = ref([]);
const processes = ref([]);
const yarnItems = ref([]);
const colours = ref([]);
const editable = ref(false);
const selectedProcess = ref("");
const draft = ref(null);
const editingIndex = ref(null);
let onChange = null;

const processByName = computed(() => {
	const result = {};
	for (const process of processes.value) {
		result[process.name] = process;
	}
	return result;
});

const availableProcesses = computed(() => {
	const used = new Set(steps.value.map((step) => step.process_name));
	return processes.value.filter((process) => !used.has(process.name));
});

const draftConversion = computed(() => {
	if (!draft.value) return false;
	return Boolean(processByName.value[draft.value.process_name]?.is_item_conversion);
});

function clone(value) {
	return JSON.parse(JSON.stringify(value));
}

function isConversion(step) {
	const process = processByName.value[step.process_name];
	if (process) return Boolean(process.is_item_conversion);
	return step.input_item !== step.output_item;
}

function ratioLabel(step) {
	const ratio = Number(step.quantity_ratio || 1);
	return ratio === 1 ? __("1 : 1") : __("1 : {0}", [ratio]);
}

function groupRows(rows) {
	const grouped = new Map();
	for (const row of rows || []) {
		const sequence = Number(row.sequence || 0);
		if (!grouped.has(sequence)) {
			grouped.set(sequence, {
				sequence,
				process_name: row.process_name || "",
				input_item: row.input_item || "",
				output_item: row.output_item || "",
				quantity_ratio: Number(row.quantity_ratio || 1),
				routes: [],
			});
		}
		grouped.get(sequence).routes.push({
			from_colour: row.from_colour || "",
			to_colour: row.to_colour || "",
		});
	}
	return [...grouped.values()].sort((a, b) => a.sequence - b.sequence);
}

function load_data(payload, changeHandler) {
	processes.value = clone(payload.processes || []);
	yarnItems.value = clone(payload.yarn_items || []);
	colours.value = clone(payload.colours || []);
	editable.value = Boolean(payload.editable);
	steps.value = groupRows(payload.routes || []);
	onChange = changeHandler;
	selectedProcess.value = "";
	draft.value = null;
	editingIndex.value = null;
}

function get_steps() {
	return clone(steps.value);
}

function addStep() {
	if (!selectedProcess.value) return;
	const previous = steps.value[steps.value.length - 1];
	const process = processByName.value[selectedProcess.value] || {};
	const inputItem = previous?.output_item || "";
	draft.value = {
		sequence: Math.max(0, ...steps.value.map((step) => Number(step.sequence || 0))) + 10,
		process_name: selectedProcess.value,
		input_item: inputItem,
		output_item: process.is_item_conversion ? "" : inputItem,
		quantity_ratio: 1,
		routes: [{ from_colour: "", to_colour: "" }],
	};
	editingIndex.value = null;
}

function editStep(index) {
	draft.value = clone(steps.value[index]);
	editingIndex.value = index;
}

function processChanged() {
	if (!draft.value) return;
	if (draftConversion.value) {
		if (draft.value.output_item === draft.value.input_item) {
			draft.value.output_item = "";
		}
		draft.value.routes = [{ from_colour: "", to_colour: "" }];
	} else {
		draft.value.output_item = draft.value.input_item;
		if (!draft.value.routes.length) addColourRoute();
	}
}

function inputChanged() {
	if (draft.value && !draftConversion.value) {
		draft.value.output_item = draft.value.input_item;
	}
}

function addColourRoute() {
	draft.value.routes.push({ from_colour: "", to_colour: "" });
}

function validateDraft() {
	if (!draft.value.process_name || !draft.value.input_item || !draft.value.output_item) {
		frappe.msgprint(__("Select the Process, Input Yarn Item, and Output Yarn Item."));
		return false;
	}
	if (Number(draft.value.quantity_ratio || 0) <= 0) {
		frappe.msgprint(__("Output per Input must be greater than zero."));
		return false;
	}
	if (draftConversion.value) {
		if (draft.value.input_item === draft.value.output_item) {
			frappe.msgprint(__("Doubling must convert the input Yarn Item into a different output Yarn Item."));
			return false;
		}
		return true;
	}
	draft.value.output_item = draft.value.input_item;
	if (!draft.value.routes.length || draft.value.routes.some(
		(route) => !route.from_colour || !route.to_colour || route.from_colour === route.to_colour
	)) {
		frappe.msgprint(__("Every Dyeing transition needs two different From and To colours."));
		return false;
	}
	const keys = draft.value.routes.map((route) => `${route.from_colour}\u0000${route.to_colour}`);
	if (new Set(keys).size !== keys.length) {
		frappe.msgprint(__("Remove the duplicate Dyeing colour transition."));
		return false;
	}
	return true;
}

function saveDraft() {
	if (!validateDraft()) return;
	const oldOutput = editingIndex.value === null
		? null
		: steps.value[editingIndex.value].output_item;
	if (editingIndex.value === null) {
		steps.value.push(clone(draft.value));
	} else {
		steps.value.splice(editingIndex.value, 1, clone(draft.value));
		const next = steps.value[editingIndex.value + 1];
		if (next && next.input_item === oldOutput) {
			next.input_item = draft.value.output_item;
			if (!isConversion(next)) next.output_item = draft.value.output_item;
		}
	}
	steps.value.sort((a, b) => a.sequence - b.sequence);
	emitChange();
	cancelDraft();
}

function removeStep(index) {
	steps.value.splice(index, 1);
	steps.value.forEach((step, position) => {
		step.sequence = (position + 1) * 10;
	});
	emitChange();
}

function cancelDraft() {
	draft.value = null;
	editingIndex.value = null;
	selectedProcess.value = "";
}

function emitChange() {
	if (!onChange) return;
	const routes = [];
	for (const step of steps.value) {
		const stepRoutes = isConversion(step)
			? [{ from_colour: "", to_colour: "" }]
			: step.routes;
		for (const route of stepRoutes) {
			routes.push({
				sequence: step.sequence,
				process_name: step.process_name,
				input_item: step.input_item,
				output_item: step.output_item,
				from_colour: route.from_colour || "",
				to_colour: route.to_colour || "",
				quantity_ratio: Number(step.quantity_ratio || 1),
			});
		}
	}
	onChange({ routes });
}

defineExpose({ load_data, get_steps });
</script>

<style scoped>
.mgk-yarn-flow {
	--yf-border: var(--border-color, #d8d8d8);
	--yf-muted: var(--text-muted, #6c7680);
	margin-bottom: 1rem;
}

.yf-empty,
.yf-card,
.yf-editor,
.yf-addbar {
	border: 1px solid var(--yf-border);
	border-radius: 8px;
	background: var(--card-bg, #fff);
}

.yf-empty {
	padding: 1rem;
	color: var(--yf-muted);
}

.yf-flow {
	display: flex;
	flex-direction: column;
}

.yf-card {
	padding: 1rem;
}

.yf-card-head {
	display: flex;
	align-items: flex-start;
	gap: 0.75rem;
}

.yf-sequence {
	display: inline-grid;
	place-items: center;
	width: 1.75rem;
	height: 1.75rem;
	border-radius: 50%;
	background: var(--primary, #2490ef);
	color: #fff;
	font-weight: 700;
}

.yf-process {
	font-weight: 650;
	font-size: 1rem;
}

.yf-badge {
	display: inline-block;
	margin-top: 0.2rem;
	padding: 0.12rem 0.45rem;
	border-radius: 999px;
	font-size: 0.72rem;
	font-weight: 600;
}

.yf-badge.is-conversion {
	background: #e8f3ff;
	color: #1768ac;
}

.yf-badge.is-colour {
	background: #f3eaff;
	color: #7044a0;
}

.yf-actions {
	display: flex;
	align-items: center;
	gap: 0.45rem;
	margin-left: auto;
}

.yf-remove {
	border: 0;
	background: transparent;
	color: var(--yf-muted);
	font-size: 1.25rem;
	line-height: 1;
}

.yf-route {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 0.55rem;
	margin: 0.9rem 0 0.55rem 2.5rem;
}

.yf-arrow {
	color: var(--yf-muted);
}

.yf-ratio {
	margin-left: auto;
	color: var(--yf-muted);
	font-size: 0.8rem;
}

.yf-colours {
	display: flex;
	flex-wrap: wrap;
	gap: 0.4rem;
	margin-left: 2.5rem;
}

.yf-colour-route {
	padding: 0.28rem 0.5rem;
	border-radius: 5px;
	background: var(--control-bg, #f6f7f8);
	font-size: 0.82rem;
}

.yf-note {
	margin: 0 0 0 2.5rem;
	color: var(--yf-muted);
	font-size: 0.82rem;
}

.yf-connector {
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: 0.15rem 0;
	color: var(--yf-muted);
	line-height: 1;
}

.yf-connector small {
	font-size: 0.68rem;
}

.yf-addbar {
	display: flex;
	align-items: flex-end;
	gap: 0.75rem;
	margin-top: 0.85rem;
	padding: 0.85rem;
}

.yf-addbar label {
	flex: 1;
	margin: 0;
}

.yf-addbar label > span,
.yf-grid label > span {
	display: block;
	margin-bottom: 0.3rem;
	color: var(--yf-muted);
	font-size: 0.78rem;
	font-weight: 600;
}

.yf-editor {
	margin-top: 0.85rem;
	padding: 1rem;
}

.yf-editor-title {
	display: flex;
	align-items: center;
	gap: 0.55rem;
	margin-bottom: 0.85rem;
	font-weight: 650;
}

.yf-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 0.75rem;
}

.yf-grid label {
	margin: 0;
}

.yf-transition-editor {
	margin-top: 1rem;
	padding-top: 0.85rem;
	border-top: 1px solid var(--yf-border);
}

.yf-transition-head {
	margin-bottom: 0.55rem;
	font-weight: 600;
}

.yf-transition-row {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto;
	align-items: center;
	gap: 0.5rem;
	margin-bottom: 0.5rem;
}

.yf-editor-actions {
	display: flex;
	gap: 0.5rem;
	margin-top: 1rem;
}

@media (max-width: 700px) {
	.yf-grid {
		grid-template-columns: 1fr;
	}

	.yf-transition-row {
		grid-template-columns: 1fr auto 1fr auto;
	}

	.yf-addbar {
		align-items: stretch;
		flex-direction: column;
	}
}
</style>
