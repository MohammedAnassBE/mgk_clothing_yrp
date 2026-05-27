/**
 * Thin wrapper over PrimeVue's ToastService so app code keeps a stable
 * `success/error/warn/info` surface (same shape albion exposed) without
 * importing PrimeVue's `useToast` everywhere.
 */
import { useToast } from "primevue/usetoast"

export function useAppToast() {
	const toast = useToast()

	function show(severity, summary, detail, life = 4000) {
		toast.add({ severity, summary, detail, life })
	}

	return {
		success(summary, detail) {
			show("success", summary || "Success", detail)
		},
		error(summary, detail) {
			show("error", summary || "Error", detail, 6000)
		},
		warn(summary, detail) {
			show("warn", summary || "Warning", detail)
		},
		info(summary, detail) {
			show("info", summary || "Info", detail)
		},
	}
}
