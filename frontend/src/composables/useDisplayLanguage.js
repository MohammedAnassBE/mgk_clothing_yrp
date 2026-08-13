import { computed, ref } from "vue"

const ENGLISH = "en"
const TAMIL = "ta"
const SUPPORTED_LANGUAGES = new Set([ENGLISH, TAMIL])

function currentUser() {
	if (typeof window === "undefined") return "Guest"
	return window.frappe?.boot?.user?.name || window.frappe?.session?.user || "Guest"
}

function storageKey() {
	return `mgk-display-language:${currentUser()}`
}

function storedLanguage() {
	if (typeof window === "undefined") return ENGLISH
	try {
		const value = window.localStorage.getItem(storageKey())
		return SUPPORTED_LANGUAGES.has(value) ? value : ENGLISH
	} catch (_) {
		return ENGLISH
	}
}

// Module-level state is deliberate: the top-bar toggle, Link fields, lists,
// specialized editors and saved-document views must all switch in the same
// render without copying the persisted Link value or reloading the page.
const language = ref(storedLanguage())
const isTamil = computed(() => language.value === TAMIL)

function setLanguage(value) {
	const next = SUPPORTED_LANGUAGES.has(value) ? value : ENGLISH
	language.value = next
	if (typeof window === "undefined") return
	try {
		window.localStorage.setItem(storageKey(), next)
	} catch (_) {
		// A blocked/disabled localStorage must not prevent the display switch for
		// the current session.
	}
}

export function useDisplayLanguage() {
	return {
		language,
		isTamil,
		setLanguage,
		ENGLISH,
		TAMIL,
	}
}
