import { defineAsyncComponent } from "vue"

// Static, build-time allowlist. UI Layout stores only one of these safe keys;
// it can never import a database-provided component path.
const experiences = Object.freeze({
	"operations-workspace": {
		component: defineAsyncComponent(() =>
			import("./operations-workspace/OperationsWorkspaceExperience.vue")
		),
	},
})

export function getRegisteredExperience(key) {
	return experiences[key] || null
}
