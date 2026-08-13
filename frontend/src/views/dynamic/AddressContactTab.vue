<!--
  AddressContactTab — list / create / edit / delete the Addresses and Contacts
  linked to a party (Supplier / Customer / MGK Agent). Self-contained: it owns
  its own load + dialogs and never touches the parent DocDetail form.

  The Address ↔ party and Contact ↔ party relations are Frappe Dynamic Link
  child tables. Loading queries Address/Contact with a child-table filter on those
  links (getAddressList/getContactList in api/client — get_address_display_list is
  NOT whitelisted, so it 403s over REST). CREATE sends `links: [{ link_doctype,
  link_name }]`. EDIT OMITS `links` so the REST PUT (which only replaces child
  tables present in the payload) preserves existing links — including addresses
  shared with other parties; Contact edits MERGE email_ids/phone_nos so a contact's
  other emails/phones are not dropped.
-->
<template>
	<div class="ac-tab">
		<div v-if="canRead('Address') || canRead('Contact')" class="ac-cols">
			<!-- ── ADDRESSES ──────────────────────────────────────────────── -->
			<section v-if="canRead('Address')" class="ac-col">
				<header class="ac-col__head">
					<h4 class="ac-col__title"><i class="pi pi-map-marker" /> Addresses</h4>
					<Button
						v-if="canCreate('Address')"
						label="New Address"
						icon="pi pi-plus"
						size="small"
						:disabled="!partyName"
						@click="openAddressDialog()"
					/>
				</header>

				<div v-if="addrLoading" class="ac-state">
					<i class="pi pi-spin pi-spinner" /> <span>Loading addresses…</span>
				</div>
				<div v-else-if="!addresses.length" class="mgk-empty">
					<i class="pi pi-map-marker" />
					<span class="mgk-empty__text">No addresses yet</span>
				</div>
				<div v-else class="ac-cards">
					<article v-for="a in addresses" :key="a.name" class="mgk-card ac-card">
						<div class="ac-card__main">
							<div class="ac-card__topline">
								<span class="ac-type">{{ a.address_type || "Address" }}</span>
								<span v-if="a.is_primary_address" class="badge badge--primary">Primary</span>
								<span v-if="a.is_shipping_address" class="badge badge--shipping">Shipping</span>
								<span v-if="a.disabled" class="badge badge--muted">Disabled</span>
							</div>
							<div v-if="a.address_title" class="ac-card__title">{{ a.address_title }}</div>
							<div class="ac-card__body">
								<div v-if="a.address_line1">{{ a.address_line1 }}</div>
								<div v-if="a.address_line2">{{ a.address_line2 }}</div>
								<div v-if="cityStatePin(a)">{{ cityStatePin(a) }}</div>
								<div v-if="a.country">{{ a.country }}</div>
								<div v-if="a.phone" class="ac-card__meta"><i class="pi pi-phone" /> {{ a.phone }}</div>
								<div v-if="a.email_id" class="ac-card__meta"><i class="pi pi-envelope" /> {{ a.email_id }}</div>
							</div>
						</div>
						<div class="ac-card__actions">
							<Button
								v-if="canWrite('Address')"
								icon="pi pi-pencil"
								text
								rounded
								size="small"
								v-tooltip.top="'Edit'"
								@click="openAddressDialog(a)"
							/>
							<Button
								v-if="canDelete('Address')"
								icon="pi pi-trash"
								text
								rounded
								size="small"
								severity="danger"
								v-tooltip.top="'Delete'"
								@click="confirmDeleteAddress(a)"
							/>
						</div>
					</article>
				</div>
			</section>

			<!-- ── CONTACTS ───────────────────────────────────────────────── -->
			<section v-if="canRead('Contact')" class="ac-col">
				<header class="ac-col__head">
					<h4 class="ac-col__title"><i class="pi pi-id-card" /> Contacts</h4>
					<Button
						v-if="canCreate('Contact')"
						label="New Contact"
						icon="pi pi-plus"
						size="small"
						:disabled="!partyName"
						@click="openContactDialog()"
					/>
				</header>

				<div v-if="contactLoading" class="ac-state">
					<i class="pi pi-spin pi-spinner" /> <span>Loading contacts…</span>
				</div>
				<div v-else-if="!contacts.length" class="mgk-empty">
					<i class="pi pi-id-card" />
					<span class="mgk-empty__text">No contacts yet</span>
				</div>
				<div v-else class="ac-cards">
					<article v-for="c in contacts" :key="c.name" class="mgk-card ac-card">
						<div class="ac-card__main">
							<div class="ac-card__topline">
								<span class="ac-type">{{ contactName(c) }}</span>
								<span v-if="c.is_primary_contact" class="badge badge--primary">Primary</span>
							</div>
							<div v-if="c.designation" class="ac-card__title">{{ c.designation }}</div>
							<div class="ac-card__body">
								<div v-if="c.email_id" class="ac-card__meta"><i class="pi pi-envelope" /> {{ c.email_id }}</div>
								<div v-if="c.mobile_no" class="ac-card__meta"><i class="pi pi-mobile" /> {{ c.mobile_no }}</div>
								<div v-if="c.phone" class="ac-card__meta"><i class="pi pi-phone" /> {{ c.phone }}</div>
							</div>
						</div>
						<div class="ac-card__actions">
							<Button
								v-if="canWrite('Contact')"
								icon="pi pi-pencil"
								text
								rounded
								size="small"
								v-tooltip.top="'Edit'"
								@click="openContactDialog(c)"
							/>
							<Button
								v-if="canDelete('Contact')"
								icon="pi pi-trash"
								text
								rounded
								size="small"
								severity="danger"
								v-tooltip.top="'Delete'"
								@click="confirmDeleteContact(c)"
							/>
						</div>
					</article>
				</div>
			</section>
		</div>
		<div v-else class="mgk-empty"><i class="pi pi-lock" /><span class="mgk-empty__text">No Address or Contact access</span></div>

		<!-- ── ADDRESS DIALOG ─────────────────────────────────────────────── -->
		<Dialog
			:visible="addrDialog"
			modal
			:header="addrForm.name ? 'Edit Address' : 'New Address'"
			:style="{ width: '480px', maxWidth: '95vw' }"
			@update:visible="addrDialog = $event"
			@hide="restoreDialogFocus('address')"
		>
			<div ref="addrFormEl" class="ac-form">
				<div v-if="errorLines.length" class="ac-error">
					<div v-for="(l, i) in errorLines" :key="i">{{ l }}</div>
				</div>

				<div class="ac-field" data-focus-key="address_type">
					<label class="field-label">Address Type <span class="req">*</span></label>
					<Select
						v-model="addrForm.address_type"
						:options="ADDRESS_TYPES"
						placeholder="Select…"
						:invalid="missing.address_type"
						class="fld"
						fluid
					/>
				</div>
				<div class="ac-field" data-focus-key="address_line1">
					<label class="field-label">Address Line 1 <span class="req">*</span></label>
					<InputText v-model="addrForm.address_line1" :invalid="missing.address_line1" class="fld" fluid />
				</div>
				<div class="ac-field" data-focus-key="address_line2">
					<label class="field-label">Address Line 2</label>
					<InputText v-model="addrForm.address_line2" class="fld" fluid />
				</div>
				<div class="ac-field" data-focus-key="city">
					<label class="field-label">City / Town <span class="req">*</span></label>
					<InputText v-model="addrForm.city" :invalid="missing.city" class="fld" fluid />
				</div>
				<div class="ac-field" data-focus-key="state">
					<label class="field-label">State / Province</label>
					<InputText v-model="addrForm.state" class="fld" fluid />
				</div>
				<div class="ac-field" data-focus-key="pincode">
					<label class="field-label">Postal Code</label>
					<InputText v-model="addrForm.pincode" class="fld" fluid />
				</div>
				<div class="ac-field" data-focus-key="country">
					<label class="field-label">Country <span class="req">*</span></label>
					<LinkField
						:model-value="addrForm.country"
						@update:model-value="addrForm.country = $event"
						target-doctype="Country"
						:invalid="missing.country"
					/>
				</div>
				<div class="ac-field">
					<label class="field-label">Email</label>
					<InputText v-model="addrForm.email_id" class="fld" fluid />
				</div>
				<div class="ac-field">
					<label class="field-label">Phone</label>
					<InputText v-model="addrForm.phone" class="fld" fluid />
				</div>
				<div class="ac-field ac-field--toggle">
					<ToggleSwitch
						:modelValue="!!addrForm.is_primary_address"
						@update:modelValue="addrForm.is_primary_address = $event ? 1 : 0"
					/>
					<span class="check-label">Preferred billing address</span>
				</div>
				<div class="ac-field ac-field--toggle">
					<ToggleSwitch
						:modelValue="!!addrForm.is_shipping_address"
						@update:modelValue="addrForm.is_shipping_address = $event ? 1 : 0"
					/>
					<span class="check-label">Preferred shipping address</span>
				</div>
			</div>

			<template #footer>
				<Button label="Cancel" severity="secondary" outlined size="small" @click="addrDialog = false" />
				<Button
					:label="addrForm.name ? 'Save' : 'Create'"
					icon="pi pi-check"
					size="small"
					:loading="saving"
					@click="saveAddress"
				/>
			</template>
		</Dialog>

		<!-- ── CONTACT DIALOG ─────────────────────────────────────────────── -->
		<Dialog
			:visible="contactDialog"
			modal
			:style="{ width: '480px', maxWidth: '95vw' }"
			@update:visible="contactDialog = $event"
			@hide="restoreDialogFocus('contact')"
		>
			<div ref="contactFormEl" class="ac-form">
				<div v-if="errorLines.length" class="ac-error">
					<div v-for="(l, i) in errorLines" :key="i">{{ l }}</div>
				</div>

				<div class="ac-field" data-focus-key="first_name">
					<label class="field-label">First Name <span class="req">*</span></label>
					<InputText v-model="contactForm.first_name" :invalid="missing.first_name" class="fld" fluid />
				</div>
				<div class="ac-field">
					<label class="field-label">Last Name</label>
					<InputText v-model="contactForm.last_name" class="fld" fluid />
				</div>
				<div class="ac-field">
					<label class="field-label">Designation</label>
					<InputText v-model="contactForm.designation" class="fld" fluid />
				</div>
				<div class="ac-field">
					<label class="field-label">Email</label>
					<InputText v-model="contactForm.email_id" class="fld" fluid />
				</div>
				<div class="ac-field">
					<label class="field-label">Mobile No</label>
					<InputText v-model="contactForm.mobile_no" class="fld" fluid />
				</div>
				<div class="ac-field ac-field--toggle">
					<ToggleSwitch
						:modelValue="!!contactForm.is_primary_contact"
						@update:modelValue="contactForm.is_primary_contact = $event ? 1 : 0"
					/>
					<span class="check-label">Primary contact</span>
				</div>
			</div>

			<template #footer>
				<Button label="Cancel" severity="secondary" outlined size="small" @click="contactDialog = false" />
				<Button
					:label="contactForm.name ? 'Save' : 'Create'"
					icon="pi pi-check"
					size="small"
					:loading="saving"
					@click="saveContact"
				/>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from "vue"
