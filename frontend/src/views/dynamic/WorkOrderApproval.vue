<!--
  Work Order design-approval gate (doctype-specific addition to DocDetail).

  Wires the mgk_clothing_yrp approval API:
    - mgk_clothing_yrp.mgk_clothing_yrp.api.work_order.get_approval_state
    - .../work_order.approve
    - .../work_order.reject

  Renders (per the approved MGK_WEB.html WO detail):
    - a gate BANNER explaining the before_submit block (warn or cleared variant)
    - Approve / Reject buttons (perm + docstatus gated by the server's
      `can_approve` flag) — Reject opens a Dialog with a required reason
    - the design-approval summary (status / last action) as a side-panel slot

  Read-only chunk note: this DOES perform writes via approve/reject because
  approval is the headline feature of this chunk. It does NOT submit/cancel the
  WO itself — that gate stays for Chunk 2.

  Usage:
    <WorkOrderApproval :name="doc.name" :docstatus="doc.docstatus"
        :approval-log="doc.mgk_approval_log" @changed="onChanged" />
    + named slot exposed via <template #side> for the side-panel card.
-->
<template>
	<div class="wo-approval">
		<!-- Gate banner -->
		<div
			v-if="state && state.needs_approval"
			class="gate-banner"
			:class="{ cleared: isApproved }"
		>
			<i :class="isApproved ? 'pi pi-check-circle g-ic' : 'pi pi-flag g-ic'" />
			<div v-if="isApproved">
				<b>Design approved.</b> Signed off by <b>{{ state.approved_by }}</b>.
				Submit is unblocked (subject to <code>before_submit</code> checks).
			</div>
			<div v-else>
				<b>Design approval required.</b> This is a gated process
				(<b>{{ state.approver_role }}</b>). <b>Submit is blocked</b> until an
				approver signs off — enforced server-side by
				<code>Work&nbsp;Order.before_submit()</code> against
				<code>mgk_approval_log</code>.
				<span v-if="state.rejection_reason">
					Last decision: <b>Rejected</b> — <i>"{{ state.rejection_reason }}"</i>.
				</span>
			</div>

			<!-- Approve / Reject — only when server says this user can act -->
			<div v-if="showActions" class="g-actions">
				<Button
					label="Approve"
					icon="pi pi-check"
					size="small"
					:loading="acting === 'approve'"
					@click="doApprove"
				/>
				<Button
					label="Reject"
					icon="pi pi-times"
					size="small"
					severity="danger"
					outlined
					:loading="acting === 'reject'"
					@click="openReject"
				/>
			</div>
		</div>

		<!-- Reject dialog: required reason -->
		<Dialog
			v-model:visible="rejectOpen"
			modal
			header="Reject design approval"
			:style="{ width: '460px' }"
		>
			<p class="reject-help">
				A reason is required. It is recorded against the Work Order and
				appended to the approval log.
			</p>
			<Textarea
				v-model="rejectReason"
				rows="4"
				autoResize
				class="reject-input"
				placeholder="e.g. Border pattern doesn't match approved swatch — re-share shade card."
			/>
			<small v-if="rejectError" class="reject-error">{{ rejectError }}</small>
			<template #footer>
				<Button label="Cancel" text severity="secondary" @click="rejectOpen = false" />
				<Button
					label="Reject"
					icon="pi pi-times"
					severity="danger"
					:loading="acting === 'reject'"
					@click="doReject"
				/>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import Button from "primevue/button"
import Dialog from "primevue/dialog"
import Textarea from "primevue/textarea"
import { callMethod } from "@/api/client"
import { useAppToast } from "@/composables/useToast"
import { useAppConfirm } from "@/composables/useConfirm"

const API = "mgk_clothing_yrp.mgk_clothing_yrp.api.work_order"

