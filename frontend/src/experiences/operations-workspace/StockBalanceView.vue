<template>
	<section class="stock-note">
		<nav class="stock-breadcrumbs" aria-label="Breadcrumb">
			<RouterLink to="/">All Books</RouterLink><span>›</span><span>Stock</span>
		</nav>

		<header class="stock-hero">
			<span class="stock-book"><small>MGK</small><strong>STK</strong></span>
			<div>
				<div class="eyebrow">Stock note</div>
				<h1>Stock Balance</h1>
				<p>See the available stock by supplier and warehouse, including the inward dates that make up each balance.</p>
			</div>
			<RouterLink class="button secondary" to="/">← All Books</RouterLink>
		</header>

		<form class="filter-card" @submit.prevent="load">
			<label><span>From date</span><input v-model="filters.from_date" type="date" required /></label>
			<label><span>To date</span><input v-model="filters.to_date" type="date" required /></label>
			<label>
				<span>Supplier / stock holder</span>
				<select v-model="filters.supplier" @change="onSupplierChange">
					<option value="">All suppliers</option>
					<option v-for="option in options.suppliers" :key="option.name" :value="option.name">{{ localized(option.supplier_name, option.mgk_tamil_name, option.name) }}</option>
				</select>
			</label>
			<label>
				<span>Warehouse</span>
				<select v-model="filters.warehouse">
					<option value="">All warehouses</option>
					<option v-for="option in visibleWarehouses" :key="option.name" :value="option.name">{{ localized(option.name1, option.mgk_tamil_name, option.name) }}</option>
				</select>
			</label>
			<label>
				<span>Item</span>
				<select v-model="filters.item">
					<option value="">All items</option>
					<option v-for="option in options.items" :key="option.name" :value="option.name">{{ localized(option.name1, option.mgk_tamil_name, option.name) }}</option>
				</select>
			</label>
			<label>
				<span>Received type</span>
				<select v-model="filters.received_type">
					<option value="">All received types</option>
					<option v-for="option in options.received_types" :key="option.name" :value="option.name">{{ option.name }}</option>
				</select>
			</label>
			<button class="button primary refresh-button" type="submit" :disabled="state.loading">
				<i :class="state.loading ? 'pi pi-spin pi-spinner' : 'pi pi-refresh'" />
				{{ state.loading ? "Loading…" : "Show stock" }}
			</button>
		</form>

		<div v-if="state.error" class="stock-error" role="alert"><i class="pi pi-exclamation-triangle" /><span>{{ state.error }}</span></div>

		<section v-else class="stock-results">
			<div class="summary-grid">
				<article><span>Stock lines</span><strong>{{ summary.line_count || 0 }}</strong></article>
				<article><span>Warehouses</span><strong>{{ summary.warehouse_count || 0 }}</strong></article>
				<article><span>Available quantity</span><strong>{{ quantitySummary }}</strong></article>
				<article><span>Stock value</span><strong>{{ money(summary.total_value) }}</strong></article>
			</div>

			<div v-if="!state.loading && !rows.length" class="empty-stock">
				<i class="pi pi-box" /><h2>No stock found</h2><p>Change the filters or date range and try again.</p>
			</div>

			<div v-else class="stock-table-card">
				<header><div><h2>Available stock</h2><p>Each inward-date line is the quantity still remaining from that receipt date.</p></div><span>{{ rows.length }} lines</span></header>
				<div class="table-scroll">
					<table>
						<thead><tr><th>Item</th><th>Supplier / stock holder</th><th>Warehouse</th><th>Received type</th><th>Available</th><th>Value</th><th>Inward dates</th></tr></thead>
						<tbody>
							<tr v-for="row in rows" :key="rowKey(row)">
								<td><RouterLink :to="`/item/${encodeURIComponent(row.item_name)}`">{{ localized(row.item_display_name, row.item_tamil_name, row.item_name) }}</RouterLink><small>{{ row.item }}</small></td>
								<td><RouterLink v-if="row.supplier" :to="`/supplier/${encodeURIComponent(row.supplier)}`">{{ localized(row.supplier_name, row.supplier_tamil_name, row.supplier) }}</RouterLink><span v-else>Company stock</span></td>
								<td><RouterLink :to="`/warehouse/${encodeURIComponent(row.warehouse)}`">{{ localized(row.warehouse_name, row.warehouse_tamil_name, row.warehouse) }}</RouterLink></td>
								<td>{{ row.received_type || "—" }}</td>
								<td><strong>{{ qty(row.bal_qty) }}</strong><small>{{ row.stock_uom }}</small></td>
								<td>{{ money(row.bal_val) }}</td>
								<td>
									<div v-if="row.inward_date_breakdown?.length" class="inward-list">
										<span v-for="entry in row.inward_date_breakdown" :key="entry.date"><time>{{ entry.date }}</time><strong>{{ qty(entry.qty) }} {{ row.stock_uom }}</strong></span>
									</div>
									<span v-else>—</span>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</div>
		</section>
	</section>
