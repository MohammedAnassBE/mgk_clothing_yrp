<template>
	<main class="experience-host">
		<component
			v-if="registration"
			:is="registration.component"
			v-bind="experienceProps"
		/>
		<section v-else class="experience-error" role="alert">
			<i class="pi pi-exclamation-triangle" />
			<h1>Experience unavailable</h1>
			<p>The assigned experience is not registered in this application build.</p>
		</section>
	</main>
</template>

<script setup>
import { computed } from "vue"
import { getRegisteredExperience } from "./index"

const uiConfig = window.frappe?.boot?.ui_config || {}
const registration = getRegisteredExperience(uiConfig.meta?.experience_key)
const configuredProps = uiConfig.config?.experience_props || {}
const experienceProps = computed(() =>
	registration?.mapProps ? registration.mapProps(configuredProps) : {}
)
</script>

<style scoped>
.experience-host {
	min-height: 100vh;
	background: var(--mgk-bg);
}

.experience-error {
	max-width: 520px;
	margin: 12vh auto 0;
	padding: 32px;
	text-align: center;
	color: var(--mgk-ink);
	background: var(--mgk-card);
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius-lg);
	box-shadow: var(--mgk-shadow-card);
}

.experience-error .pi {
	font-size: 28px;
	color: var(--mgk-warning);
}

.experience-error h1 {
	margin: 14px 0 8px;
}

.experience-error p {
	margin: 0;
	color: var(--mgk-muted);
}

</style>
