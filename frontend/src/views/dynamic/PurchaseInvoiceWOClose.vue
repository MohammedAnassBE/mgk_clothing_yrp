<!--
  Purchase Invoice — close the linked Work Orders before submit.

  yrp gates PI submit on ALL linked WOs being closed (before_submit →
  check_all_wo_closed). A PI can span GRNs from several WOs (e.g. 3 GRNs → 2 WOs);
  every one must reach open_status == "Close". This panel surfaces the open /
  close-request WOs and lets the user close them WITHOUT leaving the PI — mirrors
  the Desk purchase_invoice.js open_close_dialog flow.

  Server contract (yrp):
    - purchase_invoice.check_all_wo_closed(purchase_invoice)
        → {all_closed, open_work_orders, close_request_wos}
    - work_order.get_close_permission() → {approver_role, is_close_manager}
    - work_order.update_stock(work_order, close_reason, close_other_reason, close_remarks)
        (non-manager → "Close Request"; manager → "Close")
    - debit.create_debit(work_order, debit_no, debit_value, reason, on_close=1)  (optional, before close)

  Rendered by DocDetail in VIEW mode for a DRAFT, Work-Order-based PI only.
-->
<template>
	<div v-if="show" class="pi-wo-close">
		<div class="gate-banner" :class="{ cleared: allClosed }">
			<i :class="allClosed ? 'pi pi-check-circle g-ic' : 'pi pi-flag g-ic'" />
			<div v-if="allClosed">
				<b>All Work Orders closed.</b> Submit is unblocked (subject to
				<code>before_submit</code> checks).
			</div>
			<div v-else>
				<b>{{ pendingCount }} Work Order(s) must be closed</b> before this invoice
				can be submitted — enforced server-side by
				<code>before_submit → check_all_wo_closed</code>.
			</div>
		</div>

		<div v-if="!allClosed" class="wo-list">
			<div v-for="wo in openWos" :key="'o-' + wo" class="wo-row">
				<span class="wo-name">{{ wo }}</span>
				<span class="wo-badge open">Open</span>
				<Button
					:label="perm && perm.is_close_manager ? 'Close' : 'Request Close'"
					icon="pi pi-lock"
					size="small"
					severity="warn"
					:loading="acting === wo"
					@click="openCloseDialog(wo)"
				/>
			</div>
			<div v-for="wo in closeRequestWos" :key="'r-' + wo" class="wo-row">
				<span class="wo-name">{{ wo }}</span>
				<span class="wo-badge req">Close Requested</span>
				<Button
					v-if="perm && perm.is_close_manager"
					label="Approve Close"
					icon="pi pi-check"
					size="small"
					severity="success"
					:loading="acting === wo"
					@click="openCloseDialog(wo)"
				/>
				<span v-else class="wo-muted">awaiting manager approval</span>
			</div>
		</div>

		<!-- Close dialog (mirrors Desk open_close_dialog) -->
		<Dialog
			v-model:visible="closeOpen"
			modal
			:header="`Close Work Order ${closeWo}`"
			:style="{ width: 'min(520px, calc(100vw - 32px))' }"
		>
			<div class="close-form">
				<label class="fld-l">Close Reason *</label>
				<Select
					v-model="cf.close_reason"
					:options="closeReasons"
					placeholder="Select a reason"
					class="fld"
					fluid
				/>
				<template v-if="cf.close_reason === 'Others'">
					<label class="fld-l">Other Reason *</label>
					<InputText v-model="cf.close_other_reason" class="fld" fluid />
				</template>
				<label class="fld-l">Close Remarks</label>
				<Textarea v-model="cf.close_remarks" rows="2" autoResize class="fld" fluid />

				<div class="debit-toggle">
					<Checkbox v-model="cf.with_debit" binary inputId="pi-with-debit" />
					<label for="pi-with-debit">Raise a debit on close</label>
				</div>
				<template v-if="cf.with_debit">
					<label class="fld-l">Debit No *</label>
					<InputText v-model="cf.debit_no" class="fld" fluid />
					<label class="fld-l">Debit Value *</label>
					<InputText v-model="cf.debit_value" inputmode="decimal" class="fld" fluid />
					<label class="fld-l">Debit Reason *</label>
					<Textarea v-model="cf.debit_reason" rows="2" autoResize class="fld" fluid />
				</template>
				<small v-if="closeError" class="close-error">{{ closeError }}</small>
			</div>
			<template #footer>
				<Button label="Cancel" text severity="secondary" @click="closeOpen = false" />
				<Button
					label="Close Work Order"
					icon="pi pi-lock"
					:loading="acting === closeWo"
					@click="doClose"
				/>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { ref, reactive, computed, watch } from "vue"
import Button from "primevue/button"
import Dialog from "primevue/dialog"
import Select from "primevue/select"
import InputText from "primevue/inputtext"
import Textarea from "primevue/textarea"
import Checkbox from "primevue/checkbox"
import { callMethod } from "@/api/client"
import { useAppToast } from "@/composables/useToast"

const PI = "yrp.yrp.doctype.purchase_invoice.purchase_invoice"
const WO = "yrp.yrp.doctype.work_order.work_order"
const DEBIT = "yrp.yrp.doctype.debit.debit"

