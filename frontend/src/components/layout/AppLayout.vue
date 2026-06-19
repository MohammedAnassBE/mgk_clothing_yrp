<template>
	<div class="mgk-shell" :class="{ collapsed }">
		<AppSidebar :collapsed="collapsed" @toggle="collapsed = !collapsed" />
		<AppTopbar />
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
		<CommandPalette />
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import AppSidebar from "./AppSidebar.vue"
import AppTopbar from "./AppTopbar.vue"
import CommandPalette from "@/components/CommandPalette.vue"
import { useAuth } from "@/composables/useAuth"

const collapsed = ref(false)
const { checkAuth } = useAuth()

onMounted(() => {
	checkAuth()
})
</script>

<style scoped>
.mgk-shell {
	display: grid;
	grid-template-columns: var(--sidebar-width) 1fr;
	grid-template-rows: var(--topbar-height) 1fr;
	grid-template-areas:
		"sidebar topbar"
		"sidebar main";
	height: 100vh;
}

.mgk-shell.collapsed {
	grid-template-columns: var(--sidebar-collapsed-width) 1fr;
}

.mgk-main {
	grid-area: main;
	overflow-y: auto;
	padding: 22px 28px 60px;
	background: var(--mgk-bg);
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
