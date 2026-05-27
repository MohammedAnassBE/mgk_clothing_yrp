<template>
	<header class="mgk-topbar">
		<span class="topbar-title">{{ pageTitle }}</span>

		<div class="topbar-right">
			<!-- Real role(s), read-only — NO switcher (plan: the user's real
			     role drives the UI). -->
			<div class="role-chip" :title="roleTitle">
				<div class="avatar">{{ initials }}</div>
				<div class="role-meta">
					<span class="role-name">{{ fullName }}</span>
					<span class="role-sub">{{ primaryRole }}</span>
				</div>
			</div>
			<Button
				icon="pi pi-sign-out"
				severity="secondary"
				text
				rounded
				aria-label="Log out"
				@click="onLogout"
			/>
		</div>
	</header>
</template>

<script setup>
import { computed } from "vue"
import { useRoute } from "vue-router"
import Button from "primevue/button"
import { useAuth } from "@/composables/useAuth"
import { getRegistryByRoute } from "@/config/doctypes"

const route = useRoute()
const { fullName, logout } = useAuth()

const bootUser = window.frappe?.boot?.user || {}
const roles = Array.isArray(bootUser.roles) ? bootUser.roles : []

// Show the most relevant business role first; fall back to first role.
const ROLE_PRIORITY = [
	"System Manager",
	"Production Manager",
	"Purchase Manager",
	"Stock Manager",
]
const primaryRole = computed(() => {
	for (const r of ROLE_PRIORITY) {
		if (roles.includes(r)) return r
	}
	return roles[0] || "User"
})
const roleTitle = computed(() => `Roles: ${roles.join(", ") || "—"}`)

const pageTitle = computed(() => {
	if (route.name === "Home") return "Home"
	const reg = getRegistryByRoute(route.params.docRoute)
	return reg?.label || route.name || ""
})

const initials = computed(() => {
	const n = (fullName.value || "U").trim()
	const parts = n.split(/\s+/)
	return parts.length >= 2
		? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
		: n.slice(0, 2).toUpperCase()
})

async function onLogout() {
	await logout()
}
</script>

<style scoped>
.mgk-topbar {
	grid-area: topbar;
	background: var(--mgk-card);
	border-bottom: 1px solid var(--mgk-line);
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 20px;
}

.topbar-title {
	font-size: 13px;
	font-weight: 600;
	color: var(--mgk-ink-2);
}

.topbar-right {
	display: flex;
	align-items: center;
	gap: 10px;
}

.role-chip {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 4px 10px 4px 4px;
	background: var(--mgk-slate-50);
	border-radius: 999px;
	user-select: none;
}

.role-chip .avatar {
	width: 28px;
	height: 28px;
	border-radius: 50%;
	background: var(--mgk-ink);
	color: #fff;
	font-weight: 600;
	font-size: 12px;
	display: grid;
	place-items: center;
}

.role-meta {
	display: flex;
	flex-direction: column;
	line-height: 1.2;
}

.role-name {
	font-weight: 600;
	font-size: 13px;
}

.role-sub {
	font-size: 11.5px;
	color: var(--mgk-muted);
}
</style>
