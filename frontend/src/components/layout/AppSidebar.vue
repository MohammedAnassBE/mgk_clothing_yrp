<template>
	<aside class="mgk-sidebar" :class="{ collapsed }">
		<div class="sidebar-logo" @click="$router.push('/home')">
			<div class="logo-mark">MGK</div>
			<span v-if="!collapsed" class="logo-text">MGK Clothing</span>
		</div>

		<nav class="sidebar-nav">
			<!-- Home (no group label) -->
			<router-link to="/home" class="nav-item" active-class="active">
				<i class="pi pi-th-large nav-icon" />
				<span v-if="!collapsed">Home</span>
			</router-link>

			<!-- Perm-gated DocType groups -->
			<div v-for="grp in sidebarGroups" :key="grp.group" class="nav-group">
				<span v-if="!collapsed" class="nav-group-label">{{ grp.group }}</span>
				<router-link
					v-for="item in grp.items"
					:key="item.route"
					:to="`/${item.route}`"
					class="nav-item"
					active-class="active"
					:title="item.label"
				>
					<i :class="[item.icon, 'nav-icon']" />
					<span v-if="!collapsed">{{ item.label }}</span>
				</router-link>
			</div>
		</nav>

		<div class="sidebar-foot">
			<button class="collapse-btn" :title="collapsed ? 'Expand' : 'Collapse'" @click="$emit('toggle')">
				<i :class="collapsed ? 'pi pi-angle-right' : 'pi pi-angle-left'" />
			</button>
			<span class="spacer" />
			<a v-if="!collapsed" class="desk-link" href="/app" title="Open Frappe Desk">
				<i class="pi pi-external-link" /> Desk
			</a>
		</div>
	</aside>
</template>

<script setup>
import { computed } from "vue"
import { usePermissions } from "@/composables/usePermissions"
import { getSidebarGroups } from "@/config/doctypes"

defineProps({ collapsed: Boolean })
defineEmits(["toggle"])

const { canRead } = usePermissions()

// Live-perm gate: only show items the user can read. Admin sees everything;
// DocTypes not installed (e.g. Workstation) resolve canRead → false and drop.
const sidebarGroups = computed(() => getSidebarGroups((dt) => canRead(dt)))
</script>

<style scoped>
.mgk-sidebar {
	grid-area: sidebar;
	background: var(--mgk-card);
	border-right: 1px solid var(--mgk-line);
	display: flex;
	flex-direction: column;
	min-height: 0;
}

.sidebar-logo {
	height: var(--topbar-height);
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 0 16px;
	border-bottom: 1px solid var(--mgk-line);
	cursor: pointer;
}

.logo-mark {
	width: 28px;
	height: 28px;
	border-radius: 7px;
	background: linear-gradient(135deg, var(--mgk-accent), var(--mgk-accent-700));
	color: #fff;
	font-weight: 700;
	font-size: 11px;
	display: grid;
	place-items: center;
	flex-shrink: 0;
}

.logo-text {
	font-weight: 600;
	letter-spacing: -0.01em;
	white-space: nowrap;
}

.sidebar-nav {
	flex: 1;
	overflow-y: auto;
	padding: 12px 8px 24px;
}

.nav-group {
	padding: 4px 0 6px;
}

.nav-group-label {
	display: block;
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--mgk-muted-2);
	padding: 8px 12px 6px;
}

.nav-item {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 7px 12px 7px 14px;
	border-radius: var(--radius-sm);
	color: var(--mgk-ink-2);
	font-size: 13.5px;
	border-left: 3px solid transparent;
	margin: 1px 0;
	white-space: nowrap;
}

.nav-item:hover {
	background: var(--mgk-slate-50);
}

.nav-item.active {
	background: var(--mgk-accent-50);
	color: var(--mgk-accent-700);
	border-left-color: var(--mgk-accent);
	font-weight: 600;
}

.nav-icon {
	width: 16px;
	font-size: 14px;
	flex-shrink: 0;
	color: var(--mgk-muted);
}

.nav-item.active .nav-icon {
	color: var(--mgk-accent);
}

.collapsed .nav-group-label,
.collapsed .nav-item span,
.collapsed .logo-text {
	display: none;
}

.collapsed .nav-item {
	justify-content: center;
	padding: 9px 0;
}

.sidebar-foot {
	border-top: 1px solid var(--mgk-line);
	padding: 10px 12px;
	display: flex;
	align-items: center;
	gap: 8px;
}

.collapse-btn {
	background: transparent;
	border: 0;
	color: var(--mgk-muted);
	padding: 4px 8px;
	border-radius: var(--radius-sm);
	cursor: pointer;
}

.collapse-btn:hover {
	background: var(--mgk-slate-50);
	color: var(--mgk-ink);
}

.spacer {
	flex: 1;
}

.desk-link {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	color: var(--mgk-muted);
	font-size: 12.5px;
	padding: 4px 8px;
	border-radius: var(--radius-sm);
}

.desk-link:hover {
	background: var(--mgk-slate-50);
	color: var(--mgk-ink);
}
</style>
