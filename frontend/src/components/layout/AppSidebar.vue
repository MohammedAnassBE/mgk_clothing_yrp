<template>
	<aside class="mgk-sidebar" :class="{ pinned, 'drawer-open': drawerOpen }">
		<div class="sidebar-logo" @click="goHome">
			<div class="logo-mark">MGK</div>
			<span class="logo-text">MGK Clothing</span>
		</div>

		<nav class="sidebar-nav">
			<!-- Home (no group label) -->
			<router-link to="/home" class="nav-item" active-class="active" @click="$emit('navigate')">
				<i class="pi pi-th-large nav-icon" />
				<span class="nav-label">Home</span>
			</router-link>

			<!-- Perm-gated DocType groups -->
			<div
				v-for="grp in sidebarGroups"
				:key="grp.group"
				class="nav-group"
				:class="{ 'section-collapsed': isCollapsed(grp.group) }"
			>
				<!-- Section header: a toggle button (shown only when the rail is
				     expanded). Collapse state is per-user, persisted server-side via
				     useSidebarCollapse — independent of the rail's expand state. -->
				<button
					type="button"
					class="nav-group-label"
					:aria-expanded="!isCollapsed(grp.group)"
					@click="toggleSection(grp.group)"
				>
					<span class="nav-group-text">{{ grp.group }}</span>
					<i
						class="pi pi-chevron-down nav-group-chevron"
						:class="{ 'is-collapsed': isCollapsed(grp.group) }"
					/>
				</button>
				<router-link
					v-for="item in grp.items"
					:key="item.route"
					:to="`/${item.route}`"
					class="nav-item"
					active-class="active"
					:title="item.label"
					@click="$emit('navigate')"
				>
					<i :class="[item.icon, 'nav-icon']" />
					<span class="nav-label">{{ item.label }}</span>
				</router-link>
			</div>
		</nav>

		<div class="sidebar-foot">
			<!-- Pin keeps the rail expanded (pushes content); persisted in AppLayout. -->
			<button
				class="pin-btn"
				type="button"
				:title="pinned ? 'Unpin sidebar' : 'Pin sidebar open'"
				:aria-pressed="pinned"
				@click="$emit('toggle-pin')"
			>
				<i :class="pinned ? 'pi pi-angle-left' : 'pi pi-angle-right'" />
			</button>
			<a class="desk-link" href="/app" title="Open Frappe Desk">
				<i class="pi pi-external-link" />
				<span class="nav-label">Desk</span>
			</a>
		</div>
	</aside>
</template>

<script setup>
import { computed } from "vue"
import { useRouter } from "vue-router"
import { usePermissions } from "@/composables/usePermissions"
import { getSidebarGroups } from "@/config/doctypes"
import { useSidebarCollapse } from "@/composables/useSidebarCollapse"

defineProps({ pinned: Boolean, drawerOpen: Boolean })
const emit = defineEmits(["toggle-pin", "navigate"])

const router = useRouter()
const { canRead } = usePermissions()

// Live-perm gate: only show items the user can read. Admin sees everything;
// DocTypes not installed (e.g. Workstation) resolve canRead → false and drop.
const sidebarGroups = computed(() => getSidebarGroups((dt) => canRead(dt)))

// Per-user, server-persisted collapse state for each sidebar SECTION.
const { isCollapsed, toggleSection } = useSidebarCollapse()

function goHome() {
	emit("navigate")
	router.push("/home")
}
</script>

<style scoped>
/* Slim rail by default; expands to a flyout on hover, or stays open when pinned.
   Positioned absolutely over the grid's reserved rail column (see AppLayout) so
   the flyout overlays content instead of reflowing it. */
.mgk-sidebar {
	position: absolute;
	top: 0;
	left: 0;
	height: 100%;
	width: var(--sidebar-collapsed-width);
	background: var(--mgk-card);
	border-right: 1px solid var(--mgk-line);
	display: flex;
	flex-direction: column;
	min-height: 0;
	z-index: 20;
	overflow: hidden;
	transition: width 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}

.mgk-sidebar:hover,
.mgk-sidebar.pinned {
	width: var(--sidebar-width);
}

/* Unpinned hover = flyout overlaying content → lift it with a shadow. */
.mgk-sidebar:not(.pinned):hover {
	box-shadow: var(--mgk-shadow-pop);
}

.sidebar-logo {
	height: var(--topbar-height);
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 0 16px;
	border-bottom: 1px solid var(--mgk-line);
	cursor: pointer;
	flex-shrink: 0;
}

.logo-mark {
	width: 28px;
	height: 28px;
	border-radius: 7px;
	background: linear-gradient(135deg, var(--mgk-accent), var(--mgk-accent2));
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
}

