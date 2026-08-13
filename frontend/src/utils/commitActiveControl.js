import { nextTick } from "vue"

/**
 * Commit the control currently being edited before a keyboard-triggered save.
 *
 * PrimeVue controls such as InputNumber keep a formatted value internally and
 * emit their final v-model update on blur. Clicking Save naturally causes that
 * blur; Ctrl/Cmd+S does not. Blurring here and waiting for Vue's next render
 * tick gives every form/grid editor the same payload regardless of how Save was
 * triggered.
 */
export async function commitActiveControl() {
	if (typeof document === "undefined") return
	const active = document.activeElement
	if (active && active !== document.body && typeof active.blur === "function") {
		active.blur()
	}
	await nextTick()
}
