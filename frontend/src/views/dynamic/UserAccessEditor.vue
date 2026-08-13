<template>
	<div class="user-access-editor">
		<div class="access-toggle">
			<ToggleSwitch :model-value="!!enabled" @update:model-value="emit('update:enabled', $event ? 1 : 0)" />
			<div><strong>Account active</strong><small>Disabled users cannot sign in.</small></div>
		</div>

		<div class="access-field">
			<label>Role profiles</label>
			<MultiSelect
				:model-value="selectedProfiles"
				:options="roleProfileOptions"
				filter
				display="chip"
				placeholder="Choose role profiles…"
				:loading="loading"
				fluid
				@update:model-value="updateProfiles"
			/>
			<small>A profile applies its complete role set when the User is saved.</small>
		</div>

		<div class="access-field">
			<div class="role-list-head">
				<div><label>Roles</label><small>{{ selectedRoles.length }} of {{ roleOptions.length }} selected</small></div>
				<div v-if="!selectedProfiles.length" class="role-list-actions">
					<Button label="Select all" size="small" severity="secondary" text @click="selectAllRoles" />
					<Button label="Clear" size="small" severity="secondary" text @click="clearRoles" />
				</div>
			</div>
			<span class="role-search">
				<i class="pi pi-search" />
				<InputText v-model="roleSearch" placeholder="Search roles…" fluid />
			</span>
			<div class="role-checklist" :class="{ disabled: selectedProfiles.length > 0 }">
				<label v-for="role in filteredRoles" :key="role" class="role-option" :class="{ selected: selectedRoleSet.has(role) }">
					<Checkbox
						:model-value="selectedRoleSet.has(role)"
						binary
						:disabled="selectedProfiles.length > 0"
						@update:model-value="toggleRole(role, $event)"
					/>
					<span>{{ role }}</span>
				</label>
				<div v-if="!filteredRoles.length" class="role-empty">No roles match “{{ roleSearch }}”.</div>
			</div>
			<small v-if="selectedProfiles.length">These roles come from the selected Role Profile and are read-only here.</small>
			<small v-else>Check every role this user needs, as in the Frappe Desk User form.</small>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import MultiSelect from "primevue/multiselect"
import ToggleSwitch from "primevue/toggleswitch"
import Checkbox from "primevue/checkbox"
import InputText from "primevue/inputtext"
import Button from "primevue/button"
import { callMethod, getList } from "@/api/client"
import { useAppToast } from "@/composables/useToast"

const props = defineProps({
	roles: { type: Array, default: () => [] },
	roleProfiles: { type: Array, default: () => [] },
	enabled: { type: [Boolean, Number], default: 1 },
})
const emit = defineEmits(["update:roles", "update:roleProfiles", "update:enabled"])
const toast = useAppToast()
const loading = ref(false)
const roleOptions = ref([])
const roleProfileOptions = ref([])
const roleSearch = ref("")

const selectedRoles = computed(() => (props.roles || []).map((row) => row?.role).filter(Boolean))
const selectedProfiles = computed(() => (props.roleProfiles || []).map((row) => row?.role_profile).filter(Boolean))
const selectedRoleSet = computed(() => new Set(selectedRoles.value))
const filteredRoles = computed(() => {
	const query = roleSearch.value.trim().toLowerCase()
	if (!query) return roleOptions.value
	return roleOptions.value.filter((role) => role.toLowerCase().includes(query))
})

function updateRoles(values) {
	emit("update:roles", (values || []).map((role) => ({ role })))
}

async function updateProfiles(values) {
	const profiles = (values || []).map((role_profile) => ({ role_profile }))
	emit("update:roleProfiles", profiles)
	if (!profiles.length) return
	loading.value = true
	try {
		const docs = await Promise.all(profiles.map((row) => callMethod("frappe.client.get", {
			doctype: "Role Profile",
			name: row.role_profile,
		})))
		const roles = [...new Set(docs.flatMap((doc) => (doc?.roles || []).map((row) => row.role).filter(Boolean)))]
		updateRoles(roles)
	} catch (error) {
		toast.error("Could not load Role Profile", error?.message || "Try again.")
	} finally {
		loading.value = false
	}
}

function toggleRole(role, checked) {
	if (selectedProfiles.value.length) return
	const next = new Set(selectedRoles.value)
	if (checked) next.add(role)
	else next.delete(role)
	updateRoles(roleOptions.value.filter((option) => next.has(option)))
}

function selectAllRoles() {
	if (selectedProfiles.value.length) return
	updateRoles([...roleOptions.value])
}

function clearRoles() {
	if (selectedProfiles.value.length) return
	updateRoles([])
}

onMounted(async () => {
	loading.value = true
	try {
		const [roles, profiles] = await Promise.all([
			callMethod("frappe.core.doctype.user.user.get_all_roles"),
			getList("Role Profile", {
				fields: ["name"],
				order_by: "name asc",
				limit_page_length: 500,
			}).then((result) => result.data || []),
		])
		roleOptions.value = Array.isArray(roles) ? roles : []
		roleProfileOptions.value = profiles.map((row) => row.name).filter(Boolean)
	} catch (error) {
		toast.error("Could not load access options", error?.message || "Try again.")
	} finally {
		loading.value = false
	}
})
</script>

<style scoped>
.user-access-editor { display: grid; gap: 18px; }
.access-toggle { display: flex; align-items: center; gap: 12px; padding: 14px; border: 1px solid #ded5c7; border-radius: 12px; background: #fbf7ef; }
.access-toggle strong, .access-toggle small { display: block; }
.access-toggle strong { color: #1d2739; font-size: 13px; }
.access-toggle small, .access-field small { margin-top: 3px; color: #7b8492; font-size: 11.5px; line-height: 1.4; }
.access-field { display: grid; gap: 6px; }
.access-field label { color: #596273; font-size: 11px; font-weight: 750; letter-spacing: .055em; text-transform: uppercase; }
.role-list-head { display: flex; align-items: end; justify-content: space-between; gap: 12px; }
.role-list-head > div:first-child { display: grid; gap: 2px; }
.role-list-head > div:first-child small { margin: 0; }
.role-list-actions { display: flex; align-items: center; gap: 2px; }
.role-search { position: relative; display: block; }
.role-search > i { position: absolute; z-index: 1; top: 50%; left: 13px; color: #8a93a0; font-size: 12px; transform: translateY(-50%); pointer-events: none; }
.role-search :deep(input) { padding-left: 34px; }
.role-checklist { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; max-height: 410px; padding: 12px; overflow-y: auto; border: 1px solid #ded5c7; border-radius: 12px; background: #fbf7ef; }
.role-checklist.disabled { background: #f4f5f7; }
.role-option { display: flex; align-items: center; gap: 9px; min-width: 0; padding: 9px 10px; border: 1px solid #e4ddd2; border-radius: 10px; background: #fff; cursor: pointer; }
.role-option:hover { border-color: #c9b8a2; }
.role-option.selected { border-color: #8bc8bd; background: #edf8f5; }
.role-option > span { min-width: 0; overflow: hidden; color: #344054; font-size: 12px; font-weight: 650; letter-spacing: 0; text-overflow: ellipsis; text-transform: none; white-space: nowrap; }
.role-checklist.disabled .role-option { cursor: default; }
.role-empty { grid-column: 1 / -1; padding: 20px; color: #7b8492; font-size: 12px; text-align: center; }
@media (max-width: 760px) {
	.role-checklist { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 520px) {
	.role-list-head { align-items: flex-start; flex-direction: column; }
	.role-checklist { grid-template-columns: 1fr; }
}
</style>