.sidebar-nav {
	flex: 1;
	overflow-y: auto;
	overflow-x: hidden;
	padding: 10px 8px 24px;
}

.nav-group {
	padding: 2px 0 4px;
}

.nav-group-label {
	/* hidden in the slim rail; revealed (display:flex) when expanded */
	display: none;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	width: 100%;
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--mgk-muted-2);
	padding: 8px 12px 6px;
	background: transparent;
	border: 0;
	text-align: left;
	cursor: pointer;
	font-family: inherit;
}

.nav-group-label:hover {
	color: var(--mgk-ink);
}

.nav-group-text {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.nav-group-chevron {
	font-size: 10px;
	flex-shrink: 0;
	transition: transform 0.15s ease;
}

.nav-group-chevron.is-collapsed {
	transform: rotate(-90deg);
}

.nav-item {
	display: flex;
	align-items: center;
	gap: 11px;
	padding: 8px 12px;
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
	width: 18px;
	font-size: 15px;
	flex-shrink: 0;
	color: var(--mgk-muted);
	text-align: center;
}

.nav-item.active .nav-icon {
	color: var(--mgk-accent);
}

/* Labels: faded out in the slim rail, faded in when expanded (hover/pinned). */
.nav-label,
.logo-text {
	opacity: 0;
	transition: opacity 0.12s ease;
	white-space: nowrap;
}

.mgk-sidebar:hover .nav-label,
.mgk-sidebar:hover .logo-text,
.mgk-sidebar.pinned .nav-label,
.mgk-sidebar.pinned .logo-text {
	opacity: 1;
}

.mgk-sidebar:hover .nav-group-label,
.mgk-sidebar.pinned .nav-group-label {
	display: flex;
}

/* Collapsed section → hide its items, but only when the rail is expanded
   (in the slim rail every item shows as a bare icon). */
.mgk-sidebar:hover .nav-group.section-collapsed .nav-item,
.mgk-sidebar.pinned .nav-group.section-collapsed .nav-item {
	display: none;
}

/* Keyboard parity (spec: expand on hover AND focus). When focus enters the rail
   it expands and reveals labels — but we do NOT apply the section-collapse hiding
   here, so a keyboard user can tab through every item (hiding the focused item
   would blur it). */
.mgk-sidebar:focus-within {
	width: var(--sidebar-width);
}
.mgk-sidebar:not(.pinned):focus-within {
	box-shadow: var(--mgk-shadow-pop);
}
.mgk-sidebar:focus-within .nav-label,
.mgk-sidebar:focus-within .logo-text {
	opacity: 1;
}
.mgk-sidebar:focus-within .nav-group-label {
	display: flex;
}

/* overflow:hidden on the rail would clip a default focus ring — inset it. */
.nav-item:focus-visible,
.pin-btn:focus-visible,
.desk-link:focus-visible {
	outline: 2px solid var(--mgk-accent2);
	outline-offset: -2px;
	border-radius: var(--radius-sm);
}

.sidebar-foot {
	border-top: 1px solid var(--mgk-line);
	padding: 8px;
	display: flex;
	align-items: center;
	gap: 6px;
	flex-shrink: 0;
}

.pin-btn {
	background: transparent;
	border: 0;
	color: var(--mgk-muted);
	padding: 6px 9px;
	border-radius: var(--radius-sm);
	cursor: pointer;
	flex-shrink: 0;
}

.pin-btn:hover {
	background: var(--mgk-slate-50);
	color: var(--mgk-ink);
}

.desk-link {
	display: flex;
	align-items: center;
	gap: 8px;
	color: var(--mgk-muted);
	font-size: 12.5px;
	padding: 6px 9px;
	border-radius: var(--radius-sm);
}

.desk-link:hover {
	background: var(--mgk-slate-50);
	color: var(--mgk-ink);
}

/* ── Mobile: off-canvas drawer (no hover-expand) ── */
@media (max-width: 768px) {
	.mgk-sidebar {
		width: var(--sidebar-width);
		transform: translateX(-100%);
		transition: transform 0.2s ease;
		box-shadow: var(--mgk-shadow-pop);
		z-index: 30;
	}
	.mgk-sidebar.drawer-open {
		transform: translateX(0);
	}
	/* Drawer is full-width → always show labels + group headers. */
	.mgk-sidebar .nav-label,
	.mgk-sidebar .logo-text {
		opacity: 1;
	}
	.mgk-sidebar .nav-group-label {
		display: flex;
	}
	.mgk-sidebar.drawer-open .nav-group.section-collapsed .nav-item {
		display: none;
	}
}
</style>