</template>

<script setup>
import { computed, onMounted, reactive } from "vue"
import { RouterLink } from "vue-router"

import { callMethod } from "@/api/client"
import { useDisplayLanguage } from "@/composables/useDisplayLanguage"

const METHOD = "mgk_clothing_yrp.mgk_clothing_yrp.api.experiences.operations_workspace.stock_balance.get_stock_note"
const { isTamil } = useDisplayLanguage()
const today = new Date()
const monthAgo = new Date(today)
monthAgo.setDate(monthAgo.getDate() - 30)
const iso = (date) => date.toISOString().slice(0, 10)

const filters = reactive({ from_date: iso(monthAgo), to_date: iso(today), supplier: "", warehouse: "", item: "", received_type: "" })
const state = reactive({ loading: false, error: "", loaded: false })
const options = reactive({ suppliers: [], warehouses: [], items: [], received_types: [] })
const summary = reactive({ line_count: 0, warehouse_count: 0, total_value: 0, uom_totals: {} })
const rows = reactive([])

const visibleWarehouses = computed(() => filters.supplier
	? options.warehouses.filter((row) => row.supplier === filters.supplier)
	: options.warehouses)
const quantitySummary = computed(() => {
	const parts = Object.entries(summary.uom_totals || {}).map(([uom, value]) => `${qty(value)} ${uom}`)
	return parts.join(" · ") || "0"
})

function localized(english, tamil, fallback = "") {
	return (isTamil.value && tamil) || english || fallback || "—"
}

function qty(value) {
	return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 3 }).format(Number(value || 0))
}

function money(value) {
	return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value || 0))
}

function rowKey(row) {
	return [row.item, row.warehouse, row.received_type, row.lot].filter(Boolean).join("::")
}

function onSupplierChange() {
	if (filters.warehouse && !visibleWarehouses.value.some((row) => row.name === filters.warehouse)) filters.warehouse = ""
}

async function load() {
	state.loading = true
	state.error = ""
	try {
		const result = await callMethod(METHOD, { ...filters })
		rows.splice(0, rows.length, ...(result?.rows || []))
		Object.assign(options, result?.options || {})
		Object.assign(summary, result?.summary || {})
		if (!state.loaded && result?.filters) {
			filters.from_date = result.filters.from_date || filters.from_date
			filters.to_date = result.filters.to_date || filters.to_date
		}
		state.loaded = true
	} catch (error) {
		state.error = error?.message || "Unable to load the stock balance."
	} finally {
		state.loading = false
	}
}

onMounted(load)
</script>

