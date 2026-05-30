/**
 * Per-DocType field configs for the detail page.
 *
 * Each module under this folder default-exports an object:
 *   {
 *     detail?:             Array<{ fieldname, label, type? }>  // VIEW Details-tab grid
 *     formOrder?:          Array<string>                       // EDIT/CREATE field order
 *     hideFormFields?:     Array<string>                       // never render in EDIT/CREATE
 *     linkSearchHandlers?: Record<string, (form) => fn|null>   // per-Link custom search
 *   }
 *
 * Missing parts fall back to meta-driven defaults in DocDetail.vue. So a
 * DocType with no config still renders a usable detail + form page.
 *
 * Route convention matches config/doctypes.js slugify (label → kebab-case).
 */

import workOrder from "./work-order.js"
import deliveryChallan from "./delivery-challan.js"
import stockReconciliation from "./stock-reconciliation.js"
import purchaseOrder from "./purchase-order.js"
import goodsReceivedNote from "./goods-received-note.js"
import item from "./item.js"

const FIELD_CONFIGS = {
	"Work Order": workOrder,
	"Delivery Challan": deliveryChallan,
	"Stock Reconciliation": stockReconciliation,
	"Purchase Order": purchaseOrder,
	"Goods Received Note": goodsReceivedNote,
	"Item": item,
}

/**
 * VIEW Details-tab curated field list, or null to fall back to meta.
 */
export function getDetailFieldConfig(doctype) {
	return FIELD_CONFIGS[doctype]?.detail || null
}

/**
 * EDIT/CREATE field-order array (config-listed fields first, rest appended
 * by DocDetail in meta order). null means "use meta order entirely".
 */
export function getFormFieldOrder(doctype) {
	return FIELD_CONFIGS[doctype]?.formOrder || null
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
