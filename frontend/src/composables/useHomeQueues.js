/**
 * MGK Clothing — Home "My Work Today" work-queues.
 *
 * Four operational queues, each rendered as a clickable card on HomePage that
 * deep-links to its DocType list pre-filtered to the same condition. Counts are
 * fetched live (frappe.client.get_count) in parallel and degrade to "—" on
 * error so the home never crashes.
 *
 * Each queue descriptor:
 *   { key, label, sub, icon, tone, doctype, filters, route, count, error }
 * where `filters` is the deep-link filter as a JSON array of [field, op, value]
 * triples — the exact shape DynamicListPage's `?filters=` base filter parses.
 *
 * Queue 1 (Design Approvals Pending) is two-step: the gated process list comes
 * from MGK Settings → process_approval_roles[].process_name. If that list is
 * empty the queue is a guaranteed 0 (no Work Order query is issued) and the
 * deep-link is harmless.
 *
 * Tones map to coloured square icons in HomePage (amber / info / emerald /
 * slate). Visibility is gated per-queue on canRead(doctype) by the caller.
 */

import { reactive, ref } from "vue"
import { getCount, callMethod } from "@/api/client"
import { usePermissions } from "@/composables/usePermissions"
import { getRegistryByDoctype } from "@/config/doctypes"

// get_count takes a {field: value} object filter; the cards deep-link with the
// array-of-triples form. Convert one to the other so a single source of truth
// (the triples) drives both the count and the URL.
function triplesToObject(triples) {
	const obj = {}
	for (const [field, op, value] of triples) {
		obj[field] = [op, value]
	}
	return obj
}

export function useHomeQueues() {
	const { canRead } = usePermissions()

	// Static queue definitions. `filters` is the deep-link/base-filter triples.
	// Queue 1's process_name `in` clause is filled at load time from MGK Settings.
	const queues = reactive([
		{
			key: "design-approvals",
			label: "Design Approvals Pending",
			sub: "Draft Work Orders awaiting sign-off",
			icon: "pi pi-flag",
			tone: "amber",
			doctype: "Work Order",
			filters: [
				["docstatus", "=", 0],
				["approved_by", "is", "not set"],
				["process_name", "in", []],
			],
			count: null, // null = still loading / unknown; rendered as "—"
			error: false,
		},
		{
			key: "pending-inspections",
			label: "Pending Inspections",
			sub: "Inspection Entries not yet converted",
			icon: "pi pi-verified",
			tone: "info",
			doctype: "Inspection Entry",
			filters: [["is_converted", "=", 0]],
			count: null,
			error: false,
		},
		{
			key: "vendor-bills",
			label: "Vendor Bills Pending",
			sub: "Open / assigned / reopened bills",
			icon: "pi pi-indian-rupee",
			tone: "emerald",
			doctype: "Bill Tracking",
			filters: [["form_status", "in", ["Open", "Assigned", "Reopen"]]],
			count: null,
			error: false,
		},
		{
			key: "open-work-orders",
			label: "Open Work Orders",
			sub: "Submitted, not closed or cancelled",
			icon: "pi pi-bars",
			tone: "slate",
			doctype: "Work Order",
			filters: [
				["docstatus", "=", 1],
				["status", "not in", ["Closed", "Cancelled"]],
			],
			count: null,
			error: false,
		},
	])

	const loading = ref(false)

	// Resolve route slug per queue (used by the card to navigate). Computed once.
	for (const q of queues) {
		q.route = getRegistryByDoctype(q.doctype)?.route || ""
	}

	// Visible queues = those the user can read. The caller renders only these.
	function visibleQueues() {
		return queues.filter((q) => canRead(q.doctype))
	}

	// Fetch the gated-process list for queue 1. Returns [] on any failure (a WO
	// site with no configured gates simply shows 0 — never an error card).
	async function loadGatedProcesses() {
		try {
			const settings = await callMethod("frappe.client.get", {
				doctype: "MGK Settings",
				name: "MGK Settings",
			})
			const rows = settings?.process_approval_roles || []
			return rows.map((r) => r.process_name).filter((p) => !!p)
		} catch (_) {
			return []
		}
	}

	// Load counts for every readable queue in parallel. Each count is isolated:
	// one failing query shows "—" on that card only.
	async function loadCounts() {
		loading.value = true
		const targets = visibleQueues()

		// Queue 1 first needs the gated process list (only if it is visible).
		const designQ = queues.find((q) => q.key === "design-approvals")
		if (designQ && targets.includes(designQ)) {
			const gated = await loadGatedProcesses()
			// Inject into the `process_name in [...]` triple so the deep-link and
			// the count share the same gated list.
			const triple = designQ.filters.find((t) => t[0] === "process_name")
			if (triple) triple[2] = gated
			if (gated.length === 0) {
				// No gated processes → guaranteed zero; skip the WO query entirely.
				designQ.count = 0
				designQ.error = false
			}
		}

		await Promise.all(
			targets.map(async (q) => {
				// design-approvals with an empty gated list is already resolved to 0.
				if (q.key === "design-approvals" && q.count === 0) return
				try {
					const c = await getCount(q.doctype, triplesToObject(q.filters))
					q.count = typeof c === "number" ? c : Number(c) || 0
					q.error = false
				} catch (_) {
					q.count = null
					q.error = true
				}
			})
		)
		loading.value = false
	}

	return { queues, visibleQueues, loadCounts, loading }
}
