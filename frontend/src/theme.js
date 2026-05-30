/**
 * MGK Clothing PrimeVue preset — teal identity / cool slate surfaces.
 *
 * Built on Aura. The `primary` ramp is the Bright Workshop teal anchored on
 * #0D9488 (--mgk-accent), so every Button CTA, status Tag, and highlight
 * inherits the teal identity. Surfaces are the cool slate ramp (#F6F8FA page
 * + white cards) — no warm/cream tints. Components (Button, DataTable, Tabs,
 * Paginator…) inherit these tokens automatically.
 */
import { definePreset } from "@primeuix/themes"
import Aura from "@primeuix/themes/aura"

const MgkPreset = definePreset(Aura, {
	semantic: {
		// Bright Workshop teal primary ramp, anchored on #0D9488.
		primary: {
			50:  "#E6F6F4",
			100: "#CCEEEA",
			200: "#99DDD5",
			300: "#5EC9BE",
			400: "#2BB0A3",
			500: "#0D9488",   // --mgk-accent
			600: "#0F827A",   // --mgk-accent-600
			700: "#0F766E",   // --mgk-accent-700
			800: "#115E59",
			900: "#134E4A",
			950: "#032826",
		},
		colorScheme: {
			light: {
				primary: {
					color: "#0D9488",
					inverseColor: "#ffffff",
					hoverColor: "#0F827A",
					activeColor: "#0F766E",
				},
				highlight: {
					background: "#E6F6F4",
					focusBackground: "#CCEEEA",
					color: "#0F766E",
					focusColor: "#0F766E",
				},
				// Cool slate surfaces (Bright Workshop) — no warm/cream tints.
				surface: {
					0:   "#ffffff",
					50:  "#F6F8FA",   // --mgk-bg
					100: "#EEF2F7",   // --mgk-slate-50
					200: "#E2E8F0",   // --mgk-line
					300: "#CBD5E1",
					400: "#94A3B8",   // --mgk-muted-2
					500: "#64748B",
					600: "#5B6573",   // --mgk-muted
					700: "#475569",
					800: "#1E293B",   // --mgk-ink-2
					900: "#0F172A",
					950: "#0B1220",   // --mgk-ink
				},
			},
		},
	},
	components: {
		button: {
			root: { borderRadius: "var(--radius-sm)" },
			paddingX: "0.85rem",
			paddingY: "0.5rem",
			sm: { paddingX: "0.7rem", paddingY: "0.4rem", fontSize: "0.8125rem" },
			label: { fontWeight: "600" },
			focusRing: { width: "2px", style: "solid", color: "#0D9488", offset: "2px" },
		},
		datatable: {
			headerCell: {
				padding: "0.6rem 0.875rem",
				background: "#EEF2F7",                 // slate-50 header band
				color: "#5B6573",
				borderColor: "#E2E8F0",
				fontWeight: "600",
			},
			bodyCell: { padding: "0.65rem 0.875rem", borderColor: "#E2E8F0" },
			row: { hoverBackground: "#F6F8FA" },
		},
		inputtext: {
			borderRadius: "var(--radius-sm)",
			paddingX: "0.7rem", paddingY: "0.5rem",
			borderColor: "#E2E8F0",
			focusBorderColor: "#0D9488",
		},
		select:       { borderRadius: "var(--radius-sm)", borderColor: "#E2E8F0", focusBorderColor: "#0D9488" },
		datepicker:   { borderRadius: "var(--radius-sm)" },
		inputnumber:  { borderRadius: "var(--radius-sm)" },
		textarea:     { borderRadius: "var(--radius-sm)", borderColor: "#E2E8F0", focusBorderColor: "#0D9488" },
		toggleswitch: {
			checkedBackground: "#0D9488",
			checkedHoverBackground: "#0F827A",
			background: "#CBD5E1",                       // cool grey OFF-track (kills the tan)
		},
		tabs: {
			tab: {
				fontWeight: "500",
				activeColor: "#0F766E",
				color: "#5B6573",
				padding: "0.6rem 0.9rem",
			},
			activeBar: { height: "2px", background: "#0D9488" },
		},
		tag: {
			fontWeight: "600",
			padding: "0.2rem 0.55rem",
			borderRadius: "999px",
			primary:   { background: "#E6F6F4", color: "#0F766E" },
			info:      { background: "#E6F6F4", color: "#0F766E" },   // fold off-palette blue into teal
			success:   { background: "var(--mgk-success-50)", color: "var(--mgk-success)" },
			warn:      { background: "var(--mgk-warn-50)",    color: "var(--mgk-warn)" },
			danger:    { background: "var(--mgk-danger-50)",  color: "var(--mgk-danger)" },
			secondary: { background: "#EEF2F7", color: "#5B6573" },
		},
		dialog: {
			borderRadius: "var(--radius)",
			headerPadding: "1rem 1.25rem",
			contentPadding: "0 1.25rem 1.25rem",
		},
		card: { borderRadius: "var(--radius)", body: { padding: "0" } },
		paginator: { padding: "0.5rem 0.75rem" },
	},
})

export default MgkPreset
