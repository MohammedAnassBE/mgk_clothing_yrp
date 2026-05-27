import { createRouter, createWebHistory } from "vue-router"

const routes = [
	{
		path: "/",
		component: () => import("@/components/layout/AppLayout.vue"),
		children: [
			{
				path: "",
				redirect: "/home",
			},
			// Home — work hub landing
			{
				path: "home",
				name: "Home",
				component: () => import("@/views/home/HomePage.vue"),
			},
			// ── Rich production-config flows (R1a) — EXPLICIT routes, declared
			//    BEFORE the generic :docRoute/:id catch-all so they win the match.
			//    IPDConfigView: the IPD config surface (BOM + processes + matrices).
			//    ProcessMatrixEditor: the "process the combination" editor; also
			//    handles :id === "new" (create) reading ?ipd=&process= from query.
			{
				path: "item-production-detail/:id",
				name: "IPDConfig",
				component: () => import("@/views/dynamic/IPDConfigView.vue"),
				props: true,
			},
			{
				path: "ipd-process-matrix/:id",
				name: "ProcessMatrix",
				component: () => import("@/views/dynamic/ProcessMatrixEditor.vue"),
				props: true,
			},
			//    BOMMappingEditor (R1b): the "Item BOM based on attribute mapping"
			//    editor. Cross-product of the produced item's attribute values ×
			//    the BOM item's attribute values + per-combination quantities.
			{
				path: "item-bom-attribute-mapping/:id",
				name: "BOMMapping",
				component: () => import("@/views/dynamic/BOMMappingEditor.vue"),
				props: true,
			},
			//    ProductionOrderView (R2): the Production Order grid editor
			//    (ProductionOrderTable port — row-attr × grid-attr matrix per item).
			//    Also handles :id === "new" (create). Explicit, BEFORE the generic
			//    :docRoute/:id catch-all, so it wins over the generic DocDetail form.
			{
				path: "production-order/:id",
				name: "ProductionOrder",
				component: () => import("@/views/dynamic/ProductionOrderView.vue"),
				props: true,
			},
			// Generic read-only detail/form page (DocDetail) — serves every
			// sidebar DocType. View mode now; edit/create + write flows next.
			{
				path: ":docRoute/:id",
				name: "DocDetail",
				component: () => import("@/views/dynamic/DocDetail.vue"),
				props: true,
			},
			// Dynamic list (catch-all) — serves every sidebar DocType.
			{
				path: ":docRoute",
				name: "DynamicList",
				component: () => import("@/views/dynamic/DynamicListPage.vue"),
				props: true,
			},
		],
	},
]

const router = createRouter({
	history: createWebHistory("/web"),
	routes,
})

// Auth guard — boot.user is injected by web.py (load_user()); for Guests it is
// the string "Guest", otherwise the user object. Bounce Guests to login.
router.beforeEach((to) => {
	const bootUser = window.frappe?.boot?.user
	const isGuest = bootUser === "Guest" || bootUser?.name === "Guest"
	if (isGuest) {
		window.location.href = `/login?redirect-to=${encodeURIComponent("/web" + to.fullPath)}`
		return false
	}
})

// ── Stale-chunk recovery ────────────────────────────────────────────────────
// After a new build deploys, an already-open tab still references the PREVIOUS
// build's lazy chunks (hashed filenames). The next navigation/preload then 404s
// with "Failed to fetch dynamically imported module", stranding the user (e.g.
// on "+ New"). Recover with a ONE-SHOT full reload at the intended destination
// to pull the current build. A short time-guard prevents a reload loop if the
// chunk is genuinely missing rather than merely stale.
const RELOAD_KEY = "mgk:last-chunk-reload"
function recoverFromStaleChunk(targetPath) {
	const last = Number(sessionStorage.getItem(RELOAD_KEY) || 0)
	if (Date.now() - last < 10000) return // reloaded recently — let the error surface
	sessionStorage.setItem(RELOAD_KEY, String(Date.now()))
	if (targetPath) window.location.assign("/web" + targetPath)
	else window.location.reload()
}

router.onError((error, to) => {
	const msg = error?.message || ""
	if (/dynamically imported module|module script failed|Failed to fetch/i.test(msg)) {
		recoverFromStaleChunk(to?.fullPath)
	}
})

// Vite's preload helper dispatches this on the window when a modulepreload fails.
window.addEventListener("vite:preloadError", (event) => {
	event.preventDefault()
	recoverFromStaleChunk()
})

export default router