import Dialog from "primevue/dialog"
import Button from "primevue/button"
import InputText from "primevue/inputtext"
import Select from "primevue/select"
import ToggleSwitch from "primevue/toggleswitch"
import Tooltip from "primevue/tooltip"
import LinkField from "@/components/LinkField.vue"
import {
	getAddressList,
	getContactList,
	createDoc,
	updateDoc,
	deleteDoc,
	callMethod,
} from "@/api/client"
import { useAppToast } from "@/composables/useToast"
import { useAppConfirm } from "@/composables/useConfirm"
import { usePermissions } from "@/composables/usePermissions"
import { focusFirstControl } from "@/utils/focusControl"

const vTooltip = Tooltip

const props = defineProps({
	partyDoctype: { type: String, default: "" },
	partyName: { type: String, default: "" },
})

const toast = useAppToast()
const confirm = useAppConfirm()
const { canRead, canCreate, canWrite, canDelete } = usePermissions()

// Frappe's Address.address_type Select options (verified in the DocType JSON).
const ADDRESS_TYPES = [
	"Billing", "Shipping", "Office", "Personal", "Plant", "Postal",
	"Shop", "Subsidiary", "Warehouse", "Current", "Permanent", "Other",
]

const addresses = ref([])
const contacts = ref([])
const addrLoading = ref(false)
const contactLoading = ref(false)
const saving = ref(false)

