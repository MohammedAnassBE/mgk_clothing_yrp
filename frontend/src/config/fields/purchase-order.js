/**
 * Purchase Order — per-DocType field config.
 *
 * Mirrors yrp's Supplier+Warehouse pair rule (conventions.md 2026-05-23 +
 * 2026-05-29): `delivery_warehouse` filters to warehouses belonging to
 * `supplier`. Returns null when the party is empty so the LinkField falls
 * through to listing all warehouses.
 */
import { searchLink } from "@/api/client"

const linkSearchHandlers = {
	delivery_warehouse: (form) =>
		form.supplier
			? (q) => searchLink("Warehouse", q, { supplier: form.supplier })
			: null,
}

export default {
	linkSearchHandlers,
}
