/**
 * Per-DocType field configs for the detail page.
 *
 * Each module under this folder default-exports an object:
 *   {
 *     detail?:             Array<{ fieldname, label, type? }>  // VIEW Details-tab grid
 *     formOrder?:          Array<string>                       // EDIT/CREATE field order
 *     formGroups?:         Array<{label, fields: string[]}>    // EDIT/CREATE card grouping
 *     hideFormFields?:     Array<string>                       // never render in EDIT/CREATE
 *     linkSearchHandlers?: Record<string, (form) => fn|null>   // per-Link custom search
 *     labels?:             Record<string, string>              // relabel a field (overrides meta)
 *     help?:               Record<string, string>              // inline field help (overrides meta description)
 *     boolLabels?:         Record<string, {on, off}>           // Check field display words (Q20 positive display)
 *     hero?:               Array<string>                       // load-bearing fields to emphasise (Q2/Q4)
 *   }
 *
 * Missing parts fall back to meta-driven defaults in DocDetail.vue. So a
 * DocType with no config still renders a usable detail + form page.
 *
 * Route convention matches config/doctypes.js slugify (label → kebab-case).
 */

import workOrder from "./work-order.js"
import workOrderCorrection from "./work-order-correction.js"
import deliveryChallan from "./delivery-challan.js"
import stockReconciliation from "./stock-reconciliation.js"
import purchaseOrder from "./purchase-order.js"
import goodsReceivedNote from "./goods-received-note.js"
import inspectionEntry from "./inspection-entry.js"
import stockEntry from "./stock-entry.js"
import item from "./item.js"
import itemProductionDetail from "./item-production-detail.js"
import itemMasterTemplate from "./item-master-template.js"
import processCost from "./process-cost.js"
import supplier from "./supplier.js"
import mgkAgent from "./mgk-agent.js"
import warehouse from "./warehouse.js"
import itemPrice from "./item-price.js"
import user from "./user.js"
import process from "./process.js"
import receivedType from "./received-type.js"

const FIELD_CONFIGS = {
	"Work Order": workOrder,
	"Work Order Correction": workOrderCorrection,
	"Delivery Challan": deliveryChallan,
	"Stock Reconciliation": stockReconciliation,
	"Purchase Order": purchaseOrder,
	"Goods Received Note": goodsReceivedNote,
	"Inspection Entry": inspectionEntry,
	"Stock Entry": stockEntry,
	"Item": item,
	"Item Production Detail": itemProductionDetail,
	"Item Master Template": itemMasterTemplate,
	"Process Cost": processCost,
	"Supplier": supplier,
	"MGK Agent": mgkAgent,
	"Warehouse": warehouse,
	"Item Price": itemPrice,
	"User": user,
	"Process": process,
	"Received Type": receivedType,
}

/**
 * VIEW Details-tab curated field list, or null to fall back to meta.
 */
export function getDetailFieldConfig(doctype) {
	return FIELD_CONFIGS[doctype]?.detail || null
}

/**
 * Curated VIEW Details grouping: Array<{ label, key?, fields: Array<string |
 * {fieldname, label?, type?}> }>, or null to fall back to meta Section-Break
 * grouping. Use this for DocTypes whose own section structure is flat/unnamed
 * (e.g. Work Order's 26-field top section) so the Details tab still renders as
 * tidy, meaningfully-titled cards instead of one giant card. Takes precedence
 * over `detail` (single card) and meta grouping in DocDetail.detailSections.
 */
export function getDetailGroups(doctype) {
	return FIELD_CONFIGS[doctype]?.detailGroups || null
}

/**
 * EDIT/CREATE field-order array (config-listed fields first, rest appended
 * by DocDetail in meta order). null means "use meta order entirely".
 */
export function getFormFieldOrder(doctype) {
	return FIELD_CONFIGS[doctype]?.formOrder || null
}

/**
 * Optional strict allowlist for a focused form. Most DocTypes deliberately
 * return null so all meta-editable fields remain available; high-noise system
 * masters such as User opt in to a concise, operator-safe surface.
 */