const props = defineProps({
	name: { type: String, required: true },
	docstatus: { type: Number, default: 0 },
	against: { type: String, default: "" },
})
const emit = defineEmits(["changed"])
const toast = useAppToast()

const closeReasons = ["Cutting Shortage", "Printing Shortage", "Sewing Shortage", "Sewing Missing", "Others"]

const closeState = ref(null)
const perm = ref(null)
const acting = ref(null)
const closeOpen = ref(false)
const closeWo = ref("")
const closeError = ref("")
const cf = reactive({
	with_debit: false,
	debit_no: "",
	debit_value: "",
	debit_reason: "",
	close_reason: "",
	close_other_reason: "",
	close_remarks: "",
})

const isDraftWo = computed(
	() => props.against === "Work Order" && Number(props.docstatus) === 0,
)
const show = computed(() => isDraftWo.value && !!closeState.value)
const allClosed = computed(() => !!closeState.value?.all_closed)
const openWos = computed(() => closeState.value?.open_work_orders || [])
const closeRequestWos = computed(() => closeState.value?.close_request_wos || [])
const pendingCount = computed(() => openWos.value.length + closeRequestWos.value.length)

async function loadState() {
	if (!props.name || !isDraftWo.value) {
		closeState.value = null
		return
	}
	try {
		closeState.value = await callMethod(`${PI}.check_all_wo_closed`, {
			purchase_invoice: props.name,
		})
		perm.value = await callMethod(`${WO}.get_close_permission`)
	} catch (e) {
		closeState.value = null
	}
}

watch(() => [props.name, props.docstatus, props.against], loadState, { immediate: true })

function openCloseDialog(wo) {
	closeWo.value = wo
	closeError.value = ""
	cf.with_debit = false
	cf.debit_no = ""
	cf.debit_value = ""
	cf.debit_reason = ""
	cf.close_reason = ""
	cf.close_other_reason = ""
	cf.close_remarks = ""
	closeOpen.value = true
}

async function doClose() {
	if (!cf.close_reason) return (closeError.value = "Close reason is required.")
	if (cf.close_reason === "Others" && !cf.close_other_reason.trim())
		return (closeError.value = "Other reason is required.")
	if (cf.with_debit && (!cf.debit_no.trim() || !parseFloat(cf.debit_value) || !cf.debit_reason.trim()))
		return (closeError.value = "Debit no, value and reason are required.")
	acting.value = closeWo.value
	try {
		if (cf.with_debit) {
			await callMethod(`${DEBIT}.create_debit`, {
				work_order: closeWo.value,
				debit_no: cf.debit_no,
				debit_value: parseFloat(cf.debit_value) || 0,
				reason: cf.debit_reason,
				on_close: 1,
			})
		}
		const res = await callMethod(`${WO}.update_stock`, {
			work_order: closeWo.value,
			close_reason: cf.close_reason,
			close_other_reason: cf.close_other_reason,
			close_remarks: cf.close_remarks,
		})
		toast.success(`Work Order ${res === "Close" ? "closed" : "close requested"}`, closeWo.value)
		closeOpen.value = false
		await loadState()
		emit("changed")
	} catch (e) {
		toast.error("Close failed", e.message)
	} finally {
		acting.value = null
	}
}

defineExpose({ reload: loadState })
</script>

<style scoped>
.pi-wo-close {
	margin-bottom: 14px;
}
.gate-banner {
	display: flex;
	align-items: flex-start;
	gap: 10px;
	background: var(--mgk-warn-50);
	border: 1px solid var(--mgk-warn);
	border-radius: var(--radius-sm);
	padding: 11px 14px;
	margin-bottom: 12px;
	font-size: 12.5px;
	color: var(--mgk-warn);
	line-height: 1.5;
}
.gate-banner.cleared {
	background: var(--mgk-success-50);
	border-color: var(--mgk-success);
	color: var(--mgk-success);
}
.gate-banner .g-ic {
	font-size: 16px;
	flex-shrink: 0;
}
.gate-banner code {
	font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
	font-size: 11.5px;
	background: rgba(0, 0, 0, 0.05);
	padding: 1px 4px;
	border-radius: 3px;
}
.wo-list {
	display: flex;
	flex-direction: column;
	gap: 8px;
}
.wo-row {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 8px 12px;
	border: 1px solid var(--surface-border, #e5e7eb);
	border-radius: var(--radius-sm);
}
.wo-name {
	font-weight: 600;
}
.wo-badge {
	font-size: 11px;
	padding: 2px 8px;
	border-radius: 10px;
}
.wo-badge.open {
	background: var(--mgk-warn-50);
	color: var(--mgk-warn);
}
.wo-badge.req {
	background: #eef2ff;
	color: #4f46e5;
}
.wo-muted {
	color: var(--mgk-muted);
	font-size: 12px;
	margin-left: auto;
}
.wo-row .p-button {
	margin-left: auto;
}
.close-form {
	display: flex;
	flex-direction: column;
	gap: 6px;
}
.fld-l {
	font-size: 12px;
	font-weight: 600;
	margin-top: 6px;
}
.debit-toggle {
	display: flex;
	align-items: center;
	gap: 8px;
	margin-top: 10px;
}
.close-error {
	color: var(--mgk-danger);
	font-size: 12px;
	margin-top: 6px;
}
</style>