const addrDialog = ref(false)
const contactDialog = ref(false)
const errorLines = ref([])
const missing = reactive({})
const addrFormEl = ref(null)
const contactFormEl = ref(null)
let addressDialogOpener = null
let contactDialogOpener = null

const addrForm = reactive(emptyAddress())
const contactForm = reactive(emptyContact())

function emptyAddress() {
	return {
		name: "",
		address_type: "Billing",
		address_line1: "",
		address_line2: "",
		city: "",
		state: "",
		pincode: "",
		country: "",
		email_id: "",
		phone: "",
		is_primary_address: 0,
		is_shipping_address: 0,
	}
}
function emptyContact() {
	return {
		name: "",
		first_name: "",
		last_name: "",
		designation: "",
		email_id: "",
		mobile_no: "",
		is_primary_contact: 0,
	}
}

// ── display helpers ──────────────────────────────────────────────────────
function cityStatePin(a) {
	return [a.city, a.state, a.pincode].filter(Boolean).join(", ")
}
function contactName(c) {
	return c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ") || c.name
}

// ── load ─────────────────────────────────────────────────────────────────
async function loadAddresses() {
	if (!canRead("Address") || !props.partyDoctype || !props.partyName) {
		addresses.value = []
		return
	}
	addrLoading.value = true
	try {
		addresses.value = await getAddressList(props.partyDoctype, props.partyName)
	} catch (e) {
		addresses.value = []
		toast.error("Could not load addresses", firstLine(e))
	} finally {
		addrLoading.value = false
	}
}
async function loadContacts() {
	if (!canRead("Contact") || !props.partyDoctype || !props.partyName) {
		contacts.value = []
		return
	}
	contactLoading.value = true
	try {
		contacts.value = await getContactList(props.partyDoctype, props.partyName)
	} catch (e) {
		contacts.value = []
		toast.error("Could not load contacts", firstLine(e))
	} finally {
		contactLoading.value = false
	}
}