<style scoped>
.stock-note { color: #172033; }
.stock-breadcrumbs { display: flex; gap: 8px; margin-bottom: 16px; color: #5f6878; font-size: .875rem; }
.stock-breadcrumbs a, td a { color: #087f73; font-weight: 750; text-decoration: none; }
.stock-hero { display: flex; align-items: center; gap: 16px; margin-bottom: 18px; padding: 20px 24px; border: 1px solid #e0d7c9; border-left: 8px solid #356d78; border-radius: 16px; background: linear-gradient(105deg, #fff7f0, #fff); box-shadow: 0 7px 24px rgba(25,35,53,.04); }
.stock-book { display: grid; place-items: center; flex: 0 0 auto; width: 58px; height: 68px; border-radius: 7px 13px 13px 7px; background: #356d78; color: #fff; box-shadow: inset 8px 0 rgba(0,0,0,.14); }
.stock-book small { font-size: .65rem; font-weight: 800; }.stock-book strong { font-size: 1.2rem; }
.stock-hero h1 { margin: 0 0 5px; font-size: 1.75rem; }.stock-hero p { margin: 0; color: #5f6878; font-size: .875rem; }.stock-hero .button { margin-left: auto; }
.eyebrow { margin-bottom: 5px; color: #9f3f2f; font-size: .75rem; font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
.button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 42px; padding: 9px 15px; border: 1px solid transparent; border-radius: 10px; font: inherit; font-size: .875rem; font-weight: 750; text-decoration: none; cursor: pointer; }.button.primary { background: #14233c; color: #fff; }.button.secondary { border-color: #ded9cf; background: #fff; color: #172033; }.button:disabled { opacity: .6; cursor: wait; }
.filter-card { display: grid; grid-template-columns: repeat(6, minmax(130px, 1fr)) auto; align-items: end; gap: 12px; margin-bottom: 16px; padding: 16px; border: 1px solid #e2ddd4; border-radius: 15px; background: #fff; }
label span { display: block; margin-bottom: 6px; color: #5f6878; font-size: .72rem; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; }
input, select { width: 100%; height: 42px; padding: 8px 10px; border: 1px solid #d7dce4; border-radius: 9px; background: #fff; color: #172033; font: inherit; font-size: .875rem; } input:focus, select:focus { border-color: #0f9184; outline: 3px solid rgba(15,145,132,.12); }
.summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }.summary-grid article { padding: 15px 17px; border: 1px solid #e2ddd4; border-radius: 13px; background: #fff; }.summary-grid span { display: block; color: #5f6878; font-size: .75rem; font-weight: 700; }.summary-grid strong { display: block; margin-top: 5px; font-size: 1.15rem; }
.stock-table-card { overflow: hidden; border: 1px solid #e2ddd4; border-radius: 15px; background: #fff; box-shadow: 0 5px 20px rgba(23,32,51,.035); }.stock-table-card > header { display: flex; align-items: center; padding: 14px 17px; border-bottom: 1px solid #e8e3db; background: #faf9f7; }.stock-table-card h2 { margin: 0; font-size: 1rem; }.stock-table-card header p { margin: 3px 0 0; color: #5f6878; font-size: .75rem; }.stock-table-card header > span { margin-left: auto; color: #5f6878; font-size: .75rem; font-weight: 700; }.table-scroll { overflow-x: auto; }table { width: 100%; border-collapse: collapse; }th { padding: 11px 13px; border-bottom: 1px solid #e8e3db; background: #14233c; color: #fff; font-size: .72rem; letter-spacing: .04em; text-align: left; text-transform: uppercase; white-space: nowrap; }td { padding: 13px; border-bottom: 1px solid #efebe5; font-size: .875rem; vertical-align: top; }tbody tr:last-child td { border-bottom: 0; }td small { display: block; margin-top: 3px; color: #687386; font-size: .72rem; }
.inward-list { display: grid; gap: 4px; min-width: 170px; }.inward-list span { display: flex; justify-content: space-between; gap: 12px; padding: 4px 7px; border-radius: 7px; background: #eef7f5; }.inward-list time { color: #536174; font-size: .75rem; }.inward-list strong { color: #087f73; font-size: .75rem; }
.stock-error, .empty-stock { padding: 28px; border: 1px solid #e2ddd4; border-radius: 15px; background: #fff; text-align: center; }.stock-error { display: flex; gap: 9px; color: #9f2e2e; text-align: left; }.empty-stock i { color: #758196; font-size: 1.7rem; }.empty-stock h2 { margin: 10px 0 3px; font-size: 1.1rem; }.empty-stock p { margin: 0; color: #5f6878; font-size: .875rem; }
@media (max-width: 1200px) { .filter-card { grid-template-columns: repeat(3, 1fr); }.refresh-button { align-self: end; }.summary-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 700px) { .stock-hero { align-items: flex-start; flex-wrap: wrap; }.stock-hero .button { width: 100%; margin-left: 0; }.filter-card { grid-template-columns: 1fr; }.summary-grid { grid-template-columns: 1fr 1fr; } }
</style>
