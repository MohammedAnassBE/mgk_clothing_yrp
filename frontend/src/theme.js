/**
 * MGK Clothing PrimeVue preset — slate + emerald identity.
 *
 * Built on Aura. The `primary` ramp is emerald (the accent in
 * `custom ui/MGK_WEB.html` — #0F766E deep emerald, #115E59 darker).
 * Surfaces stay light/warm-neutral (slate-tinted) to match the mockup's
 * off-white page + white cards. Components (Button, DataTable, Tabs,
 * Paginator…) inherit these tokens automatically.
 */
import { definePreset } from "@primeuix/themes"
import Aura from "@primeuix/themes/aura"

const MgkPreset = definePreset(Aura, {
	semantic: {
		// Emerald primary ramp (PrimeUIX emerald palette values).
		primary: {
			50: "#ecfdf5",
			100: "#d0fae5",
			200: "#a4f4cf",
			300: "#5ee9b5",
			400: "#00d492",
			500: "#00bc7d",
			600: "#009966",
			700: "#0F766E",
			800: "#115E59",
			900: "#134e4a",
			950: "#032826",
		},
		colorScheme: {
			light: {
				primary: {
					color: "#0F766E",
					inverseColor: "#ffffff",
					hoverColor: "#115E59",
					activeColor: "#0c4a45",
				},
				highlight: {
					background: "#E7F4F2",
					focusBackground: "#d2ebe7",
					color: "#115E59",
					focusColor: "#115E59",
				},
				// Warm-neutral / slate surfaces to match the mockup.
				surface: {
					0: "#ffffff",
					50: "#FAF8F3",
					100: "#F4F1EB",
					200: "#E5E1D8",
					300: "#D7D2C6",
					400: "#B8B2A4",
					500: "#9AA1AC",
					600: "#6B7280",
					700: "#475569",
					800: "#334155",
					900: "#1F2937",
					950: "#0B1220",
				},
			},
		},
	},
	components: {
		// Slightly denser tables to match the mockup's compact list rows.
		datatable: {
			headerCell: {
				padding: "0.6rem 0.875rem",
			},
			bodyCell: {
				padding: "0.65rem 0.875rem",
			},
		},
	},
})

export default MgkPreset
