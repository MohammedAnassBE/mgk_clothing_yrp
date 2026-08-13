/**
 * Item Production Detail — per-DocType field config consumed by DocDetail.vue.
 *
 * `linkSearchHandlers`: the top-level `yarn_item` Link → Item field must only
 * offer items flagged as yarn (desk-side Check `is_yarn_item`, added 2026-06-18).
 * Mirrors the delivery-challan.js pattern: the factory returns an async
 * `(query) => Array<{ name }>` that restricts the Item search with the
 * `{ is_yarn_item: 1 }` filter (applied as an AND condition by the backend
 * link_search). There is no controlling field, so the handler is unconditional.
 *
 * NOTE: as of this change `yarn_item` is a top-level Link field on the IPD
 * DocType. The rich IPDConfigView editor renders a curated set of fields and
 * may not surface `yarn_item` yet; the generic DocDetail editor renders meta
 * Link fields, so the handler applies wherever the field is shown. Keeping the
 * handler here means the filter is correct the moment the field becomes visible
 * on either surface.
 */
import { searchLink } from "@/api/client"

const linkSearchHandlers = {
	item: () => (q) => searchLink("Item", q, { disabled: 0 }),
	yarn_item: () => (q) => searchLink("Item", q, { is_yarn_item: 1 }),
}

export default {
	formOrder: ["item"],
	labels: {
		item: "Finished Item",
	},
	help: {
		item: "Select the finished Item. Its attributes and values are loaded automatically.",
	},
	linkSearchHandlers,
}
