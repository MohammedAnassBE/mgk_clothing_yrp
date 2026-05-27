/**
 * Optional per-DocType field configs for the detail page's Details tab.
 *
 * If a DocType has an entry here, DocDetail renders exactly these fields (in
 * this order, with these labels) in the field grid. If it does NOT, DocDetail
 * falls back to the DocType meta (or, if meta is unavailable, the doc's own
 * keys) — so every DocType gets a usable detail page with zero config.
 *
 * Each entry: an array of { fieldname, label, type? }.
 *   type ∈ "Date" | "Datetime" | "Currency" | "Float" | "Int" | "Check" |
 *          "Link" | "Text" | (default: plain text)
 * type only affects how the value is *formatted* in read mode.
 *
 * Route convention matches config/doctypes.js slugify (label → kebab-case).
 */

import workOrder from "./work-order.js"

const FIELD_CONFIGS = {
	"Work Order": workOrder,
}

/**
 * @param {string} doctype  e.g. "Work Order"
 * @returns {Array|null}  the field list, or null to use the meta/doc fallback.
 */
export function getFieldConfig(doctype) {
	return FIELD_CONFIGS[doctype] || null
}
