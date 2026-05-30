<template>
	<div class="home">
		<!-- Greeting — NO site-name chip, NO role chip (plan, 2026-05-25). -->
		<div class="home-greeting">
			<h1>{{ greeting }}</h1>
		</div>

		<!-- My Work Today — live work-queues (CUSTOM_UI §4). Each card deep-links
		     to its DocType list pre-filtered to the same condition (§6.4). -->
		<template v-if="visibleQueues.length">
			<div class="section-head">
				<h2 class="mgk-section-title">My Work Today</h2>
				<span class="section-hint">Live counts across your queues</span>
			</div>

			<div class="queue-grid">
				<button
					v-for="q in visibleQueues"
					:key="q.key"
					class="queue-card"
					@click="openQueue(q)"
				>
					<div class="q-icon" :class="`tone-${q.tone}`">
						<i :class="q.icon" />
					</div>
					<div class="q-body">
						<div class="q-label">{{ q.label }}</div>
						<div class="q-count">{{ formatCount(q) }}</div>
						<div class="q-sub">{{ q.sub }}</div>
					</div>
					<i class="pi pi-arrow-right q-arrow" />
				</button>
			</div>
		</template>

		<!-- Quick Create — perm-gated pills for the independent, parent-free
		     creates (CUSTOM_UI §11). -->
		<template v-if="quickCreates.length">
			<div class="section-head">
				<h2 class="mgk-section-title">Quick Create</h2>
				<span class="section-hint">Start a new document</span>
			</div>

			<div class="quick-create-row">
				<button
					v-for="qc in quickCreates"
					:key="qc.doctype"
					class="qc-pill"
					@click="$router.push(`/${qc.route}/new`)"
				>
					<i :class="qc.icon" />
					<span>{{ qc.label }}</span>
				</button>
			</div>
		</template>

		<!-- Jump to — hero shortcut grid (kept). -->
		<div class="section-head">
			<h2 class="mgk-section-title">Jump to</h2>
			<span class="section-hint">Live document lists</span>
		</div>

		<div class="shortcut-grid">
			<button
				v-for="s in visibleShortcuts"
				:key="s.route"
				class="shortcut-card"
				@click="$router.push(`/${s.route}`)"
			>
				<div class="s-icon"><i :class="s.icon" /></div>
				<div class="s-body">
					<div class="s-title">{{ s.label }}</div>
					<div class="s-sub">{{ s.sub }}</div>
				</div>
				<i class="pi pi-arrow-right s-arrow" />
			</button>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted } from "vue"
import { useRouter } from "vue-router"
import { useAuth } from "@/composables/useAuth"
import { usePermissions } from "@/composables/usePermissions"
import { getRegistryByDoctype } from "@/config/doctypes"
import { useHomeQueues } from "@/composables/useHomeQueues"

const router = useRouter()
const { fullName } = useAuth()
const { canRead, canCreate } = usePermissions()
const { queues, visibleQueues: queueVisible, loadCounts } = useHomeQueues()

const greeting = computed(() => {
	const h = new Date().getHours()
	const part = h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening"
	const name = (fullName.value || "").split(" ")[0]
	return name ? `${part}, ${name}` : `${part}`
})

// ── My Work Today queues ──
const visibleQueues = computed(() => queueVisible())

function formatCount(q) {
	if (q.error || q.count === null || q.count === undefined) return "—"
	return q.count
}

// Whole card deep-links to the filtered list. Filters travel as a JSON-encoded
// array of [field, op, value] triples — DynamicListPage parses `?filters=` into
// its base filter (ANDs with the tabs + feeds the tab counts).
function openQueue(q) {
	if (!q.route) return
	const encoded = encodeURIComponent(JSON.stringify(q.filters))
	router.push(`/${q.route}?filters=${encoded}`)
}

onMounted(() => {
	// Counts load in parallel; failures degrade to "—" per card.
	loadCounts()
})

// ── Quick Create (parent-free, independent creates) ──
const QUICK_CREATE = ["Work Order", "Purchase Order", "MGK Agent"]

const quickCreates = computed(() =>
	QUICK_CREATE.filter((dt) => canCreate(dt)).map((dt) => {
		const reg = getRegistryByDoctype(dt)
		return {
			doctype: dt,
			label: dt,
			icon: reg?.icon || "pi pi-plus",
			route: reg?.route || "",
		}
	}).filter((qc) => qc.route)
)

// ── Jump-to shortcuts (hero-4, perm-gated) ──
const SHORTCUTS = [
	{ doctype: "Work Order", icon: "pi pi-bars", sub: "Towel job-work orders" },
	{ doctype: "Purchase Order", icon: "pi pi-upload", sub: "Yarn & consumables" },
	{ doctype: "Goods Received Note", icon: "pi pi-plus-circle", sub: "Receipts against PO / WO" },
	{ doctype: "Inspection Entry", icon: "pi pi-verified", sub: "Quality inspection queue" },
]

const visibleShortcuts = computed(() =>
	SHORTCUTS.filter((s) => canRead(s.doctype)).map((s) => ({
		...s,
		label: s.doctype,
		route: getRegistryByDoctype(s.doctype)?.route || "",
	}))
)
</script>

