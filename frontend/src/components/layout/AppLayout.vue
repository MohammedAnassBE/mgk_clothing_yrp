<template>
	<div class="mgk-shell" :class="{ pinned, 'drawer-open': drawerOpen }">
		<!-- Reserves the rail's width in the grid; the real sidebar is positioned
		     absolutely over it so it can expand into a flyout without reflowing. -->
		<div class="rail-spacer" aria-hidden="true" />
		<AppSidebar
			:pinned="pinned"
			:drawer-open="drawerOpen"
			@toggle-pin="togglePin"
			@navigate="drawerOpen = false"
		/>
		<AppTopbar @toggle-drawer="drawerOpen = !drawerOpen" />
		<main class="mgk-main">
			<!-- Key by path so each DocType/record gets a fresh instance — the
			     dynamic views capture their doctype at setup (useDoc/useDocList),
			     so reusing the instance across routes would load stale data. -->
			<router-view v-slot="{ Component }">
				<transition name="route-fade" mode="out-in">
					<component :is="Component" :key="$route.path" />
				</transition>
			</router-view>
		</main>
		<!-- Mobile drawer scrim (closes the drawer on tap). -->
		<div class="mgk-scrim" @click="drawerOpen = false" />
		<CommandPalette />
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import AppSidebar from "./AppSidebar.vue"
import AppTopbar from "./AppTopbar.vue"
import CommandPalette from "@/components/CommandPalette.vue"
import { useAuth } from "@/composables/useAuth"

// Rail is slim by default (hover to expand); "pin" keeps it expanded and pushes
// content. Persisted per-browser so a user's preference survives reloads.
const PIN_KEY = "mgk.sidebar.pinned"
const pinned = ref(localStorage.getItem(PIN_KEY) === "1")
const drawerOpen = ref(false)

function togglePin() {
	pinned.value = !pinned.value
	localStorage.setItem(PIN_KEY, pinned.value ? "1" : "0")
}

const { checkAuth } = useAuth()
onMounted(() => {
	checkAuth()
})
</script>

<style scoped>
.mgk-shell {
	position: relative;
	display: grid;
	grid-template-columns: var(--rail-w) 1fr;
	grid-template-rows: var(--topbar-height) 1fr;
	grid-template-areas:
		"rail topbar"
		"rail main";
	height: 100vh;
	--rail-w: var(--sidebar-collapsed-width);
}

/* Pinned → grid reserves the full sidebar width; content is pushed (no overlay). */
.mgk-shell.pinned {
	--rail-w: var(--sidebar-width);
}

.rail-spacer {
	grid-area: rail;
}

.mgk-main {
	grid-area: main;
	overflow-y: auto;
	padding: 22px 28px 60px;
	background: var(--mgk-bg);
}

/* Scrim only exists on mobile when the drawer is open. */
.mgk-scrim {
	display: none;
}

@media (max-width: 768px) {
	.mgk-shell {
		grid-template-columns: 1fr;
		grid-template-areas:
			"topbar"
			"main";
		--rail-w: 0px;
	}
	.rail-spacer {
		display: none;
	}
	.mgk-shell.drawer-open .mgk-scrim {
		display: block;
		position: fixed;
		inset: 0;
		background: rgb(var(--c-ink) / 0.42);
		z-index: 25;
	}
}

/* Subtle cross-fade between routes so navigation feels smooth, not a hard cut.
   Short + opacity-only so it never delays interaction. */
.route-fade-enter-active,
.route-fade-leave-active {
	transition: opacity 0.15s ease;
}
.route-fade-enter-from,
.route-fade-leave-to {
	opacity: 0;
}
</style>
