<!--
  AssignDepartmentModal — assign a submitted Bill Tracking to a Department
  (mirrors the Desk "Assign" dialog in bill_tracking.js). Assignment is
  DEPARTMENT-based, not per-user: the picker targets the Department master and
  on submit we call yrp's whitelisted `assign_vendor_bill`, which appends an
  "Assign" history row, sets form_status = "Assigned", and stamps the supplier's
  department (set-once). The parent refreshes the doc + toasts on success.

  Usage:
    <AssignDepartmentModal
        v-model:visible="assignOpen"
        :name="doc.name"
        @assigned="onAssigned" />
-->
<template>
	<Dialog
		:visible="visible"
		modal
		header="Assign to Department"
		:style="{ width: '460px', maxWidth: '95vw' }"
		@update:visible="$emit('update:visible', $event)"
	>
		<div class="ad-form">
			<div class="ad-field">
				<label class="ad-label">Assigned To *</label>
				<LinkField
					v-model="department"
					target-doctype="Department"
					placeholder="Search Department…"
				/>
			</div>
			<div class="ad-field">
				<label class="ad-label">Remarks</label>
				<Textarea
					v-model="remarks"
					rows="3"
					autoResize
					fluid
					placeholder="Optional note"
				/>
			</div>
		</div>

		<template #footer>
			<Button label="Cancel" text severity="secondary" @click="close" />
			<Button
				label="Assign"
				icon="pi pi-user-plus"
				:loading="saving"
				:disabled="!department"
				@click="submit"
			/>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, watch } from "vue"
import Dialog from "primevue/dialog"
import Button from "primevue/button"
import Textarea from "primevue/textarea"
import LinkField from "@/components/LinkField.vue"
import { callMethod } from "@/api/client"
import { useAppToast } from "@/composables/useToast"

const ASSIGN = "yrp.yrp.doctype.bill_tracking.bill_tracking.assign_vendor_bill"

const props = defineProps({
	visible: { type: Boolean, default: false },
	// The Bill Tracking docname to assign.
	name: { type: String, required: true },
})
const emit = defineEmits(["update:visible", "assigned", "assigning"])
const toast = useAppToast()

const saving = ref(false)
const department = ref("")
const remarks = ref("")

// Reset the form each time the dialog opens, so a prior pick doesn't linger.
watch(
	() => props.visible,
	(open) => {
		if (open) {
			department.value = ""
			remarks.value = ""
		}
	},
)

function close() {
	emit("update:visible", false)
}

async function submit() {
	if (!department.value) {
		toast.warn("Department required", "Pick a Department to assign this bill to.")
		return
	}
	saving.value = true
	// Signal the parent BEFORE the write so it can mark this as a local write —
	// otherwise assign_vendor_bill's doc_update realtime echo races ahead and the
	// detail page raises a false "modified by another user" banner.
	emit("assigning")
	try {
		await callMethod(ASSIGN, {
			name: props.name,
			assigned_to: department.value,
			remarks: remarks.value || null,
		})
		// Parent toasts + reloads (it owns the doc); we just signal success + close.
		emit("assigned", department.value)
		emit("update:visible", false)
	} catch (e) {
		toast.error("Assign failed", e.message)
	} finally {
		saving.value = false
	}
}
</script>

<style scoped>
.ad-form {
	display: flex;
	flex-direction: column;
	gap: 14px;
}
.ad-field {
	display: flex;
	flex-direction: column;
	gap: 5px;
}
.ad-label {
	font-size: 11.5px;
	font-weight: 600;
	color: var(--mgk-muted);
}
</style>