export function getAllowedFormFields(doctype) {
	const fields = FIELD_CONFIGS[doctype]?.allowFormFields
	return fields?.length ? new Set(fields) : null
}

/**
 * Curated EDIT/CREATE card grouping. Fields remain meta-backed and permission /
 * depends_on aware; this only replaces confusing unnamed DocType sections with
 * workflow-language groups in a Registered Experience.
 */
export function getFormGroups(doctype) {
	return FIELD_CONFIGS[doctype]?.formGroups || null
}

/**
 * Set of fieldnames to hide from EDIT/CREATE for the given DocType.
 * Returns an empty Set when no overrides exist (so callers can `.has()` safely).
 */
export function getHiddenFormFields(doctype) {
	return new Set(FIELD_CONFIGS[doctype]?.hideFormFields || [])
}

/**
 * Custom Link search handler for one field on `doctype`. The factory closes
 * over the live `form` so calling code re-evaluates on each render — when the
 * controlling field changes (e.g. supplier), the returned handler refreshes.
 *
 * Returns null when no custom handler applies — LinkField falls back to the
 * default name-like search.
 */
export function getLinkSearchHandler(doctype, fieldname, form) {
	const factory = FIELD_CONFIGS[doctype]?.linkSearchHandlers?.[fieldname]
	if (typeof factory !== "function") return null
	return factory(form)
}

/**
 * Set of child-table fieldnames that must render as DISPLAY-ONLY in the
 * edit grid for the given parent doctype + child doctype. Empty Set when
 * no override exists. Currently used to make `Item Item Attribute.mapping`
 * non-editable: base yrp auto-creates the mapping on save, so the user
 * picking an existing one would silently share state across items.
 */
export function getReadOnlyChildFields(doctype, childDoctype) {
	const list = FIELD_CONFIGS[doctype]?.readOnlyChildFields?.[childDoctype] || []
	return new Set(list)
}

export function getHiddenChildTables(doctype) {
	return new Set(FIELD_CONFIGS[doctype]?.hideChildTables || [])
}

export function getChildColumnRules(doctype) {
	return FIELD_CONFIGS[doctype]?.childColumnRules || {}
}

// ── UX override layer (Q13/Q18/Q20/Q2) ──────────────────────────────────────
// These let the SPA relabel, help-annotate, humanise booleans, and emphasise
// fields WITHOUT touching the base-yrp DocType JSON (the plan's standing rule:
// "override yrp labels in the SPA field-config layer, not the DocType JSON").

// Site-wide defaults applied when a doctype config doesn't override the field.
// Negatively-named flags read as a double-negative ("Disabled: No"); show the
// effective state instead. Per-doctype `boolLabels` win over these.
const GLOBAL_BOOL_LABELS = {
	disabled: { on: "Disabled", off: "Active" },
	is_disabled: { on: "Disabled", off: "Active" },
}

/**
 * UX label override for one field, or null to fall back to meta label / humanize.
 * Used to unify the vendor party to a single term ("Job-worker") across WO/DC/GRN
 * and to plain-language a few engine-speak field names.
 */
export function getFieldLabel(doctype, fieldname) {
	return FIELD_CONFIGS[doctype]?.labels?.[fieldname] || null
}

/**
 * Inline help text for one field, or null. Falls back (in DocDetail) to the
 * meta `description` when no override is set.
 */
export function getFieldHelp(doctype, fieldname) {
	const help = FIELD_CONFIGS[doctype]?.help
	if (help && Object.prototype.hasOwnProperty.call(help, fieldname)) return help[fieldname]
	return null
}

/**
 * `{ on, off }` display words for a Check field, or null. Per-doctype config wins
 * over the GLOBAL_BOOL_LABELS site defaults.
 */
export function getBoolLabels(doctype, fieldname) {
	return (
		FIELD_CONFIGS[doctype]?.boolLabels?.[fieldname] ||
		GLOBAL_BOOL_LABELS[fieldname] ||
		null
	)
}

/**
 * Set of load-bearing fieldnames to emphasise in the detail cards. Empty Set
 * when none configured (safe to `.has()`).
 */
export function getHeroFields(doctype) {
	return new Set(FIELD_CONFIGS[doctype]?.hero || [])
}