onMounted(() => {
	loadAddresses()
	loadContacts()
})
watch(
	() => props.partyName,
	() => {
		loadAddresses()
		loadContacts()
	},
)

// ── error surfacing ──────────────────────────────────────────────────────
// Frappe puts validation text in _server_messages (JSON-encoded) and/or the
// exception/message. Pull human-readable lines for the inline banner + toast.
function clearErrors() {
	errorLines.value = []
	for (const k of Object.keys(missing)) delete missing[k]
}
function firstLine(e) {
	const lines = extractLines(e)
	return lines[0] || (e && e.message) || "Unexpected error"
}
function extractLines(e) {
	const out = []
	const data = e && (e.data || e._error || e)
	const sm = data && (data._server_messages || e._server_messages)
	if (sm) {
		try {
			for (const raw of JSON.parse(sm)) {
				try {
					out.push(JSON.parse(raw).message)
				} catch (_) {
					out.push(raw)
				}
			}
		} catch (_) {
			/* not JSON */
		}
	}
	if (!out.length && e && e.message) out.push(e.message)
	return out.map((s) => String(s).replace(/<[^>]*>/g, "").trim()).filter(Boolean)
}
function showError(e, fallback) {
	const lines = extractLines(e)
	errorLines.value = lines.length ? lines : [fallback]
	toast.error(fallback, lines[0] || (e && e.message))
}

function links() {
	return [{ link_doctype: props.partyDoctype, link_name: props.partyName }]
}

// ── address create / edit ────────────────────────────────────────────────
async function openAddressDialog(a = null) {
	addressDialogOpener = document.activeElement
	clearErrors()
	Object.assign(addrForm, emptyAddress())
	if (a) {
		addrForm.name = a.name
		addrForm.address_type = a.address_type || "Billing"
		addrForm.address_line1 = a.address_line1 || ""
		addrForm.address_line2 = a.address_line2 || ""
		addrForm.city = a.city || ""
		addrForm.state = a.state || ""
		addrForm.pincode = a.pincode || ""
		addrForm.country = a.country || ""
		addrForm.email_id = a.email_id || ""
		addrForm.phone = a.phone || ""
		addrForm.is_primary_address = a.is_primary_address ? 1 : 0
		addrForm.is_shipping_address = a.is_shipping_address ? 1 : 0
	}
	addrDialog.value = true
	await focusDialogField("address", "address_type")
}

function validateAddress() {
	clearErrors()
	let ok = true
	for (const f of ["address_type", "address_line1", "city", "country"]) {
		if (!String(addrForm[f] || "").trim()) {
			missing[f] = true
			ok = false
		}
	}
	if (!ok) errorLines.value = ["Please fill all required fields (marked *)."]
	return ok
}

