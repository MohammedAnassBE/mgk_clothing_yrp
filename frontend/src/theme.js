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
			// Dark Bright Workshop — activated by `.dark` on <html> (darkModeSelector).
			// Brighter teal primary for contrast; deep cool-slate surfaces (0 = card
			// ground, low numbers = backgrounds, high numbers = light text).
			dark: {
				primary: {
					color: "#2BB0A3",        // brighter teal reads on dark
					inverseColor: "#04241F",
					hoverColor: "#5EC9BE",
					activeColor: "#99DDD5",
				},
				highlight: {
					background: "rgba(45, 176, 163, 0.16)",
					focusBackground: "rgba(45, 176, 163, 0.24)",
					color: "#5EC9BE",
					focusColor: "#99DDD5",
				},
				surface: {
					0:   "#0F1A2A",   // component ground (cards, table, dialog)
					50:  "#16202F",   // row hover
					100: "#1B2636",   // header band / secondary surface
					200: "#2A3647",   // borders / lines
					300: "#3A485C",   // toggle OFF-track
					400: "#5B6573",
					500: "#94A3B8",   // muted text
					600: "#A9B4C2",
					700: "#C3CDDA",
					800: "#DCE3EC",
					900: "#EDF1F6",
					950: "#F7F9FB",   // brightest text
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
			// Token refs so the focus ring tracks the active scheme's primary.
			focusRing: { width: "2px", style: "solid", color: "{primary.color}", offset: "2px" },
		},
		datatable: {
			headerCell: {
				padding: "0.6rem 0.875rem",
				background: "{surface.100}",            // slate header band (light) / dark band (dark)
				color: "{surface.500}",
				borderColor: "{surface.200}",
				fontWeight: "600",
			},
			bodyCell: { padding: "0.65rem 0.875rem", borderColor: "{surface.200}" },
			row: { hoverBackground: "{surface.50}" },
		},
		inputtext: {
			borderRadius: "var(--radius-sm)",
			paddingX: "0.7rem", paddingY: "0.5rem",
			borderColor: "{surface.200}",
			focusBorderColor: "{primary.color}",
		},
		select:       { borderRadius: "var(--radius-sm)", borderColor: "{surface.200}", focusBorderColor: "{primary.color}" },
		datepicker:   { borderRadius: "var(--radius-sm)" },
		inputnumber:  { borderRadius: "var(--radius-sm)" },
		textarea:     { borderRadius: "var(--radius-sm)", borderColor: "{surface.200}", focusBorderColor: "{primary.color}" },
		toggleswitch: {
			checkedBackground: "{primary.color}",
			checkedHoverBackground: "{primary.hoverColor}",
			background: "{surface.300}",                 // cool grey OFF-track, adapts per scheme
		},
		tabs: {
			tab: {
				fontWeight: "500",
				activeColor: "{primary.color}",
				color: "{surface.500}",
				padding: "0.6rem 0.9rem",
			},
			activeBar: { height: "2px", background: "{primary.color}" },
		},
		tag: {
			fontWeight: "600",
			padding: "0.2rem 0.55rem",
			borderRadius: "999px",
			// Status/teal tints use --mgk-* vars (overridden under .dark in global.css).
			primary:   { background: "var(--mgk-accent-50)", color: "var(--mgk-accent-ink)" },
			info:      { background: "var(--mgk-accent-50)", color: "var(--mgk-accent-ink)" },
			success:   { background: "var(--mgk-success-50)", color: "var(--mgk-success)" },
			warn:      { background: "var(--mgk-warn-50)",    color: "var(--mgk-warn)" },
			danger:    { background: "var(--mgk-danger-50)",  color: "var(--mgk-danger)" },
			secondary: { background: "{surface.100}", color: "{surface.500}" },
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
