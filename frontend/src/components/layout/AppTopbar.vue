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
				:icon="isDark ? 'pi pi-sun' : 'pi pi-moon'"
				severity="secondary"
				text
				rounded
				:aria-label="isDark ? 'Switch to light theme' : 'Switch to dark theme'"
				:title="isDark ? 'Light mode' : 'Dark mode'"
				@click="toggleTheme"
			/>
			<Button
				icon="pi pi-sign-out"
				severity="secondary"
				text
				rounded
				aria-label="Log out"
				title="Log out"
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
import { useTheme } from "@/composables/useTheme"
import { getRegistryByRoute } from "@/config/doctypes"

const route = useRoute()
const { fullName, logout } = useAuth()
const { isDark, toggleTheme } = useTheme()

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

// Q3: readable titles for the specialized rich-flow routes (their route.name is
// camelCase like "ProcessMatrix", which leaked into the topbar). Generic
// list/detail routes resolve to the DocType label via the registry.
const ROUTE_TITLES = {
	Home: "Home",
	IPDCreate: "New Item Production Detail",
	IPDEditFields: "Edit Item Production Detail",
	IPDConfig: "Item Production Detail",
	ProcessMatrix: "Process Matrix",
	BOMMapping: "Item BOM Mapping",
	ProductionOrder: "Production Order",
}

const pageTitle = computed(() => {
	const reg = getRegistryByRoute(route.params.docRoute)
	if (reg) return reg.label
	return ROUTE_TITLES[route.name] || route.name || ""
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
	/* Teal (brand) so initials stay legible in both light and dark — the old
	   --mgk-ink bg inverted to near-white in dark, hiding white initials. */
	background: var(--mgk-accent);
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
