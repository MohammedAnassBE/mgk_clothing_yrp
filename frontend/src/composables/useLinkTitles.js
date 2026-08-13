/**
 * Resolve canonical Frappe Link values to their user-facing English/Tamil
 * master names. The Link value is never replaced: only the rendered label
 * follows the MGK header language toggle.
 */
import { reactive } from "vue"
import { getList, getMeta } from "@/api/client"
import { useDisplayLanguage } from "@/composables/useDisplayLanguage"

export const LOCALIZED_NAME_FIELDS = Object.freeze({
	Item: { english: "name1", tamil: "mgk_tamil_name" },
	Supplier: { english: "supplier_name", tamil: "mgk_tamil_name" },
	Warehouse: { english: "name1", tamil: "mgk_tamil_name" },
	"MGK Agent": { english: "agent_name", tamil: "mgk_tamil_name" },
})

// `${doctype}::${name}` → { english, tamil } or null (resolved, no title).
// undefined means not resolved yet. This module-level cache is shared by every
// list, detail, popup and editor in the Registered Experience.
const titleCache = reactive({})
const titleFieldCache = reactive({})
const inflight = {}
const pending = {}
let pendingScheduled = false

const { isTamil } = useDisplayLanguage()

function key(doctype, name) {
	return `${doctype}::${name}`
}

function localizedFields(doctype) {
	return LOCALIZED_NAME_FIELDS[doctype] || null
}

async function resolveTitleFields(doctype) {
	if (doctype in titleFieldCache) return titleFieldCache[doctype]
	if (localizedFields(doctype)) {
		titleFieldCache[doctype] = localizedFields(doctype)
		return titleFieldCache[doctype]
	}
	try {
		const bundle = await getMeta(doctype)
		const parent = Array.isArray(bundle) ? bundle[0] : null
		const field = parent?.title_field || ""
		titleFieldCache[doctype] = {
			english: field && field !== "name" ? field : "",
			tamil: "",
		}
	} catch (_) {
		titleFieldCache[doctype] = { english: "", tamil: "" }
	}
	return titleFieldCache[doctype]
}

function remember(doctype, rows) {
	if (!doctype) return
	for (const row of rows || []) {
		if (!row?.name) continue
		const english = row.label_en || row.label || row.name
		const tamil = row.label_ta || ""
		titleCache[key(doctype, row.name)] = {
			english: String(english || row.name),
			tamil: String(tamil || ""),
		}
	}
}
async function prime(pairs) {
	const byDoctype = {}
	for (const { doctype, name } of pairs || []) {
		if (!doctype || !name) continue
		if (key(doctype, name) in titleCache) continue
		;(byDoctype[doctype] ||= new Set()).add(String(name))
	}

	await Promise.all(
		Object.entries(byDoctype).map(async ([doctype, nameSet]) => {
			const names = [...nameSet]
			const fields = await resolveTitleFields(doctype)
			if (!fields.english && !fields.tamil) {
				for (const name of names) titleCache[key(doctype, name)] = null
				return
			}

			const flightKey = `${doctype}::${names.slice().sort().join(",")}`
			if (!inflight[flightKey]) {
				const requestedFields = ["name", fields.english, fields.tamil].filter(Boolean)
				inflight[flightKey] = getList(doctype, {
					fields: [...new Set(requestedFields)],
					filters: [["name", "in", names]],
					limit_page_length: names.length,
				})
					.then(({ data }) => {
						const found = new Set()
						for (const row of data || []) {
							const english = (fields.english && row[fields.english]) || row.name
							const tamil = (fields.tamil && row[fields.tamil]) || ""
							titleCache[key(doctype, row.name)] = {
								english: String(english || row.name),
								tamil: String(tamil || ""),
							}
							found.add(String(row.name))
						}
						for (const name of names) {
							if (!found.has(name)) titleCache[key(doctype, name)] = null
						}
					})
					.catch(() => {
						// Do not negative-cache transient failures; a later render retries.
					})
					.finally(() => {
						delete inflight[flightKey]
					})
			}
			await inflight[flightKey]
		}),
	)
}

// Specialized tables do not all have an explicit lifecycle hook. A cache miss
// queues one microtask-batched fetch, so calling titleFor() in any template is
// sufficient and never creates one API request per cell.
function queuePrime(doctype, name) {
	if (!doctype || !name || key(doctype, name) in titleCache) return
	;(pending[doctype] ||= new Set()).add(String(name))
	if (pendingScheduled) return
	pendingScheduled = true
	Promise.resolve().then(() => {
		pendingScheduled = false
		const pairs = Object.entries(pending).flatMap(([target, names]) => {
			delete pending[target]
			return [...names].map((value) => ({ doctype: target, name: value }))
		})
		prime(pairs)
	})
}

function titlesFor(doctype, name) {
	if (!doctype || !name) return null
	const cacheKey = key(doctype, name)
	if (!(cacheKey in titleCache)) queuePrime(doctype, name)
	return titleCache[cacheKey] || null
}

function englishTitleFor(doctype, name) {
	return titlesFor(doctype, name)?.english || null
}

function tamilTitleFor(doctype, name) {
	return titlesFor(doctype, name)?.tamil || null
}

function titleFor(doctype, name) {
	const titles = titlesFor(doctype, name)
	if (!titles) return null
	return (isTamil.value && titles.tamil) || titles.english || null
}

function linkParts(doctype, name, siblingEnglish = "", siblingTamil = "") {
	const code = name == null ? "" : String(name)
	const cached = titlesFor(doctype, name)
	const english = String(siblingEnglish || cached?.english || "")
	const tamil = String(siblingTamil || cached?.tamil || "")
	const human = (isTamil.value && tamil) || english || code

	// In Tamil mode an available Tamil master name is the complete display label,
	// as requested. The canonical code remains in the model and link URL.
	if (isTamil.value && tamil) return { primary: tamil, code: "" }
	if (human && human !== code) return { primary: human, code }
	return { primary: code, code: "" }
}

function suggestionLabel(row) {
	if (!row) return ""
	return (isTamil.value && row.label_ta) || row.label_en || row.label || row.name || ""
}

export function useLinkTitles() {
	return {
		prime,
		remember,
		titleFor,
		englishTitleFor,
		tamilTitleFor,
		linkParts,
		suggestionLabel,
		isLocalizedDoctype: (doctype) => !!localizedFields(doctype),
	}
}
