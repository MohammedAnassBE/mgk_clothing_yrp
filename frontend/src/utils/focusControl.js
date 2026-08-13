import { nextTick, unref } from "vue"

const DEFAULT_FOCUSABLE = [
	"input:not([disabled]):not([type='hidden'])",
	"textarea:not([disabled])",
	"select:not([disabled])",
	"button:not([disabled])",
	"[tabindex]:not([tabindex='-1']):not([disabled])",
].join(",")

function rootElement(value) {
	const candidate = unref(value)
	if (!candidate) return null
	if (typeof HTMLElement !== "undefined" && candidate instanceof HTMLElement) return candidate
	if (typeof HTMLElement !== "undefined" && candidate.$el instanceof HTMLElement) return candidate.$el
	return null
}

function isUsable(element) {
	if (!element || typeof element.focus !== "function") return false
	if (element.matches?.(":disabled, [aria-disabled='true'], [aria-hidden='true']")) return false
	if (element.closest?.("[hidden], [aria-hidden='true']")) return false
	return element.getClientRects?.().length > 0
}

function afterPaint() {
	if (typeof requestAnimationFrame !== "function") return Promise.resolve()
	// PrimeVue may restore focus to the originating trigger in its own first-frame
	// overlay cleanup. Wait one additional frame so the workflow continuation wins.
	return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))
}

/**
 * Focus a rendered control after Vue and PrimeVue have finished updating.
 *
 * `selector` may point at either the actual control or a wrapper carrying a
 * stable data-focus-key. When it points at a wrapper, the first usable control
 * inside it is focused. Passive loads must not call this helper: it is intended
 * only as the direct continuation of a user's add/edit/validation action.
 */
export async function focusFirstControl(root, { selector = "", scroll = true } = {}) {
	if (typeof document === "undefined") return false
	await nextTick()
	await afterPaint()

	const host = rootElement(root) || document
	const target = selector ? host.querySelector(selector) : host
	if (!target) return false
	const candidates = target.matches?.(DEFAULT_FOCUSABLE)
		? [target]
		: [...target.querySelectorAll(DEFAULT_FOCUSABLE)].filter(isUsable)
	// A whole form often starts with tab/action buttons before its actual fields.
	// For an unqualified form focus, prefer an entry control; explicit selectors
	// still focus their exact button when an action is the intended destination.
	const control = selector
		? candidates.find(isUsable)
		: candidates.find((element) => !element.matches?.("button")) || candidates[0]
	if (!isUsable(control)) return false

	if (scroll) control.scrollIntoView?.({ block: "nearest", inline: "nearest" })
	try {
		control.focus({ preventScroll: true })
	} catch (_) {
		control.focus()
	}
	if (typeof control.select === "function" && ["text", "search", "number"].includes(control.type)) {
		control.select()
	}
	return document.activeElement === control
}

export const focusableSelector = DEFAULT_FOCUSABLE