async function saveAddress() {
	if (!validateAddress()) {
		const fieldname = ["address_type", "address_line1", "city", "country"].find((field) => missing[field])
		await focusDialogField("address", fieldname)
		return
	}
	saving.value = true
	try {
		const payload = {
			address_type: addrForm.address_type,
			address_line1: addrForm.address_line1,
			address_line2: addrForm.address_line2 || "",
			city: addrForm.city,
			state: addrForm.state || "",
			pincode: addrForm.pincode || "",
			country: addrForm.country,
			email_id: addrForm.email_id || "",
			phone: addrForm.phone || "",
			is_primary_address: addrForm.is_primary_address ? 1 : 0,
			is_shipping_address: addrForm.is_shipping_address ? 1 : 0,
		}
		if (addrForm.name) {
			// EDIT: omit `links` so the PUT preserves existing links — an address may
			// be shared with other parties; resending only this party would drop theirs.
			await updateDoc("Address", addrForm.name, payload)
			toast.success("Address updated")
		} else {
			payload.links = links()
			await createDoc("Address", payload)
			toast.success("Address created")
		}
		addrDialog.value = false
		await loadAddresses()
	} catch (e) {
		showError(e, "Could not save address")
	} finally {
		saving.value = false
	}
}

function confirmDeleteAddress(a) {
	confirm.require({
		header: "Delete address",
		message: `Delete this ${a.address_type || ""} address? This cannot be undone.`,
		acceptLabel: "Delete",
		acceptClass: "p-button-danger",
		accept: async () => {
			try {
				await deleteDoc("Address", a.name)
				toast.success("Address deleted")
				await loadAddresses()
			} catch (e) {
				toast.error("Could not delete address", firstLine(e))
			}
		},
	})
}

// ── contact create / edit ────────────────────────────────────────────────
async function openContactDialog(c = null) {
	contactDialogOpener = document.activeElement
	clearErrors()
	Object.assign(contactForm, emptyContact())
	if (c) {
		contactForm.name = c.name
		contactForm.first_name = c.first_name || ""
		contactForm.last_name = c.last_name || ""
		contactForm.designation = c.designation || ""
		contactForm.email_id = c.email_id || ""
		contactForm.mobile_no = c.mobile_no || ""
		contactForm.is_primary_contact = c.is_primary_contact ? 1 : 0
	}
	contactDialog.value = true
	await focusDialogField("contact", "first_name")
}

function validateContact() {
	clearErrors()
	// Frappe requires first_name OR last_name; we surface the requirement on first_name.
	if (!String(contactForm.first_name || "").trim() && !String(contactForm.last_name || "").trim()) {
		missing.first_name = true
		errorLines.value = ["A first name (or last name) is required."]
		return false
	}
	return true
}

async function saveContact() {
	if (!validateContact()) {
		await focusDialogField("contact", "first_name")
		return
	}
	saving.value = true
	try {
		const email = String(contactForm.email_id || "").trim()
		const mobile = String(contactForm.mobile_no || "").trim()
		const payload = {
			first_name: contactForm.first_name || "",
			last_name: contactForm.last_name || "",
			designation: contactForm.designation || "",
			is_primary_contact: contactForm.is_primary_contact ? 1 : 0,
		}
		if (contactForm.name) {
			// EDIT: preserve the contact's other emails/phones + foreign links. Fetch
			// the existing doc, keep its non-primary rows, set the primary from the
			// form. `links` is omitted so the PUT leaves the party links untouched.
			let existing = {}
			try {
				existing = await callMethod("frappe.client.get", { doctype: "Contact", name: contactForm.name })
			} catch (_) {
				/* fall back to form-only values below */
			}
			const emails = (existing.email_ids || []).filter((e) => !e.is_primary)
			if (email) emails.unshift({ email_id: email, is_primary: 1 })
			const phones = (existing.phone_nos || []).filter((ph) => !ph.is_primary_mobile_no)
			if (mobile) phones.unshift({ phone: mobile, is_primary_mobile_no: 1 })
			payload.email_ids = emails
			payload.phone_nos = phones
			await updateDoc("Contact", contactForm.name, payload)
			toast.success("Contact updated")
		} else {
			payload.email_ids = email ? [{ email_id: email, is_primary: 1 }] : []
			payload.phone_nos = mobile ? [{ phone: mobile, is_primary_mobile_no: 1 }] : []
			payload.links = links()
			await createDoc("Contact", payload)
			toast.success("Contact created")
		}
		contactDialog.value = false
		await loadContacts()
	} catch (e) {
		showError(e, "Could not save contact")
	} finally {
		saving.value = false
	}
}

