import { computed } from "vue"

import { useDisplayLanguage } from "@/composables/useDisplayLanguage"


function bootTerminology() {
	if (typeof window === "undefined") return {}
	return window.frappe?.boot?.ui_config?.meta?.terminology || {}
}


export function useTerminology() {
	const { isTamil } = useDisplayLanguage()
	const terms = computed(() => bootTerminology())

	function term(key, fallback = "") {
		const row = key ? terms.value?.[key] : null
		if (!row) return fallback
		if (isTamil.value && row.ta) return row.ta
		return row.source || fallback
	}

	return { term, terms }
}
