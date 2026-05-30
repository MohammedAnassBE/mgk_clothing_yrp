/**
 * Stock Reconciliation — per-DocType field config.
 *
 * Mirrors yrp's Supplier+Warehouse pair rule (conventions.md 2026-05-23 +
 * 2026-05-29): `default_warehouse` filters to warehouses belonging to
 * `default_supplier`. Returns null when the party is empty so the LinkField
 * falls through to listing all warehouses — the user can still pick freely.
 */
import { searchLink } from "@/api/client"

const linkSearchHandlers = {
	default_warehouse: (form) =>
		form.default_supplier
			? (q) => searchLink("Warehouse", q, { supplier: form.default_supplier })
			: null,
}

export default {
	linkSearchHandlers,
}