function focusDialogField(kind, fieldname) {
	const root = kind === "address" ? addrFormEl : contactFormEl
	return focusFirstControl(root, { selector: fieldname ? `[data-focus-key="${fieldname}"]` : "" })
}

function restoreDialogFocus(kind) {
	const opener = kind === "address" ? addressDialogOpener : contactDialogOpener
	if (kind === "address") addressDialogOpener = null
	else contactDialogOpener = null
	if (opener && opener.isConnected && !opener.disabled) opener.focus()
}

function confirmDeleteContact(c) {
	confirm.require({
		header: "Delete contact",
		message: `Delete ${contactName(c)}? This cannot be undone.`,
		acceptLabel: "Delete",
		acceptClass: "p-button-danger",
		accept: async () => {
			try {
				await deleteDoc("Contact", c.name)
				toast.success("Contact deleted")
				await loadContacts()
			} catch (e) {
				toast.error("Could not delete contact", firstLine(e))
			}
		},
	})
}
</script>

<style scoped>
.ac-tab {
	padding-top: var(--space-2);
}

/* Two responsive columns; stack on mobile. */
.ac-cols {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: var(--space-5);
	align-items: start;
}
@media (max-width: 768px) {
	.ac-cols {
		grid-template-columns: 1fr;
	}
}

.ac-col__head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-3);
	margin-bottom: var(--space-3);
}
.ac-col__title {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	margin: 0;
	font-size: var(--fs-base);
	font-weight: 700;
	color: var(--mgk-ink-2);
}
.ac-col__title .pi {
	color: var(--mgk-accent);
	font-size: 15px;
}

.ac-state {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	padding: 14px 4px;
	color: var(--mgk-muted);
	font-size: var(--fs-sm);
}

.ac-cards {
	display: flex;
	flex-direction: column;
	gap: var(--space-3);
}

.ac-card {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: var(--space-3);
	padding: var(--space-4);
}
.ac-card__main {
	min-width: 0;
	flex: 1;
}
.ac-card__topline {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: var(--space-2);
	margin-bottom: 4px;
}
.ac-type {
	font-size: var(--fs-md);
	font-weight: 700;
	color: var(--mgk-ink);
	word-break: break-word;
}
.ac-card__title {
	font-size: var(--fs-sm);
	color: var(--mgk-muted);
	margin-bottom: 6px;
}
.ac-card__body {
	font-size: var(--fs-sm);
	line-height: 1.5;
	color: var(--mgk-ink-2);
}
.ac-card__meta {
	display: flex;
	align-items: center;
	gap: 6px;
	color: var(--mgk-muted);
	margin-top: 2px;
}
.ac-card__meta .pi {
	font-size: 12px;
}
.ac-card__actions {
	display: flex;
	flex-shrink: 0;
	gap: 2px;
}

/* Status pills — tinted via the shared --mgk-* tokens. */
.badge {
	display: inline-flex;
	align-items: center;
	font-size: var(--fs-2xs);
	font-weight: 700;
	letter-spacing: 0.02em;
	padding: 1px 8px;
	border-radius: 999px;
	text-transform: uppercase;
}
.badge--primary {
	background: var(--mgk-accent-50);
	color: var(--mgk-accent-700);
}
.badge--shipping {
	background: var(--mgk-success-50);
	color: var(--mgk-success);
}
.badge--muted {
	background: var(--mgk-slate-50);
	color: var(--mgk-muted);
}

/* ── Dialog form ───────────────────────────────────────────────────────── */
.ac-form {
	display: flex;
	flex-direction: column;
	gap: var(--space-3);
}
.ac-field {
	display: flex;
	flex-direction: column;
	gap: 4px;
}
.ac-field--toggle {
	flex-direction: row;
	align-items: center;
	gap: var(--space-2);
	margin-top: 2px;
}
.field-label {
	font-size: var(--fs-xs);
	font-weight: 600;
	color: var(--mgk-muted);
}
.field-label .req {
	color: var(--mgk-danger);
	margin-left: 2px;
}
.check-label {
	font-size: var(--fs-sm);
	color: var(--mgk-ink-2);
}
.ac-error {
	background: var(--mgk-danger-50);
	color: var(--mgk-danger);
	border: 1px solid var(--mgk-danger);
	border-radius: var(--radius-sm);
	padding: 8px 12px;
	font-size: var(--fs-sm);
	line-height: 1.45;
}
</style>