const props = defineProps({
	name: { type: String, required: true },
	docstatus: { type: Number, default: 0 },
	// Loaded `modified` timestamp — forwarded to approve/reject so the backend's
	// stale-write guard (_guard_not_modified) rejects a concurrent edit.
	modified: { type: String, default: null },
})

const emit = defineEmits(["changed", "state"])

const toast = useAppToast()
const confirm = useAppConfirm()

const state = ref(null)
const acting = ref(null) // "approve" | "reject" | null
const rejectOpen = ref(false)
const rejectReason = ref("")
const rejectError = ref("")

const isApproved = computed(() => !!state.value?.approved_by)

// Server is the source of truth for whether THIS user can act. We additionally
// require docstatus 0 (only a draft can be approved) and not-already-approved.
const showActions = computed(
	() =>
		!!state.value &&
		state.value.can_approve &&
		!state.value.approved_by &&
		Number(state.value.docstatus) === 0,
)

async function loadState() {
	if (!props.name) return
	try {
		state.value = await callMethod(`${API}.get_approval_state`, {
			work_order: props.name,
		})
		emit("state", state.value)
	} catch (e) {
		// Non-fatal: a WO whose process isn't gated still renders fine.
		state.value = null
		emit("state", null)
	}
}

watch(() => props.name, loadState, { immediate: true })

// Q7: the design sign-off is the single most consequential, irreversible action
// in the WO flow — gate it behind a confirm that names the consequence, the same
// way Submit / Reject / Cancel are guarded.
function doApprove() {
	confirm.require({
		header: "Approve design?",
		message: `Approve the design for ${props.name}? This unblocks Submit for this Work Order.`,
		icon: "pi pi-check-circle",
		acceptLabel: "Approve",
		acceptClass: "p-button-primary",
		rejectLabel: "Cancel",
		accept: performApprove,
	})
}

async function performApprove() {
	acting.value = "approve"
	try {
		await callMethod(`${API}.approve`, { work_order: props.name, modified: props.modified })
		toast.success("Approved", `${props.name} design approved`, 6000)
		await loadState()
		emit("changed")
	} catch (e) {
		toast.error("Approve failed", e.message)
	} finally {
		acting.value = null
	}
}

function openReject() {
	rejectReason.value = ""
	rejectError.value = ""
	rejectOpen.value = true
}

async function doReject() {
	if (!rejectReason.value.trim()) {
		rejectError.value = "A reason is required to reject."
		return
	}
	acting.value = "reject"
	try {
		await callMethod(`${API}.reject`, {
			work_order: props.name,
			reason: rejectReason.value.trim(),
			modified: props.modified,
		})
		toast.success("Rejected", `${props.name} design rejected`, 6000)
		rejectOpen.value = false
		await loadState()
		emit("changed")
	} catch (e) {
		toast.error("Reject failed", e.message)
	} finally {
		acting.value = null
	}
}

defineExpose({ state, reload: loadState })
</script>

<style scoped>
/* Gate banner — replicates MGK_WEB.html .gate-banner (warn + cleared) */
.gate-banner {
	display: flex;
	align-items: flex-start;
	gap: 10px;
	background: var(--mgk-warn-50);
	border: 1px solid var(--mgk-warn);
	border-radius: var(--radius-sm);
	padding: 11px 14px;
	margin-bottom: 14px;
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
	line-height: 1.3;
	flex-shrink: 0;
}

.gate-banner code {
	font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
	font-size: 11.5px;
	background: rgba(0, 0, 0, 0.05);
	padding: 1px 4px;
	border-radius: 3px;
}

.g-actions {
	margin-left: auto;
	display: flex;
	gap: 8px;
	flex-shrink: 0;
}

.reject-help {
	margin: 0 0 10px;
	font-size: 12.5px;
	color: var(--mgk-muted);
}

.reject-input {
	width: 100%;
}

.reject-error {
	display: block;
	margin-top: 6px;
	color: var(--mgk-danger);
	font-size: 12px;
}
</style>