<style scoped>
.home {
	display: flex;
	flex-direction: column;
	gap: 8px;
	/* Containment: blank lower region reads as intentional margin, not void. */
	max-width: 1100px;
	margin: 0 auto;
	width: 100%;
}

.home-greeting h1 {
	font-size: 22px;
	font-weight: 600;
	margin: 0 0 6px;
	letter-spacing: -0.01em;
}

/* Helper text stacks directly under the heading (not right-aligned). */
.section-head {
	margin: 14px 0 8px;
}

.section-head h2 {
	font-size: 14.5px;
	font-weight: 600;
	margin: 0;
}

.section-hint {
	display: block;
	margin-top: 2px;
	padding-left: 13px;   /* aligns under the section-title text past its accent bar */
	font-size: 11px;
	color: var(--mgk-muted-2);
}

/* ── My Work Today queue cards ── */
.queue-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
	gap: 12px;
}

.queue-card {
	display: flex;
	align-items: flex-start;
	gap: 12px;
	background: var(--mgk-card);
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius);
	box-shadow: var(--mgk-shadow-sm);
	padding: 14px 16px;
	cursor: pointer;
	text-align: left;
	transition: border-color 0.14s, transform 0.14s, box-shadow 0.14s;
}

.queue-card:hover {
	border-color: var(--mgk-accent);
	transform: translateY(-1px);
	box-shadow: 0 6px 18px rgba(11, 18, 32, 0.08);
}

.q-icon {
	width: 38px;
	height: 38px;
	border-radius: 9px;
	display: grid;
	place-items: center;
	font-size: 17px;
	flex-shrink: 0;
}

/* Tone palette. Teal is the default identity; amber is reserved for genuine
   alert queues (design approvals pending). The old off-palette blue "info"
   tone is folded into teal so the home grid reads as one accent system. */
.q-icon.tone-amber {
	background: var(--mgk-warn-50);
	color: var(--mgk-warn);
}

.q-icon.tone-info,
.q-icon.tone-emerald {
	background: var(--mgk-accent-50);
	color: var(--mgk-accent);
}

.q-icon.tone-slate {
	background: var(--mgk-slate-50);
	color: var(--mgk-ink-2);
}

.q-body {
	flex: 1;
	min-width: 0;
}

.q-label {
	font-size: 12.5px;
	font-weight: 600;
	color: var(--mgk-muted);
}

.q-count {
	font-size: 28px;
	font-weight: 700;
	line-height: 1.15;
	color: var(--mgk-accent);
	letter-spacing: -0.02em;
	margin: 2px 0;
}

.q-sub {
	font-size: 12px;
	color: var(--mgk-muted);
}

.q-arrow {
	color: var(--mgk-muted-2);
	margin-top: 2px;
}

.queue-card:hover .q-arrow {
	color: var(--mgk-accent);
}

/* ── Quick Create pills ── */
.quick-create-row {
	display: flex;
	flex-wrap: wrap;
	gap: 10px;
}

.qc-pill {
	display: inline-flex;
	align-items: center;
	gap: 8px;
	min-height: 38px;
	background: var(--mgk-card);
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius);
	padding: 8px 16px;
	font-size: 13px;
	font-weight: 600;
	color: var(--mgk-ink-2);
	cursor: pointer;
	transition: border-color 0.14s, background 0.14s;
}

.qc-pill i {
	color: var(--mgk-accent);
	font-size: 13px;
}

.qc-pill:hover {
	border-color: var(--mgk-accent);
	background: var(--mgk-accent-50);
}

.qc-pill:hover span {
	text-decoration: underline;
	text-decoration-color: var(--mgk-accent);
	text-underline-offset: 3px;
}

/* ── Jump-to shortcut grid ── */
.shortcut-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
	gap: 12px;
}

.shortcut-card {
	display: flex;
	align-items: center;
	gap: 12px;
	background: var(--mgk-card);
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius);
	box-shadow: var(--mgk-shadow-sm);
	padding: 14px 16px;
	cursor: pointer;
	text-align: left;
	transition: border-color 0.14s, transform 0.14s, box-shadow 0.14s;
}

.shortcut-card:hover {
	border-color: var(--mgk-accent);
	transform: translateY(-1px);
	box-shadow: 0 6px 18px rgba(11, 18, 32, 0.08);
}

.s-icon {
	width: 36px;
	height: 36px;
	border-radius: 9px;
	background: var(--mgk-accent-50);
	color: var(--mgk-accent-700);
	display: grid;
	place-items: center;
	font-size: 16px;
	flex-shrink: 0;
}

.s-body {
	flex: 1;
	min-width: 0;
}

.s-title {
	font-size: 14px;
	font-weight: 600;
	color: var(--mgk-ink);
}

.s-sub {
	font-size: 12px;
	color: var(--mgk-muted);
	margin-top: 1px;
}

.s-arrow {
	color: var(--mgk-muted-2);
}

.shortcut-card:hover .s-arrow {
	color: var(--mgk-accent);
}
</style>
