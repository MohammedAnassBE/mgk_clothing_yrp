<template>
	<div class="correction-section">
		<div v-if="!blocks.length" class="correction-empty">
			No correction items{{ editable ? " for this Work Order." : "." }}
		</div>
		<section
			v-for="(block, index) in blocks"
			:key="block.work_order_correction || index"
			class="correction-block"
		>
			<header class="correction-block-title">
				<strong>{{ block.title || block.work_order_correction }}</strong>
				<small>Work Order Correction</small>
			</header>
			<StockItemGridEditor
				:ref="(element) => setBlockRef(index, element)"
				grouped-field="correction_item_details"
				:value-fields="valueFields"
				:entry-fields="entryFields"
				:cell-fields="cellFields"
				:locked-items="true"
				:editable="editable"
				:show-secondary-toggle="showSecondaryToggle"
				:initial-data="block.item_details || []"
				@change="onChange"
				@summary="(summary) => onBlockSummary(index, summary)"
			/>
		</section>
	</div>
</template>

<script setup>
import { ref, watch } from "vue"
import StockItemGridEditor from "./StockItemGridEditor.vue"

const props = defineProps({
	editable: { type: Boolean, default: true },
	valueFields: { type: Array, default: () => [] },
	entryFields: { type: Array, default: () => [] },
	cellFields: { type: Array, default: () => [] },
	showSecondaryToggle: { type: Boolean, default: false },
	initialBlocks: { type: [Array, String], default: null },
})

const emit = defineEmits(["change", "summary"])
const blocks = ref([])
const blockRefs = {}
const blockSummaries = {}

function setBlockRef(index, element) {
	if (element) blockRefs[index] = element
	else delete blockRefs[index]
}

function parseBlocks(data) {
	if (typeof data !== "string") return Array.isArray(data) ? data : []
	try {
		const parsed = JSON.parse(data || "[]")
		return Array.isArray(parsed) ? parsed : []
	} catch (_) {
		return []
	}
}

function loadData(data) {
	blocks.value = parseBlocks(data)
	for (const key of Object.keys(blockSummaries)) delete blockSummaries[key]
	emitSummary()
}

function getItems() {
	return blocks.value.map((block, index) => ({
		...block,
		item_details: blockRefs[index]?.getItems?.() || block.item_details || [],
	}))
}

function hasItems() {
	return blocks.value.length > 0
}

function focusFirstQuantity() {
	return blockRefs[0]?.focusFirstQuantity?.() || false
}

function onChange() {
	emit("change")
}

function onBlockSummary(index, summary) {
	blockSummaries[index] = summary || {}
	emitSummary()
}

function emitSummary() {
	const totals = Object.values(blockSummaries).reduce((result, summary) => ({
		itemCount: result.itemCount + (Number(summary.itemCount) || 0),
		totalQty: result.totalQty + (Number(summary.totalQty) || 0),
		pendingQty: result.pendingQty + (Number(summary.pendingQty) || 0),
		grandTotal: result.grandTotal + (Number(summary.grandTotal) || 0),
	}), { itemCount: 0, totalQty: 0, pendingQty: 0, grandTotal: 0 })
	emit("summary", totals)
}

watch(() => props.initialBlocks, (value) => {
	if (value != null) loadData(value)
}, { immediate: true })

defineExpose({ loadData, getItems, hasItems, focusFirstQuantity })
</script>

<style scoped>
.correction-section {
	display: grid;
	gap: 14px;
}
.correction-empty {
	padding: 18px;
	color: var(--book-muted, #667085);
	font-size: 13px;
}
.correction-block {
	overflow: hidden;
	border: 1px solid var(--book-line, #ded5c7);
	border-radius: 12px;
}
.correction-block-title {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	padding: 10px 14px;
	border-bottom: 1px solid var(--book-line, #ded5c7);
	background: #f7f9fc;
	color: var(--book-ink, #1d2739);
	font-size: 13px;
}
.correction-block-title small {
	color: var(--book-muted, #667085);
	font-size: 11px;
}
</style>
