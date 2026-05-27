<!--
  Generic detail / edit / create page for EVERY DocType (per CUSTOM_UI.md §7 +
  MGK_WEB_PLAN.md "Reusable components"). ONE form component, three modes:

    view    — read-only field grid + child DataTables + tabs + side panel.
    edit    — same fields/tables become PrimeVue inputs bound to a `form` model
              (deep-copied from the doc). Save → useDoc.save(form, id).
    create  — props.id === "new"; a blank form built from meta (+ meta defaults);
              no doc/linked/activity/approval load. Save → useDoc.save(form).

  Write flows go through useDoc (create/update/submit/cancel/delete/amend) →
  standard Frappe REST → the yrp controllers run (SLEs written there, NEVER here).

  Child-table contract (MGK_WEB_PLAN.md "Backend integration contract" item 1):
  send the child rows as a FLAT array in the child field (`items`,
  `deliverables`+`receivables`, `stock_update_details`) and leave the hidden
  grouped-JSON field (`item_details` / `deliverable_details` /
  `receivable_details`) EMPTY — each voucher's before_validate skips ungroup
  when that field is falsy, so the flat rows persist as-is. EXCEPTION: the grouped
  size-pivot / item->attribute->variant editor (StockItemGridEditor) IS built for
  the doctypes in STOCK_GROUPED_MAP (incl. Purchase Order) — those emit the grouped
  JSON + an EMPTY flat array, so before_validate runs ungroup and the server
  resolves/creates the variants. Every other doctype uses the flat path above.

  Reads: frappe.client.get (doc + child rows + _comments), getdoctype (meta),
  linked_with.get (Linked Documents), get_docinfo (Activity).
-->
<template>
	<div class="doc-detail">
		<!-- Breadcrumb -->
		<nav class="crumbs">
			<a @click="goHome">Home</a>
			<span class="sep">/</span>
			<a @click="goList">{{ registry?.label || docRoute }}</a>
			<span class="sep">/</span>
			<span class="crumb-cur mgk-mono">{{ isCreate ? "New" : id }}</span>
		</nav>

		<!-- Header -->
		<div class="detail-head">
			<div class="id-block">
				<div class="doc-id mgk-mono">
					<span v-if="isCreate">New {{ registry?.label || doctype }}</span>
					<span v-else>{{ id }}</span>
				</div>
				<div v-if="!isCreate && titleLine" class="doc-title">{{ titleLine }}</div>
				<div v-else-if="mode === 'edit'" class="doc-title edit-hint">Editing</div>
			</div>

			<Tag
				v-if="!loading && doc && mode === 'view' && (isSubmittable || isWorkflow || doc.status)"
				class="head-status"
				:value="statusLabel"
				:severity="statusSeverity"
				rounded
			/>

			<div class="head-actions">
				<!-- ── VIEW mode, draft (docstatus 0) ── -->
				<template v-if="mode === 'view' && doc">
					<!-- Workflow-managed doctypes (Process Cost / Item Price): the
					     transition buttons REPLACE plain Submit/Cancel (which are
					     suppressed via isSubmittable=false). Server-authoritative. -->
					<WorkflowActions
						v-if="isWorkflow"
						ref="workflowRef"
						:doc="doc"
						:doctype="doctype"
						@changed="reloadView"
					/>
					<Button
						v-if="docstatus === 0 && canWrite(doctype)"
						label="Edit"
						icon="pi pi-pencil"
						size="small"
						@click="enterEdit"
					/>
					<Button
						v-if="docstatus === 0 && isSubmittable && canSubmit(doctype)"
						label="Submit"
						icon="pi pi-arrow-right"
						iconPos="right"
						size="small"
						:loading="acting === 'submit'"
						@click="onSubmit"
					/>
					<Button
						v-if="docstatus === 0 && canDelete(doctype)"
						label="Delete"
						icon="pi pi-trash"
						size="small"
						severity="danger"
						outlined
						:loading="acting === 'delete'"
						@click="onDelete"
					/>

					<!-- VIEW mode, submitted (docstatus 1) -->
					<Button
						v-if="docstatus === 1 && isSubmittable && canCancel(doctype)"
						label="Cancel"
						icon="pi pi-ban"
						size="small"
						severity="danger"
						outlined
						:loading="acting === 'cancel'"
						@click="onCancel"
					/>

					<!-- VIEW mode, cancelled (docstatus 2) -->
					<Button
						v-if="docstatus === 2 && isSubmittable && canAmend(doctype)"
						label="Amend"
						icon="pi pi-clone"
						size="small"
						:loading="acting === 'amend'"
						@click="onAmend"
					/>
					<Button
						v-if="docstatus === 2 && canDelete(doctype)"
						label="Delete"
						icon="pi pi-trash"
						size="small"
						severity="danger"
						outlined
						:loading="acting === 'delete'"
						@click="onDelete"
					/>
				</template>

				<!-- ── EDIT mode ── -->
				<template v-else-if="mode === 'edit'">
					<Button
						label="Discard"
						icon="pi pi-times"
						size="small"
						severity="secondary"
						outlined
						:disabled="saving"
						@click="onDiscard"
					/>
					<Button
						v-if="canWrite(doctype)"
						label="Save"
						icon="pi pi-check"
						size="small"
						:loading="saving"
						@click="onSave"
					/>
				</template>

				<!-- ── CREATE mode ── -->
				<template v-else-if="mode === 'create'">
					<Button
						label="Discard"
						icon="pi pi-times"
						size="small"
						severity="secondary"
						outlined
						:disabled="saving"
						@click="onDiscard"
					/>
					<Button
						v-if="canCreate(doctype)"
						label="Save"
						icon="pi pi-check"
						size="small"
						:loading="saving"
						@click="onSave"
					/>
				</template>

				<a
					v-if="!isCreate && (isAdmin || hasRole('System Manager'))"
					class="desk-link"
					:href="deskUrl"
					target="_blank"
					rel="noopener"
				>
					<i class="pi pi-external-link" /> Open in Desk
				</a>
			</div>
		</div>

		<!-- WO design-approval gate banner (Work Order only, never in create) -->
		<WorkOrderApproval
			v-if="isWorkOrder && doc && mode === 'view'"
			ref="approvalRef"
			:name="doc.name"
			:docstatus="Number(doc.docstatus) || 0"
			@changed="onApprovalChanged"
			@state="onApprovalState"
		/>

		<!-- Loading (doc load, or create-mode meta load) -->
		<div v-if="loading || (isCreate && metaLoading)" class="state-block">
			<i class="pi pi-spin pi-spinner" style="font-size: 1.5rem" />
			<span>Loading…</span>
		</div>

		<!-- Error (load failure) -->
		<Message v-else-if="error && !doc && !isCreate" severity="error" :closable="false">
			{{ error }}
		</Message>

		<!-- ════════════════ CREATE / EDIT FORM ════════════════ -->
		<div v-else-if="isFormMode" class="form-layout">
			<div class="detail-main form-card">
				<!-- Field grid (inputs) -->
				<div class="form-grid">
					<div
						v-for="f in visibleFormFields"
						:key="f.fieldname"
						class="form-field"
						:class="{ wide: f.wide }"
					>
						<label class="field-label" :for="'fld-' + f.fieldname">
							{{ f.label }}
							<span v-if="isReqd(f)" class="req">*</span>
						</label>

						<!-- Data / Small Text -->
						<InputText
							v-if="f.input === 'text'"
							:id="'fld-' + f.fieldname"
							v-model="form[f.fieldname]"
							:disabled="isReadOnly(f)"
							:invalid="isMissing(f)"
							class="fld"
						/>

						<!-- Text / Long Text / Code -->
						<Textarea
							v-else-if="f.input === 'textarea'"
							:id="'fld-' + f.fieldname"
							v-model="form[f.fieldname]"
							:disabled="isReadOnly(f)"
							:invalid="isMissing(f)"
							rows="3"
							autoResize
							class="fld"
						/>

						<!-- Int / Float / Percent / Currency -->
						<InputNumber
							v-else-if="f.input === 'number'"
							:id="'fld-' + f.fieldname"
							v-model="form[f.fieldname]"
							:disabled="isReadOnly(f)"
							:invalid="isMissing(f)"
							:minFractionDigits="f.minFraction"
							:maxFractionDigits="f.maxFraction"
							:suffix="f.suffix"
							class="fld"
							fluid
						/>

						<!-- Date -->
						<DatePicker
							v-else-if="f.input === 'date'"
							:id="'fld-' + f.fieldname"
							:modelValue="toDateObj(form[f.fieldname])"
							@update:modelValue="form[f.fieldname] = fromDateObj($event, false)"
							:disabled="isReadOnly(f)"
							:invalid="isMissing(f)"
							dateFormat="dd-mm-yy"
							showIcon
							iconDisplay="input"
							class="fld"
							fluid
						/>

						<!-- Datetime -->
						<DatePicker
							v-else-if="f.input === 'datetime'"
							:id="'fld-' + f.fieldname"
							:modelValue="toDateObj(form[f.fieldname])"
							@update:modelValue="form[f.fieldname] = fromDateObj($event, true)"
							:disabled="isReadOnly(f)"
							:invalid="isMissing(f)"
							dateFormat="dd-mm-yy"
							showTime
							hourFormat="24"
							showIcon
							iconDisplay="input"
							class="fld"
							fluid
						/>

						<!-- Time — plain HH:MM:SS text input (picker component intentionally avoided) -->
						<InputText
							v-else-if="f.input === 'time'"
							:id="'fld-' + f.fieldname"
							v-model="form[f.fieldname]"
							:disabled="isReadOnly(f)"
							:invalid="isMissing(f)"
							placeholder="HH:MM:SS"
							class="fld"
						/>

						<!-- Check -->
						<div v-else-if="f.input === 'check'" class="fld-check">
							<ToggleSwitch
								:inputId="'fld-' + f.fieldname"
								:modelValue="!!form[f.fieldname]"
								@update:modelValue="form[f.fieldname] = $event ? 1 : 0"
								:disabled="isReadOnly(f)"
							/>
							<span class="check-label">{{ form[f.fieldname] ? "Yes" : "No" }}</span>
						</div>

						<!-- Select -->
						<Select
							v-else-if="f.input === 'select'"
							:id="'fld-' + f.fieldname"
							v-model="form[f.fieldname]"
							:options="f.options"
							@change="onFieldChanged(f.fieldname)"
							:disabled="isReadOnly(f)"
							:invalid="isMissing(f)"
							showClear
							placeholder="Select…"
							class="fld"
							fluid
						/>

						<!-- Link / Dynamic Link → LinkField (AutoComplete + "open linked doc").
						     target-doctype is reactive: a Dynamic Link re-resolves from its
						     controlling field at runtime. -->
						<LinkField
							v-else-if="f.input === 'link'"
							:model-value="form[f.fieldname]"
							@update:model-value="form[f.fieldname] = $event"
							:target-doctype="f.isDynamic ? form[f.dynamicField] : f.linkTarget"
							:disabled="isReadOnly(f)"
							:invalid="isMissing(f)"
							@item-select="onFieldChanged(f.fieldname)"
							@change="onFieldChanged(f.fieldname)"
						/>

						<!-- Fallback (unknown but editable scalar) -->
						<InputText
							v-else
							:id="'fld-' + f.fieldname"
							v-model="form[f.fieldname]"
							:disabled="isReadOnly(f)"
							class="fld"
						/>
					</div>

					<div v-if="!formFields.length" class="empty-inline">
						No editable fields for this DocType.
					</div>
				</div>

				<!-- R3a: stock size-pivot editor(s) — grouped item_details path.
				     Renders INSTEAD of the flat grid for stock vouchers only;
				     the replaced flat child fields are dropped from
				     editableChildTables above. -->
				<div
					v-for="pv in stockPivots"
					:key="'pivot-' + pv.childField"
					class="child-editor"
				>
					<div class="child-editor-head">
						<h4>{{ pv.label }}</h4>
						<span class="child-cols-note pivot-note">
							{{ useGrnSplit ? "received-type split · server resolves variants on save" : "size-pivot · server resolves variants on save" }}
						</span>
					</div>
					<!-- R3b: GRN against Work Order needs the received-type SPLIT UX
					     (split one item's qty across multiple received types). All
					     other stock vouchers (and GRN-against-Purchase-Order) keep the
					     generic pivot. Both editors expose the same loadData/getItems/
					     hasItems surface and register into gridRefs identically, so
					     hydratePivotsForEdit + buildPayload are unchanged. -->
					<GRNReceivedTypeEditor
						v-if="useGrnSplit"
						:ref="(el) => setGridRef(pv.childField, el)"
						:editable="true"
					/>
					<StockItemGridEditor
						v-else
						:ref="(el) => setGridRef(pv.childField, el)"
						:grouped-field="pv.groupedField"
						:value-fields="pv.valueFields"
						:entry-fields="pv.entryFields"
						:cell-fields="pv.cellFields || []"
						:editable="true"
					/>
				</div>

				<!-- Child-table editors (flat grid) -->
				<div
					v-for="ct in editableChildTables"
					:key="ct.fieldname"
					class="child-editor"
				>
					<div class="child-editor-head">
						<h4>{{ ct.label }}</h4>
						<span v-if="!ct.columnsAvailable" class="child-cols-note">
							columns unavailable — open in Desk
						</span>
						<Button
							v-else
							label="Add Row"
							icon="pi pi-plus"
							size="small"
							severity="secondary"
							outlined
							@click="addChildRow(ct)"
						/>
					</div>

					<DataTable
						:value="form[ct.fieldname]"
						class="mgk-table child-dt edit-dt"
						:rowHover="false"
						editMode="cell"
						@cell-edit-complete="onCellEditComplete(ct, $event)"
					>
						<Column
							v-for="col in ct.columns"
							:key="col.fieldname"
							:field="col.fieldname"
							:header="col.label + (col.reqd ? ' *' : '')"
						>
							<template #body="{ data, field }">
								<span :class="{ 'mgk-mono': col.input === 'link' }">
									{{ childCellDisplay(data[field], col) }}
								</span>
							</template>
							<template #editor="{ data, field }">
								<InputNumber
									v-if="col.input === 'number'"
									v-model="data[field]"
									:minFractionDigits="col.minFraction"
									:maxFractionDigits="col.maxFraction"
									class="cell-input"
									fluid
									autofocus
								/>
								<AutoComplete
									v-else-if="col.input === 'link'"
									v-model="data[field]"
									:suggestions="childLinkSuggestions"
									@complete="onChildLinkComplete(col, $event)"
									dropdown
									class="cell-input"
									fluid
									autofocus
								/>
								<InputText
									v-else
									v-model="data[field]"
									class="cell-input"
									fluid
									autofocus
								/>
							</template>
						</Column>

						<Column :style="{ width: '56px' }" bodyStyle="text-align:center">
							<template #body="{ index }">
								<Button
									icon="pi pi-trash"
									text
									rounded
									severity="danger"
									size="small"
									@click="removeChildRow(ct, index)"
								/>
							</template>
						</Column>

						<template #empty>
							<div class="table-empty">
								{{ ct.columnsAvailable ? "No rows. Use “Add Row”." : "Editing this table isn’t available here — open in Desk." }}
							</div>
						</template>
					</DataTable>
				</div>
			</div>
		</div>

		<!-- ════════════════ VIEW BODY ════════════════ -->
		<div v-else-if="doc" class="detail-layout">
			<!-- Main pane: tabs -->
			<div class="detail-main">
				<Tabs v-model:value="activeTab">
					<TabList>
						<Tab value="details">Details</Tab>
						<Tab v-for="ct in childTables" :key="ct.fieldname" :value="ct.fieldname">
							{{ ct.label }}
							<span v-if="tabBadge(ct)" class="tab-badge">{{ tabBadge(ct) }}</span>
						</Tab>
						<Tab v-if="isWorkOrder" value="approval">
							Approval Log
							<span v-if="approvalLog.length" class="tab-badge">{{ approvalLog.length }}</span>
						</Tab>
						<Tab value="linked">
							Linked Documents
							<span v-if="linkedTotal" class="tab-badge">{{ linkedTotal }}</span>
						</Tab>
						<Tab value="activity">Activity</Tab>
					</TabList>

					<TabPanels>
						<!-- DETAILS -->
						<TabPanel value="details">
							<div class="field-grid">
								<div v-for="f in detailFields" :key="f.fieldname" class="field">
									<label class="field-label">{{ f.label }}</label>
									<div
										class="field-value"
										:class="{ link: f.isLink, mgkmono: f.isLink }"
										@click="f.isLink && navigateLink(f, doc[f.fieldname])"
									>
										{{ displayValue(doc[f.fieldname], f.type) }}
									</div>
								</div>
								<div v-if="!detailFields.length" class="empty-inline">
									No displayable fields.
								</div>
							</div>
						</TabPanel>

						<!-- CHILD TABLES (one panel each) -->
						<TabPanel v-for="ct in childTables" :key="ct.fieldname" :value="ct.fieldname">
							<!-- #B: stock-grouped child tables show the read-only grouped pivot
							     (item → attributes → sizes), same as edit mode -->
							<StockItemGridEditor
								v-if="pivotChildFields.has(ct.fieldname)"
								:editable="false"
								:grouped-field="pivotFor(ct.fieldname)?.groupedField"
								:value-fields="pivotFor(ct.fieldname)?.valueFields || []"
								:entry-fields="pivotFor(ct.fieldname)?.entryFields || []"
								:cell-fields="pivotFor(ct.fieldname)?.cellFields || []"
								:initial-data="viewGrouped[ct.fieldname] || []"
							/>
							<DataTable
								v-else
								:value="rowsFor(ct)"
								class="mgk-table child-dt"
								:rowHover="false"
								dataKey="name"
							>
								<Column
									v-for="col in ct.columns"
									:key="col.fieldname"
									:field="col.fieldname"
									:header="col.label"
								>
									<template #body="{ data }">
										<span :class="{ 'mgk-mono': col.isLink }">
											{{ displayValue(data[col.fieldname], col.type) }}
										</span>
									</template>
								</Column>
								<template #empty>
									<div class="table-empty">No rows.</div>
								</template>
							</DataTable>
						</TabPanel>

						<!-- APPROVAL LOG (Work Order) -->
						<TabPanel v-if="isWorkOrder" value="approval">
							<Timeline
								v-if="approvalLog.length"
								:value="approvalLog"
								class="mgk-timeline"
							>
								<template #marker="{ item }">
									<span class="tl-dot" :class="item.action === 'Rejected' ? 'danger' : 'good'">
										<i :class="item.action === 'Rejected' ? 'pi pi-times' : 'pi pi-check'" />
									</span>
								</template>
								<template #content="{ item }">
									<div class="tl-when">
										{{ formatDateTime(item.action_at) }} · {{ item.action_by }}
									</div>
									<div class="tl-msg">
										<b :class="item.action === 'Rejected' ? 'txt-danger' : 'txt-good'">{{ item.action }}</b>
										<span v-if="item.reason"> — <i>"{{ item.reason }}"</i></span>
									</div>
								</template>
							</Timeline>
							<div v-else class="empty-inline">
								No approval actions recorded yet.
							</div>
							<p class="tab-footnote">
								Every Approve / Reject appends a row to <code>mgk_approval_log</code>
								(action · by · timestamp · reason). The latest action drives the
								<code>before_submit</code> gate.
							</p>
						</TabPanel>

						<!-- LINKED DOCUMENTS -->
						<TabPanel value="linked">
							<div v-if="linkedLoading" class="state-block sm">
								<i class="pi pi-spin pi-spinner" /> <span>Finding linked documents…</span>
							</div>
							<div v-else-if="linkedGroups.length" class="linked-panel">
								<div v-for="g in linkedGroups" :key="g.doctype" class="linked-group">
									<div class="linked-group-head">
										<h5>{{ g.doctype }}</h5>
										<span class="count">{{ g.rows.length }}</span>
									</div>
									<a
										v-for="row in g.rows"
										:key="row.name"
										class="linked-row"
										@click="navigateDoc(g.doctype, row.name)"
									>
										<span class="lr-id mgk-mono">{{ row.name }}</span>
										<span class="lr-meta">{{ linkedRowMeta(row) }}</span>
										<span class="lr-arrow"><i class="pi pi-arrow-right" /></span>
									</a>
								</div>
							</div>
							<div v-else class="empty-inline">
								No documents link to this {{ registry?.label || doctype }} yet.
							</div>
						</TabPanel>

						<!-- ACTIVITY -->
						<TabPanel value="activity">
							<div v-if="activityLoading" class="state-block sm">
								<i class="pi pi-spin pi-spinner" /> <span>Loading activity…</span>
							</div>
							<Timeline
								v-else-if="activityEvents.length"
								:value="activityEvents"
								class="mgk-timeline"
							>
								<template #marker="{ item }">
									<span class="tl-dot" :class="item.tone">
										<i :class="item.icon" />
									</span>
								</template>
								<template #content="{ item }">
									<div class="tl-when">{{ formatDateTime(item.when) }} · {{ item.who }}</div>
									<div class="tl-msg" v-html="item.text" />
								</template>
							</Timeline>
							<div v-else class="empty-inline">No activity recorded.</div>
						</TabPanel>
					</TabPanels>
				</Tabs>
			</div>

			<!-- SIDE PANEL -->
			<aside class="detail-side">
				<!-- WO design-approval summary -->
				<Card v-if="isWorkOrder && approvalState && approvalState.needs_approval" class="side-card">
					<template #title><span class="side-title">Design Approval</span></template>
					<template #content>
						<div class="meta-row">
							<span class="k">Role</span>
							<span class="v">{{ approvalState.approver_role }}</span>
						</div>
						<div class="meta-row">
							<span class="k">Status</span>
							<span class="v">
								<Tag
									:value="approvalState.approved_by ? 'Approved' : (approvalState.rejection_reason ? 'Rejected' : 'Awaiting')"
									:severity="approvalState.approved_by ? 'success' : (approvalState.rejection_reason ? 'danger' : 'warn')"
									rounded
								/>
							</span>
						</div>
						<div v-if="approvalState.approved_by" class="meta-row">
							<span class="k">Approved by</span>
							<span class="v">{{ approvalState.approved_by }}</span>
						</div>
						<div v-if="approvalState.rejection_reason" class="meta-row col">
							<span class="k">Reason</span>
							<span class="v reason">{{ approvalState.rejection_reason }}</span>
						</div>
						<div class="meta-row">
							<span class="k">Submit</span>
							<span class="v" :class="approvalState.approved_by ? 'txt-good' : 'txt-danger'">
								{{ approvalState.approved_by ? "Unblocked" : "Blocked" }}
							</span>
						</div>
					</template>
				</Card>

				<!-- Quick Info -->
				<Card class="side-card">
					<template #title><span class="side-title">Quick Info</span></template>
					<template #content>
						<div v-for="m in quickInfo" :key="m.label" class="meta-row">
							<span class="k">{{ m.label }}</span>
							<span class="v">{{ m.value }}</span>
						</div>
						<div v-if="!quickInfo.length" class="empty-inline sm">No summary fields.</div>
					</template>
				</Card>

				<!-- Linked summary -->
				<Card class="side-card">
					<template #title><span class="side-title">Linked Summary</span></template>
					<template #content>
						<div v-if="linkedLoading" class="empty-inline sm">Loading…</div>
						<template v-else-if="linkedGroups.length">
							<a
								v-for="g in linkedGroups"
								:key="g.doctype"
								class="meta-row link-row"
								@click="goToFirst(g)"
							>
								<span class="k">{{ g.doctype }}</span>
								<span class="v count-pill">{{ g.rows.length }}</span>
							</a>
						</template>
						<div v-else class="empty-inline sm">No linked documents.</div>
					</template>
				</Card>
			</aside>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue"
import { useRouter } from "vue-router"
import Tabs from "primevue/tabs"
import TabList from "primevue/tablist"
import Tab from "primevue/tab"
import TabPanels from "primevue/tabpanels"
import TabPanel from "primevue/tabpanel"
import DataTable from "primevue/datatable"
import Column from "primevue/column"
import Tag from "primevue/tag"
import Timeline from "primevue/timeline"
import Card from "primevue/card"
import Button from "primevue/button"
import Message from "primevue/message"
import InputText from "primevue/inputtext"
import Textarea from "primevue/textarea"
import InputNumber from "primevue/inputnumber"
import DatePicker from "primevue/datepicker"
import ToggleSwitch from "primevue/toggleswitch"
import Select from "primevue/select"
import AutoComplete from "primevue/autocomplete"
import { useDoc } from "@/composables/useDoc"
import { usePermissions } from "@/composables/usePermissions"
import { useAppConfirm } from "@/composables/useConfirm"
import { useAppToast } from "@/composables/useToast"
import { searchLink, getMeta, getDocWithOnload, callMethod } from "@/api/client"
import { getRegistryByRoute, getRegistryByDoctype, WORKFLOW_SEVERITY } from "@/config/doctypes"
import { getFieldConfig } from "@/config/fields"
import WorkOrderApproval from "./WorkOrderApproval.vue"
import StockItemGridEditor from "./StockItemGridEditor.vue"
import LinkField from "@/components/LinkField.vue"
import GRNReceivedTypeEditor from "./GRNReceivedTypeEditor.vue"
import WorkflowActions from "./WorkflowActions.vue"

const props = defineProps({
	docRoute: { type: String, required: true },
	id: { type: String, required: true },
})

const router = useRouter()
const { canWrite, canCreate, canDelete, canSubmit, canCancel, canAmend, isAdmin, hasRole } = usePermissions()
const confirm = useAppConfirm()
const toast = useAppToast()

const registry = computed(() => getRegistryByRoute(props.docRoute))
const doctype = computed(() => registry.value?.doctype || "")
const isWorkOrder = computed(() => doctype.value === "Work Order")
const isSubmittable = computed(() => registry.value?.isSubmittable || false)
const isWorkflow = computed(() => registry.value?.isWorkflow || false)

// ── doc state ──
// doctype is captured once at setup; correct only because AppLayout keys <router-view> by $route.path, remounting per doctype/record. Do not remove that :key.
const docState = useDoc(doctype.value)
const doc = docState.doc
const meta = docState.meta
const loading = docState.loading
const metaLoading = docState.metaLoading
const linkedLoading = docState.linkedLoading
const activityLoading = docState.activityLoading
const saving = docState.saving
const error = docState.error

// ── mode: "view" | "edit" | "create" ──
const isCreate = computed(() => props.id === "new")
const mode = ref("view")
const isFormMode = computed(() => mode.value === "edit" || mode.value === "create")
const acting = ref(null) // "submit" | "cancel" | "delete" | "amend" | null

const activeTab = ref("details")
const approvalRef = ref(null)
const approvalState = ref(null)
const workflowRef = ref(null)

// Reactive form model for edit/create (built fresh on entering those modes).
const form = reactive({})
// Per-field Link autocomplete suggestion buffers (parent fields).
const linkSuggestions = reactive({})
// Shared buffer for the child-grid Link cell autocomplete (one cell edits at a time).
const childLinkSuggestions = ref([])
// Child-DocType meta indexed by DocType name (from the getdoctype bundle tail).
// Gives the edit/create child grids typed columns (esp. in create, no rows).
const childMetaCache = ref({})

// docstatus convenience.
const docstatus = computed(() => Number(doc.value?.docstatus) || 0)

// System fields we never surface in the Details grid / Quick Info / form.
const SYSTEM_FIELDS = new Set([
	"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx",
	"doctype", "parent", "parentfield", "parenttype", "_user_tags", "_comments",
	"_assign", "_liked_by", "_seen", "_comment_count", "title_field",
	"deliverable_details", "receivable_details", "amended_from",
])
const META_HIDDEN_FIELDTYPES = new Set([
	"Section Break", "Column Break", "Tab Break", "HTML", "Heading", "Button",
	"Fold", "Image", "Geolocation", "Signature", "Table", "Table MultiSelect",
])
// Hidden grouped-JSON fields — NEVER editable / sent (the flat-rows contract).
const GROUPED_JSON_FIELDS = new Set([
	"item_details", "deliverable_details", "receivable_details",
])
// Child tables with a dedicated surface elsewhere → kept out of the generic
// per-child-table tabs AND the edit grids. `mgk_approval_log` already renders as
// the Approval Log timeline (view) and is written only by the approve/reject API.
const CHILD_TABLE_EXCLUDE = new Set(["mgk_approval_log"])

// ── R3a: stock size-pivot (grouped item_details) opt-in ──────────────────────
// For these stock-voucher doctypes ONLY, edit/create renders the grouped pivot
// editor (StockItemGridEditor) INSTEAD of the flat child grid, and buildPayload
// emits grouped JSON into the grouped field + sends an EMPTY flat child array
// (the OPPOSITE of the flat path — each voucher's before_validate then runs
// ungroup_items_from_ui to resolve/create variants server-side).
//
// `ungroupKey` is the parent_doctype string PARENT_CHILD_MAP keys on; valueFields/
// entryFields are mirrored from PARENT_CHILD_MAP so the per-cell / per-row extra
// fields round-trip. Each entry = one pivot section in the form.
// Every OTHER doctype is untouched (flat grid + empty grouped JSON, as before).
const STOCK_GROUPED_MAP = {
	"Stock Entry": [{
		childField: "items", groupedField: "item_details", ungroupKey: "Stock Entry",
		label: "Items", valueFields: ["rate", "secondary_qty", "secondary_uom"],
		entryFields: ["allow_zero_valuation_rate", "make_qty_zero"],
	}],
	"Stock Update": [{
		childField: "stock_update_details", groupedField: "item_details", ungroupKey: "Stock Update",
		label: "Stock Update Details", valueFields: ["rate", "secondary_qty", "secondary_uom"],
		entryFields: ["allow_zero_valuation_rate", "make_qty_zero"],
	}],
	"Stock Reconciliation": [{
		childField: "items", groupedField: "item_details", ungroupKey: "Stock Reconciliation",
		label: "Items", valueFields: ["rate", "secondary_qty", "secondary_uom"],
		entryFields: ["allow_zero_valuation_rate", "make_qty_zero"],
	}],
	"Delivery Challan": [{
		childField: "items", groupedField: "item_details", ungroupKey: "Delivery Challan",
		label: "Items",
		valueFields: [
			"rate", "valuation_rate", "pending_quantity", "delivered_quantity",
			"received_quantity", "stock_qty", "amount", "ref_doctype", "ref_docname",
			"secondary_qty", "secondary_uom",
		],
		entryFields: ["stock_uom", "conversion_factor", "set_combination", "comments"],
	}],
	"Goods Received Note": [{
		childField: "items", groupedField: "item_details", ungroupKey: "Goods Received Note",
		label: "Items",
		valueFields: [
			"rate", "pending_quantity", "max_receivable_quantity", "stock_qty", "amount",
			"ref_doctype", "ref_docname", "delivery_challan_item",
			"secondary_qty", "secondary_uom",
		],
		entryFields: [
			"stock_uom", "conversion_factor", "ref_doctype", "ref_docname",
			"delivery_challan_item", "set_combination", "comments",
		],
	}],
	"Purchase Order": [{
		childField: "items", groupedField: "item_details", ungroupKey: "Purchase Order",
		label: "Items",
		cellFields: [{ name: "rate", label: "Rate" }, { name: "pending_quantity", label: "Pending" }, { name: "total_amount", label: "Amount" }],
		valueFields: [
			"rate", "pending_quantity", "received_quantity", "cancelled_quantity",
			"stock_qty", "amount", "discount_amount", "tax_amount", "total_amount",
			"secondary_qty", "secondary_uom",
		],
		entryFields: [
			"stock_uom", "conversion_factor", "delivery_date", "tax",
			"discount_percentage", "set_combination", "comments",
		],
	}],
	"Work Order": [
		{
			childField: "deliverables", groupedField: "deliverable_details",
			ungroupKey: "Work Order Deliverables", label: "Deliverables",
			cellFields: [{ name: "pending_quantity", label: "Pending" }],
			valueFields: ["pending_quantity", "stock_update", "valuation_rate"],
			entryFields: [
				"comments", "secondary_qty", "secondary_uom", "cancelled_quantity",
				"additional_parameters", "set_combination", "grn_detail_no", "item_type",
				"is_calculated", "source_grn", "source_grn_item", "source_inspection_entry_item",
			],
		},
		{
			childField: "receivables", groupedField: "receivable_details",
			ungroupKey: "Work Order Receivables", label: "Receivables",
			cellFields: [{ name: "cost", label: "Cost" }, { name: "pending_quantity", label: "Pending" }],
			valueFields: ["cost", "pending_quantity", "total_cost"],
			entryFields: [
				"comments", "secondary_qty", "secondary_uom", "process_cost",
				"additional_parameters", "set_combination",
			],
		},
	],
}

// The pivot sections to render for the current doctype (empty ⇒ flat path).
const stockPivots = computed(() => STOCK_GROUPED_MAP[doctype.value] || [])
const useStockPivot = computed(() => isFormMode.value && stockPivots.value.length > 0)

// R3b: Goods Received Note against a Work Order uses the received-type-SPLIT
// editor (GRNReceivedTypeEditor) instead of the generic size-pivot — mirrors the
// Desk's useReceivedTypeGrnEditor gate (editorType === goods_received_note &&
// against === "Work Order"). GRN-against-Purchase-Order (or a GRN with no source
// yet, e.g. create mode where doc.against is unset) keeps the generic pivot.
// `against` comes from the loaded doc; both editors share the gridRefs surface so
// hydratePivotsForEdit + buildPayload work for either.
const useGrnSplit = computed(
	() => doctype.value === "Goods Received Note" && (form.against || doc.value?.against) === "Work Order",
)

// Per-section refs to the mounted grid editors (keyed by childField), so onSave
// can pull each section's grouped JSON via getItems(). Plain object (not reactive)
// — we only call imperative methods on the instances, never render them.
const gridRefs = {}
function setGridRef(childField, el) {
	if (el) gridRefs[childField] = el
	else delete gridRefs[childField]
}

// The set of flat child fields the pivot replaces — used to drop their flat
// editors AND to blank them in the payload so the server rebuilds from grouped.
const pivotChildFields = computed(
	() => new Set(stockPivots.value.map((p) => p.childField)),
)

// VIEW mode (#B): render the read-only grouped pivot (same shape as edit) instead
// of flat item_variant rows. The grouped JSON comes from the doc's onload.
const viewGrouped = ref({})
function pivotFor(fieldname) {
	return stockPivots.value.find((p) => p.childField === fieldname) || null
}
// An entry has no value (for the READ-ONLY view) when every size cell is zero
// qty AND every read-only cell value (Pending/Cost…) is zero too. The server pads
// grouped item_details with extra entries (e.g. one per GRN received type) so the
// EDIT split-editor can offer them — those padded all-zero entries are NOT stored,
// so we drop them from the view rather than render empty rows. A pending-only row
// (WO receivable: qty 0 but Pending > 0) is kept.
function entryHasNoValue(entry, cellFields) {
	const vals = entry?.values || {}
	for (const pv of Object.keys(vals)) {
		const cell = vals[pv] || {}
		if (Number(cell.qty)) return false
		for (const cf of cellFields || []) {
			if (Number(cell[cf.name])) return false
		}
	}
	return true
}

async function hydratePivotsForView() {
	if (!stockPivots.value.length) return
	try {
		const loaded = await getDocWithOnload(doctype.value, props.id)
		const onload = loaded?.__onload || {}
		const next = {}
		for (const pv of stockPivots.value) {
			const grouped = onload[pv.groupedField]
			const groups = grouped != null ? grouped : []
			// Drop padded all-zero entries (e.g. GRN received types with no qty) so
			// the read-only view shows only what's actually recorded.
			next[pv.childField] = groups
				.map((grp) => ({
					...grp,
					items: (grp.items || []).filter((e) => !entryHasNoValue(e, pv.cellFields || [])),
				}))
				.filter((grp) => (grp.items || []).length)
		}
		viewGrouped.value = next
	} catch (_) {
		viewGrouped.value = {}
	}
}

// ── load orchestration ──
async function loadAll() {
	if (!doctype.value) return
	approvalState.value = null
	acting.value = null

	if (isCreate.value) {
		// Create mode: meta only, then build a blank form. No doc/linked/activity.
		mode.value = "create"
		await docState.loadMeta()
		await loadChildMetas()
		buildCreateForm()
		return
	}

	mode.value = "view"
	activeTab.value = "details"
	// Meta first (gives field labels + child-table descriptors), then doc.
	docState.loadMeta()
	loadChildMetas()
	await docState.load(props.id)
	if (!docState.doc.value) return
	// U1: transaction docs open on their primary items tab (Deliverables/Items),
	// not the meta Details tab — so the core content is visible immediately.
	if (stockPivots.value.length) {
		activeTab.value = stockPivots.value[0].childField
		hydratePivotsForView()
	}
	docState.loadLinked(props.id)
	docState.loadActivity(props.id)
}

// The getdoctype bundle is [parentMeta, ...childMetas] keyed by DocType name.
// useDoc.loadMeta keeps only the parent; we index the child metas here so the
// edit/create child-table grids get proper, typed columns (esp. in create mode
// where no rows exist to infer columns from). Fetched once per doctype.
const childMetasLoaded = ref(false)
async function loadChildMetas() {
	if (childMetasLoaded.value || !doctype.value) return
	try {
		const bundle = await getMeta(doctype.value)
		const cache = {}
		for (const m of bundle) {
			if (m?.name) cache[m.name] = m
		}
		childMetaCache.value = cache
		childMetasLoaded.value = true
	} catch (_) {
		// Non-fatal: child grids fall back to row-inferred columns.
	}
}

watch(
	() => [props.docRoute, props.id],
	() => loadAll(),
	{ immediate: false },
)
onMounted(loadAll)

// ── Keyboard shortcuts (permission-gated) ──
// Ctrl/Cmd+S: in edit/create → Save; on a saved draft (view) → Submit (confirm).
// Ctrl/Cmd+D: on a submitted doc (view) → Cancel (confirm). Each fires only when
// the user holds the matching permission; the Submit/Cancel popups are the same
// confirm dialogs the buttons use.
function onShortcut(e) {
	if (!(e.ctrlKey || e.metaKey)) return
	const key = (e.key || "").toLowerCase()
	if (key === "s") {
		e.preventDefault()
		if (saving.value || acting.value) return
		if (isFormMode.value) {
			const allowed = mode.value === "create" ? canCreate(doctype.value) : canWrite(doctype.value)
			if (allowed) onSave()
		} else if (doc.value && docstatus.value === 0 && isSubmittable.value && canSubmit(doctype.value)) {
			// Workflow doctypes (isSubmittable=false) are excluded here by design —
			// they submit via WorkflowActions, never a plain docstatus PUT.
			onSubmit()
		}
	} else if (key === "d") {
		e.preventDefault()
		if (acting.value || isFormMode.value || !doc.value) return
		if (docstatus.value === 1 && isSubmittable.value && canCancel(doctype.value)) {
			onCancel() // submitted → Cancel confirmation
		} else if (docstatus.value === 0 && canDelete(doctype.value)) {
			onDelete() // saved draft → Delete confirmation
		}
	}
}
onMounted(() => window.addEventListener("keydown", onShortcut))
onBeforeUnmount(() => window.removeEventListener("keydown", onShortcut))

// ── meta field map ──
const metaFieldMap = computed(() => {
	const map = {}
	for (const f of meta.value?.fields || []) map[f.fieldname] = f
	return map
})

function linkTypeFor(fieldname) {
	const mf = metaFieldMap.value[fieldname]
	return mf?.fieldtype === "Link"
}

// ════════════════ EDIT / CREATE: editable field descriptors ════════════════

// Map a meta fieldtype to an input kind + formatting hints.
function inputDescriptor(mf) {
	const ft = mf.fieldtype
	const base = {
		fieldname: mf.fieldname,
		label: mf.label || humanize(mf.fieldname),
		reqd: !!mf.reqd,
		readOnly: !!mf.read_only,
		fieldtype: ft,
		input: "text",
		wide: false,
		dependsOn: mf.depends_on || "",
		mandatoryDependsOn: mf.mandatory_depends_on || "",
		readOnlyDependsOn: mf.read_only_depends_on || "",
		fetchFrom: mf.fetch_from || "",
	}
	if (ft === "Data" || ft === "Small Text") return { ...base, input: "text" }
	if (ft === "Text" || ft === "Long Text" || ft === "Code" || ft === "Text Editor" || ft === "Markdown Editor") {
		return { ...base, input: "textarea", wide: true }
	}
	if (ft === "Int") return { ...base, input: "number", minFraction: 0, maxFraction: 0 }
	if (ft === "Float") return { ...base, input: "number", minFraction: 0, maxFraction: 6 }
	if (ft === "Percent") return { ...base, input: "number", minFraction: 0, maxFraction: 2, suffix: " %" }
	if (ft === "Currency") return { ...base, input: "number", minFraction: 2, maxFraction: 2 }
	if (ft === "Date") return { ...base, input: "date" }
	if (ft === "Datetime") return { ...base, input: "datetime" }
	if (ft === "Time") return { ...base, input: "time" }
	if (ft === "Check") return { ...base, input: "check" }
	if (ft === "Select") {
		const options = String(mf.options || "")
			.split("\n")
			.map((s) => s.trim())
			.filter((s) => s !== "")
		return { ...base, input: "select", options }
	}
	if (ft === "Link" || ft === "Dynamic Link") {
		// Dynamic Link: `options` is the FIELDNAME holding the target doctype
		// (resolved from the form at search time), not a fixed doctype.
		const dynamic = ft === "Dynamic Link"
		return {
			...base,
			input: "link",
			linkTarget: dynamic ? "" : (mf.options || ""),
			isDynamic: dynamic,
			dynamicField: dynamic ? (mf.options || "") : "",
		}
	}
	// Unhandled-but-editable scalar fieldtypes fall back to a text input.
	return base
}

// The ordered, editable field list for the form. Drives create + edit.
// Order: per-doctype config (when present) → meta order. Either way the
// fieldtype/required/read-only come from meta (config only carries display type).
const formFields = computed(() => {
	if (!isFormMode.value) return []
	const mfMap = metaFieldMap.value
	if (!Object.keys(mfMap).length) return []

	const out = []
	const seen = new Set()
	const pushByFieldname = (fn) => {
		if (seen.has(fn)) return
		const mf = mfMap[fn]
		if (!mf) return
		if (!isEditableMetaField(mf)) return
		seen.add(fn)
		out.push(inputDescriptor(mf))
	}

	const cfg = getFieldConfig(doctype.value)
	if (cfg) {
		for (const f of cfg) pushByFieldname(f.fieldname)
		// Append any remaining editable meta fields not covered by config, so
		// nothing required is silently un-editable.
		for (const mf of meta.value.fields) pushByFieldname(mf.fieldname)
		return out
	}

	for (const mf of meta.value.fields) pushByFieldname(mf.fieldname)
	return out
})

// Evaluate a Frappe depends_on / mandatory_depends_on expression against the live
// `form` model. `eval:<js>` runs the JS with `doc` = form; a bare fieldname is
// truthy when that field is set. A bad/odd expression fails open (shows the field).
function evalCondition(expr) {
	const raw = String(expr || "").trim()
	if (!raw) return true
	if (raw.startsWith("eval:")) {
		try {
			return !!Function("doc", `"use strict"; return (${raw.slice(5)});`)(form)
		} catch (_) {
			return true
		}
	}
	return !!form[raw]
}

// reqd is the static meta flag OR a currently-satisfied mandatory_depends_on.
function isReqd(f) {
	if (f.reqd) return true
	return f.mandatoryDependsOn ? evalCondition(f.mandatoryDependsOn) : false
}

// read_only = the static meta flag OR a satisfied read_only_depends_on (e.g.
// posting_date/time stay read-only until "Edit Posting Date and Time" is ticked).
// Reads `form` so it re-evaluates reactively as the user toggles.
function isReadOnly(f) {
	if (f.readOnly) return true
	return f.readOnlyDependsOn ? evalCondition(f.readOnlyDependsOn) : false
}

// The form fields actually shown: drop any whose depends_on is currently false,
// AND drop READ-ONLY fields that still have no value (derived/auto-filled fields
// don't clutter the form — each reappears the instant it gets a value). Editable
// empty fields always show — the user needs them to enter data. Reads `form` (via
// evalCondition / the value lookup) so it re-filters reactively as the user edits.
const visibleFormFields = computed(() =>
	formFields.value.filter((f) => {
		if (f.dependsOn && !evalCondition(f.dependsOn)) return false
		// U4: in CREATE mode, read-only fields are system/derived (e.g. Open Status,
		// Is Delivered) — never show them, even when they carry a default. In EDIT a
		// read-only field is hidden only when empty (derived / not-yet-set).
		if (isReadOnly(f)) {
			if (mode.value === "create") return false
			if (isEmptyForHide(form[f.fieldname], metaFieldMap.value[f.fieldname]?.fieldtype)) return false
		}
		return true
	}),
)

function isEditableMetaField(mf) {
	if (META_HIDDEN_FIELDTYPES.has(mf.fieldtype)) return false
	if (SYSTEM_FIELDS.has(mf.fieldname)) return false
	if (GROUPED_JSON_FIELDS.has(mf.fieldname)) return false
	if (mf.hidden) return false
	return true
}

// Missing-required check (used to mark inputs invalid + block save).
function isMissing(f) {
	if (!isReqd(f)) return false
	const v = form[f.fieldname]
	return v === null || v === undefined || v === ""
}

// ── form builders ──
function blankValueFor(mf) {
	// Honour meta default when present.
	if (mf.default !== undefined && mf.default !== null && mf.default !== "") {
		if (mf.fieldtype === "Check") return Number(mf.default) ? 1 : 0
		if (["Int", "Float", "Percent", "Currency"].includes(mf.fieldtype)) {
			const n = Number(mf.default)
			return Number.isNaN(n) ? null : n
		}
		// Resolve Frappe dynamic defaults so date/time inputs get a real value,
		// not the literal "Today"/"Now" string (the posting_time="Now" bug).
		if (mf.fieldtype === "Date" && mf.default === "Today") return fromDateObj(new Date(), false)
		if (mf.fieldtype === "Datetime" && mf.default === "Now") return fromDateObj(new Date(), true)
		if (mf.fieldtype === "Time" && mf.default === "Now") return nowTimeStr()
		return mf.default
	}
	if (mf.fieldtype === "Check") return 0
	if (["Int", "Float", "Percent", "Currency"].includes(mf.fieldtype)) return null
	return ""
}

function clearForm() {
	for (const k of Object.keys(form)) delete form[k]
}

function buildCreateForm() {
	clearForm()
	for (const mf of meta.value?.fields || []) {
		if (META_HIDDEN_FIELDTYPES.has(mf.fieldtype)) continue
		if (SYSTEM_FIELDS.has(mf.fieldname)) continue
		if (GROUPED_JSON_FIELDS.has(mf.fieldname)) continue
		if (mf.hidden) continue
		form[mf.fieldname] = blankValueFor(mf)
	}
	// Initialise editable child tables to empty arrays.
	for (const ct of editableChildTables.value) {
		form[ct.fieldname] = []
	}
}

function buildEditForm() {
	clearForm()
	const src = doc.value || {}
	// Deep copy scalar + child-table values from the doc.
	for (const [k, v] of Object.entries(src)) {
		if (Array.isArray(v)) {
			form[k] = v.map((row) => ({ ...row }))
		} else if (v && typeof v === "object") {
			form[k] = { ...v }
		} else {
			form[k] = v
		}
	}
}

async function enterEdit() {
	if (!doc.value) return
	buildEditForm()
	mode.value = "edit"
	// R3a: for stock-pivot doctypes, hydrate each grid from the doc's grouped
	// onload JSON (frappe.client.get used for `doc` does NOT carry __onload, so
	// we fetch via getdoc — the same path the Desk uses). Without this the grid
	// would start empty and saving would wipe the existing rows.
	if (useStockPivot.value) await hydratePivotsForEdit()
}

// Fetch the grouped item_details/deliverable_details/receivable_details from the
// server onload and push them into the mounted grid editors. Best-effort: a load
// failure leaves the grids empty (the user can re-enter), but we keep the flat
// rows on the doc untouched until an actual save.
async function hydratePivotsForEdit() {
	try {
		const loaded = await getDocWithOnload(doctype.value, props.id)
		const onload = loaded?.__onload || {}
		await nextTick()
		for (const pv of stockPivots.value) {
			const grid = gridRefs[pv.childField]
			const grouped = onload[pv.groupedField]
			if (grid?.loadData && grouped != null) grid.loadData(grouped)
		}
	} catch (e) {
		toast.warn("Could not load existing items", "Re-enter the items before saving, or edit in Desk.")
	}
}

// ════════════════ EDITABLE CHILD TABLES ════════════════

// Editable child tables = meta Table fields, minus the hidden grouped-JSON
// twins. Columns come from the child DocType's meta (in the bundle) when
// available, else from the first existing row.
const editableChildTables = computed(() => {
	if (!isFormMode.value) return []
	const pivotFields = pivotChildFields.value
	const metaTables = (meta.value?.fields || []).filter(
		(f) =>
			f.fieldtype === "Table" &&
			!f.hidden &&
			!GROUPED_JSON_FIELDS.has(f.fieldname) &&
			!CHILD_TABLE_EXCLUDE.has(f.fieldname) &&
			// R3a: stock-pivot doctypes edit these child tables through the grouped
			// pivot editor, not the flat grid — drop them here for those doctypes only.
			!pivotFields.has(f.fieldname),
	)
	const out = []
	for (const tf of metaTables) {
		const columns = childEditColumns(tf)
		out.push({
			fieldname: tf.fieldname,
			label: tf.label || humanize(tf.fieldname),
			childDoctype: tf.options || "",
			columns,
			// No columns ⇒ neither child meta nor existing rows gave us a reliable
			// shape. The editor disables Add Row and points the user to Desk.
			columnsAvailable: columns.length > 0,
		})
	}
	return out
})

// Build the editable columns for a child table: prefer the cached child-DocType
// meta (typed columns even with no rows — needed for create), then fall back to
// inferring from existing rows, then a single generic column.
function childEditColumns(tableField) {
	const childDt = tableField.options
	// 1) Prefer child-doctype meta if we have it cached.
	const cmeta = childMetaCache.value[childDt]
	if (cmeta?.fields?.length) {
		const cols = []
		for (const mf of cmeta.fields) {
			if (!isEditableChildField(mf)) continue
			const d = inputDescriptor(mf)
			cols.push({
				fieldname: mf.fieldname,
				label: mf.label || humanize(mf.fieldname),
				input: childInputKind(d.input),
				reqd: !!mf.reqd,
				type: mfTypeToDisplay(mf.fieldtype),
				isLink: mf.fieldtype === "Link",
				linkTarget: mf.options || "",
				minFraction: d.minFraction,
				maxFraction: d.maxFraction,
			})
		}
		if (cols.length) return cols.slice(0, 10)
	}
	// 2) Fallback: derive from existing rows on the form/doc.
	const rows = form[tableField.fieldname] || doc.value?.[tableField.fieldname] || []
	if (rows.length) {
		const keys = []
		for (const k of Object.keys(rows[0])) {
			if (CHILD_HIDDEN.has(k)) continue
			const v = rows[0][k]
			if (v && typeof v === "object") continue
			keys.push(k)
		}
		return keys.slice(0, 10).map((k) => ({
			fieldname: k,
			label: humanize(k),
			input: typeof rows[0][k] === "number" ? "number" : "text",
			reqd: false,
			type: null,
			isLink: false,
		}))
	}
	// 3) No meta, no rows: we have no reliable column definition. Return nothing
	// rather than guessing a single column — the editor disables "Add Row" and
	// shows a "columns unavailable" note so we never persist wrong/incomplete data.
	return []
}

// Child cells only support scalar / link inputs in the flat v1 grid.
function childInputKind(parentInput) {
	if (parentInput === "number") return "number"
	if (parentInput === "link") return "link"
	return "text"
}

function isEditableChildField(mf) {
	if (META_HIDDEN_FIELDTYPES.has(mf.fieldtype)) return false
	if (CHILD_HIDDEN.has(mf.fieldname)) return false
	if (mf.hidden) return false
	// Only flat scalar / link cells in v1.
	const ok = ["Data", "Small Text", "Int", "Float", "Percent", "Currency", "Link", "Select", "Check"]
	return ok.includes(mf.fieldtype)
}

function addChildRow(ct) {
	if (!Array.isArray(form[ct.fieldname])) form[ct.fieldname] = []
	const row = {}
	for (const col of ct.columns) {
		row[col.fieldname] = col.input === "number" ? null : ""
	}
	form[ct.fieldname].push(row)
}

function removeChildRow(ct, index) {
	if (Array.isArray(form[ct.fieldname])) form[ct.fieldname].splice(index, 1)
}

function onCellEditComplete(ct, e) {
	// PrimeVue cell edit: commit the new value onto the row.
	const { data, newValue, field } = e
	if (data) data[field] = newValue
}

function childCellDisplay(val, col) {
	if (val === null || val === undefined || val === "") return "—"
	if (col.input === "number") return formatNumber(val)
	return String(val)
}

// ── Link autocomplete (parent fields) ──
// ════════════════ FIELD-CHANGE AUTO-FILL (mirror the Desk client scripts) ════
// (a) fetch_from — when a source field changes, copy source_doc.<field> into the
//     target (respecting fetch_if_empty); chained fetches cascade.
// (b) per-doctype header+items auto-fill via the same server methods the Desk
//     forms call (e.g. DC work_order → get_work_order_defaults → load deliverables).

// Targets whose fetch_from references `srcField`.
function fetchTargetsFor(srcField) {
	const out = []
	for (const mf of meta.value?.fields || []) {
		if (!mf.fetch_from) continue
		const dot = String(mf.fetch_from).indexOf(".")
		if (dot < 1 || mf.fetch_from.slice(0, dot) !== srcField) continue
		out.push({
			target: mf.fieldname,
			srcDocField: mf.fetch_from.slice(dot + 1),
			fetchIfEmpty: !!mf.fetch_if_empty,
		})
	}
	return out
}

// The doctype a (Dynamic) Link field points at.
function linkDoctypeOf(fieldname) {
	const mf = metaFieldMap.value[fieldname]
	if (!mf) return ""
	return mf.fieldtype === "Dynamic Link" ? (form[mf.options] || "") : (mf.options || "")
}

// Replicate Frappe's fetch_from for one source field, cascading to chained fetches.
async function applyFetchFrom(srcField) {
	const targets = fetchTargetsFor(srcField)
	if (!targets.length) return
	const srcValue = form[srcField]
	const srcDoctype = linkDoctypeOf(srcField)
	for (const t of targets) {
		if (!srcValue || !srcDoctype) {
			if (!t.fetchIfEmpty) form[t.target] = "" // source cleared → clear fetched
			continue
		}
		if (t.fetchIfEmpty && form[t.target]) continue // don't overwrite existing
		try {
			const r = await callMethod("frappe.client.get_value", {
				doctype: srcDoctype,
				filters: srcValue,
				fieldname: t.srcDocField,
			})
			form[t.target] = (r && r[t.srcDocField]) || ""
		} catch (_) {
			/* leave target as-is on lookup failure */
		}
		await applyFetchFrom(t.target) // cascade (warehouse → supplier → terms…)
	}
}

// Per-doctype header+items auto-fill (the heavy "pick a link → fill header + load
// the item grid" handlers). The server methods return { …header fields, items,
// item_details(grouped) }.
// Zero every cell qty in a grouped item_details payload (keeps pending/max so the
// clamp + display still work). Used so a GRN starts blank for data entry.
function zeroGroupedQtys(itemDetails) {
	for (const g of itemDetails || []) {
		for (const it of g.items || []) {
			for (const cell of Object.values(it.values || {})) {
				if (cell && typeof cell === "object") cell.qty = 0
			}
		}
	}
}

async function runDocAutofill(fieldname) {
	const dt = doctype.value
	let method = ""
	let args = null
	if (dt === "Delivery Challan" && fieldname === "work_order") {
		if (!form.work_order) return
		method = "yrp.yrp.doctype.delivery_challan.delivery_challan.get_work_order_defaults"
		args = { work_order: form.work_order, posting_date: form.posting_date, posting_time: form.posting_time }
	} else if (dt === "Goods Received Note" && (fieldname === "against_id" || fieldname === "delivery_challan")) {
		if (!form.against_id) return
		if (form.against === "Work Order") {
			method = "yrp.yrp.doctype.goods_received_note.goods_received_note.get_work_order_defaults"
			args = { work_order: form.against_id, delivery_challan: form.delivery_challan || "" }
		} else if (form.against === "Purchase Order") {
			method = "yrp.yrp.doctype.goods_received_note.goods_received_note.get_purchase_order_defaults"
			args = { purchase_order: form.against_id }
		} else return
	} else {
		return
	}
	try {
		const r = await callMethod(method, args)
		if (!r || typeof r !== "object") return
		for (const [k, v] of Object.entries(r)) {
			if (k === "items" || k === "item_details") continue
			if (k in form) form[k] = v // apply returned header fields
		}
		// GRN: start every received type at 0 so the user types the actual received
		// qty per row (total still clamped to pending) — no "all accepted" pre-fill.
		if (dt === "Goods Received Note") zeroGroupedQtys(r.item_details)
		await nextTick()
		for (const pv of stockPivots.value) {
			const grid = gridRefs[pv.childField]
			if (grid?.loadData && r.item_details != null) grid.loadData(r.item_details)
		}
	} catch (e) {
		toast.error("Auto-fill failed", e.message)
	}
}

// GRN: flipping `against` (Work Order ↔ Purchase Order) resets the source-derived
// header fields + the item grid (mirrors goods_received_note.js `against` handler).
function resetGrnSource() {
	for (const k of ["against_id", "delivery_challan", "process_name", "item", "production_detail", "supplier", "delivery_location", "from_warehouse", "to_warehouse", "is_rework"]) {
		if (k in form) form[k] = k === "is_rework" ? 0 : ""
	}
	for (const pv of stockPivots.value) gridRefs[pv.childField]?.loadData?.([])
}

// Wired on editable link/select inputs: cascade fetch_from + run doctype auto-fill.
async function onFieldChanged(fieldname) {
	await applyFetchFrom(fieldname)
	if (doctype.value === "Goods Received Note" && fieldname === "against") {
		resetGrnSource()
		return
	}
	await runDocAutofill(fieldname)
}

async function onLinkComplete(field, e) {
	// For a Dynamic Link the target doctype is whatever the controlling field
	// currently holds (e.g. against_id → form.against === "Work Order").
	const target = field.isDynamic ? (form[field.dynamicField] || "") : field.linkTarget
	if (!target) {
		linkSuggestions[field.fieldname] = []
		return
	}
	try {
		const rows = await searchLink(target, e.query || "")
		linkSuggestions[field.fieldname] = rows.map((r) => r.name)
	} catch (_) {
		linkSuggestions[field.fieldname] = []
	}
}

// ── Link autocomplete (child cells) ──
async function onChildLinkComplete(col, e) {
	const target = col.linkTarget
	if (!target) {
		childLinkSuggestions.value = []
		return
	}
	try {
		const rows = await searchLink(target, e.query || "")
		childLinkSuggestions.value = rows.map((r) => r.name)
	} catch (_) {
		childLinkSuggestions.value = []
	}
}

// ════════════════ SAVE / SUBMIT / CANCEL / DELETE / AMEND ════════════════

// Build the payload sent to the server.
//
// FLAT PATH (every non-stock-pivot doctype — unchanged): drop the hidden
// grouped-JSON fields so the flat child rows persist (before_validate skips
// ungroup when the grouped field is empty).
//
// STOCK-PIVOT PATH (R3a, stock vouchers only): emit each section's grouped JSON
// into its grouped field AND send an EMPTY flat child array, so the voucher's
// before_validate runs ungroup_items_from_ui → resolves/creates variants and
// rebuilds the flat child table server-side. This is the OPPOSITE of the flat
// path. Only the fields in stockPivots are affected; all others stay flat.
function buildPayload() {
	const payload = {}
	for (const [k, v] of Object.entries(form)) {
		if (GROUPED_JSON_FIELDS.has(k)) continue
		payload[k] = v
	}
	// Ensure the grouped-JSON twins are NOT sent by default (extra safety).
	for (const g of GROUPED_JSON_FIELDS) delete payload[g]

	// Stock-pivot doctypes only: write grouped JSON + blank the flat child.
	for (const pv of stockPivots.value) {
		const grid = gridRefs[pv.childField]
		const grouped = grid?.getItems ? grid.getItems() : []
		const isEmpty = grouped.length === 0
		// EDIT mode safety: if the grid is empty (e.g. the grouped onload hydration
		// failed), do NOT send empty grouped + empty flat — that would wipe the
		// doc's existing rows. Leave both fields out so the server keeps them.
		// CREATE mode: always send (an empty doc legitimately has no items).
		if (mode.value === "edit" && isEmpty) continue
		payload[pv.groupedField] = JSON.stringify(grouped)
		// Empty flat child → before_validate clears + rebuilds it from grouped.
		payload[pv.childField] = []
	}
	return payload
}

function firstMissingRequired() {
	// 1) Parent fields (only those currently visible — a depends_on-hidden field
	// is not required).
	for (const f of visibleFormFields.value) {
		if (isMissing(f)) return f.label
	}
	// 2) Editable child-table rows: any required cell left empty blocks the save
	// here (inline) instead of letting the server reject the round-trip. The
	// returned label names the child table + field + row so the toast is actionable.
	for (const ct of editableChildTables.value) {
		const reqdCols = ct.columns.filter((c) => c.reqd)
		if (!reqdCols.length) continue
		const rows = Array.isArray(form[ct.fieldname]) ? form[ct.fieldname] : []
		for (let i = 0; i < rows.length; i++) {
			for (const col of reqdCols) {
				const v = rows[i][col.fieldname]
				if (v === null || v === undefined || v === "") {
					return `${ct.label} → ${col.label} (row ${i + 1})`
				}
			}
		}
	}
	return null
}

async function onSave() {
	const missing = firstMissingRequired()
	if (missing) {
		toast.warn("Missing required field", `“${missing}” is required.`)
		return
	}
	const payload = buildPayload()
	try {
		if (mode.value === "create") {
			const result = await docState.save(payload)
			const newName = result?.name
			toast.success("Created", newName ? `${doctype.value} ${newName} created` : "Document created")
			if (newName) {
				router.push(`/${props.docRoute}/${encodeURIComponent(newName)}`)
			} else {
				mode.value = "view"
			}
		} else {
			await docState.save(payload, props.id)
			toast.success("Saved", `${props.id} updated`)
			mode.value = "view"
			await docState.load(props.id)
			docState.loadLinked(props.id)
			docState.loadActivity(props.id)
		}
	} catch (e) {
		toast.error("Save failed", e.message)
	}
}

function onDiscard() {
	if (mode.value === "create") {
		router.push(`/${props.docRoute}`)
		return
	}
	// edit → drop the form copy, back to view.
	clearForm()
	mode.value = "view"
}

function onSubmit() {
	confirm.require({
		header: "Submit document",
		message: `Submit ${props.id}? This runs the server validations and posts stock movements.`,
		acceptLabel: "Submit",
		acceptClass: "p-button-primary",
		accept: async () => {
			acting.value = "submit"
			try {
				await docState.submit(props.id)
				toast.success("Submitted", `${props.id} submitted`)
				await reloadView()
			} catch (e) {
				toast.error("Submit failed", e.message)
			} finally {
				acting.value = null
			}
		},
	})
}

function onCancel() {
	confirm.require({
		header: "Cancel document",
		message: `Cancel ${props.id}? This reverses its stock movements.`,
		acceptLabel: "Cancel Document",
		acceptClass: "p-button-danger",
		rejectLabel: "Keep",
		accept: async () => {
			acting.value = "cancel"
			try {
				await docState.cancel(props.id)
				toast.success("Cancelled", `${props.id} cancelled`)
				await reloadView()
			} catch (e) {
				toast.error("Cancel failed", e.message)
			} finally {
				acting.value = null
			}
		},
	})
}

function onDelete() {
	confirm.require({
		header: "Delete document",
		message: `Permanently delete ${props.id}? This cannot be undone.`,
		acceptLabel: "Delete",
		acceptClass: "p-button-danger",
		accept: async () => {
			acting.value = "delete"
			try {
				await docState.remove(props.id)
				toast.success("Deleted", `${props.id} deleted`)
				router.push(`/${props.docRoute}`)
			} catch (e) {
				toast.error("Delete failed", e.message)
				acting.value = null
			}
		},
	})
}

// deferred: amend flow left as-is by decision — useDoc.amend already routes
// through the standard Frappe amend (copy → new draft); a rewrite is out of scope.
function onAmend() {
	confirm.require({
		header: "Amend document",
		message: `Create a new draft amending ${props.id}?`,
		acceptLabel: "Amend",
		acceptClass: "p-button-primary",
		accept: async () => {
			acting.value = "amend"
			try {
				const result = await docState.amend(props.id)
				const newName = result?.name
				toast.success("Amended", newName ? `Draft ${newName} created` : "Amendment created")
				if (newName) router.push(`/${props.docRoute}/${encodeURIComponent(newName)}`)
			} catch (e) {
				toast.error("Amend failed", e.message)
			} finally {
				acting.value = null
			}
		},
	})
}

async function reloadView() {
	await docState.load(props.id)
	docState.loadLinked(props.id)
	docState.loadActivity(props.id)
	if (isWorkOrder.value && approvalRef.value) approvalRef.value.reload?.()
	if (isWorkflow.value && workflowRef.value) workflowRef.value.reload?.()
}

// ── Details field list (config → meta → doc keys) — VIEW mode ──
// Hide rule (applies in BOTH the Details view AND the edit/create form): a
// READ-ONLY field with no value is dropped — it's derived/auto-filled, so an empty
// one is just clutter, and it reappears the moment it gets a value (reactive).
// Empty = null/undefined/"" for any field; numeric (Int/Float/Currency/Percent)
// also counts 0 as empty. A Check always has a value (0/1) so it is never hidden.
function isEmptyForHide(v, fieldtype) {
	if (fieldtype === "Check") return false
	if (["Int", "Float", "Currency", "Percent"].includes(fieldtype))
		return v === null || v === undefined || v === "" || Number(v) === 0
	return v === null || v === undefined || v === ""
}

const detailFields = computed(() => {
	if (!doc.value) return []
	const out = []

	// 1) explicit per-doctype config
	const cfg = getFieldConfig(doctype.value)
	if (cfg) {
		for (const f of cfg) {
			if (!(f.fieldname in doc.value)) continue
			const cmf = metaFieldMap.value[f.fieldname]
			if (cmf?.read_only && isEmptyForHide(doc.value[f.fieldname], cmf?.fieldtype)) continue
			out.push({
				fieldname: f.fieldname,
				label: f.label || humanize(f.fieldname),
				type: f.type || null,
				isLink: f.type === "Link" || linkTypeFor(f.fieldname),
			})
		}
		return out
	}

	// 2) meta-driven (preferred fallback)
	if (meta.value?.fields?.length) {
		for (const mf of meta.value.fields) {
			if (META_HIDDEN_FIELDTYPES.has(mf.fieldtype)) continue
			if (SYSTEM_FIELDS.has(mf.fieldname)) continue
			if (mf.hidden) continue
			if (!(mf.fieldname in doc.value)) continue
			// Hide read-only empty/zero fields (any type; numeric 0 counts as empty).
			if (mf.read_only && isEmptyForHide(doc.value[mf.fieldname], mf.fieldtype)) continue
			out.push({
				fieldname: mf.fieldname,
				label: mf.label || humanize(mf.fieldname),
				type: mfTypeToDisplay(mf.fieldtype),
				isLink: mf.fieldtype === "Link",
			})
		}
		return out
	}

	// 3) bare fallback — the doc's own scalar keys
	for (const [k, v] of Object.entries(doc.value)) {
		if (SYSTEM_FIELDS.has(k)) continue
		if (Array.isArray(v) || (v && typeof v === "object")) continue
		out.push({ fieldname: k, label: humanize(k), type: null, isLink: false })
	}
	return out
})

// ── Child tables (from meta Table fields) — VIEW mode ──
const childTables = computed(() => {
	if (!doc.value) return []
	const tables = []
	const metaTables = (meta.value?.fields || []).filter(
		(f) => f.fieldtype === "Table" && !f.hidden && !CHILD_TABLE_EXCLUDE.has(f.fieldname),
	)
	if (metaTables.length) {
		for (const tf of metaTables) {
			const rows = doc.value[tf.fieldname]
			if (!Array.isArray(rows)) continue
			tables.push({
				fieldname: tf.fieldname,
				label: tf.label || humanize(tf.fieldname),
				columns: childColumns(rows),
			})
		}
		// U2: surface the primary content tables (Deliverables/Receivables/Items)
		// FIRST, ahead of low-traffic logs.
		const pivotFields = pivotChildFields.value
		if (pivotFields.size) {
			tables.sort((a, b) => (pivotFields.has(a.fieldname) ? 0 : 1) - (pivotFields.has(b.fieldname) ? 0 : 1))
		}
		return tables
	}
	for (const [k, v] of Object.entries(doc.value)) {
		if (!Array.isArray(v) || !v.length || typeof v[0] !== "object") continue
		tables.push({ fieldname: k, label: humanize(k), columns: childColumns(v) })
	}
	return tables
})

const CHILD_HIDDEN = new Set([
	"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx",
	"parent", "parentfield", "parenttype", "doctype", "__islocal", "__unsaved",
])

function childColumns(rows) {
	if (!rows.length) return []
	const keys = []
	for (const k of Object.keys(rows[0])) {
		if (CHILD_HIDDEN.has(k)) continue
		const v = rows[0][k]
		if (v && typeof v === "object") continue
		keys.push(k)
	}
	return keys.slice(0, 8).map((k) => ({
		fieldname: k,
		label: humanize(k),
		type: null,
		isLink: false,
	}))
}

function rowsFor(ct) {
	const rows = doc.value?.[ct.fieldname]
	return Array.isArray(rows) ? rows : []
}

// U3: badge the count the user actually SEES. For size-pivot child tables the
// grid shows grouped rows (item → attributes), not the flat child rows — so
// badge the grouped entry count; otherwise the flat row count.
function tabBadge(ct) {
	if (pivotChildFields.value.has(ct.fieldname)) {
		const groups = viewGrouped.value?.[ct.fieldname]
		if (Array.isArray(groups)) return groups.reduce((n, g) => n + (g.items?.length || 0), 0)
	}
	return rowsFor(ct).length
}

// ── Approval log (Work Order) ──
const approvalLog = computed(() => {
	const rows = doc.value?.mgk_approval_log
	if (!Array.isArray(rows)) return []
	return [...rows].sort((a, b) =>
		String(b.action_at || "").localeCompare(String(a.action_at || "")),
	)
})

// ── Linked documents ──
const linkedGroups = computed(() => {
	const raw = docState.linked.value || {}
	const groups = []
	for (const [dt, rows] of Object.entries(raw)) {
		if (!Array.isArray(rows) || !rows.length) continue
		groups.push({ doctype: dt, rows })
	}
	groups.sort((a, b) => a.doctype.localeCompare(b.doctype))
	return groups
})
const linkedTotal = computed(() =>
	linkedGroups.value.reduce((n, g) => n + g.rows.length, 0),
)

function linkedRowMeta(row) {
	const bits = []
	for (const k of ["title", "supplier", "supplier_name", "item", "status", "grand_total"]) {
		if (row[k] != null && row[k] !== "" && k !== "name") bits.push(String(row[k]))
	}
	return bits.slice(0, 2).join(" · ")
}

// ── Activity (comments + versions) ──
const activityEvents = computed(() => {
	const events = []
	const d = doc.value
	const info = docState.docInfo.value

	if (d?.creation) {
		events.push({
			when: d.creation,
			who: shortUser(d.owner),
			text: "Created",
			tone: "good",
			icon: "pi pi-plus",
		})
	}

	const comments = info?.comments
	if (Array.isArray(comments) && comments.length) {
		for (const c of comments) {
			events.push({
				when: c.creation,
				who: shortUser(c.owner),
				text: stripHtml(c.content || ""),
				tone: "muted",
				icon: "pi pi-comment",
			})
		}
	} else if (d?._comments) {
		try {
			const parsed = JSON.parse(d._comments)
			for (const c of parsed) {
				events.push({
					when: c.creation || d.modified,
					who: shortUser(c.by),
					text: stripHtml(c.comment || ""),
					tone: "muted",
					icon: "pi pi-comment",
				})
			}
		} catch (_) { /* ignore */ }
	}

	const versions = info?.versions
	if (Array.isArray(versions)) {
		for (const v of versions) {
			events.push({
				when: v.creation,
				who: shortUser(v.owner),
				text: "Edited",
				tone: "info",
				icon: "pi pi-pencil",
			})
		}
	}

	if (d?.docstatus === 1) {
		events.push({
			when: d.modified,
			who: shortUser(d.modified_by),
			text: "Submitted",
			tone: "good",
			icon: "pi pi-check-circle",
		})
	} else if (d?.docstatus === 2) {
		events.push({
			when: d.modified,
			who: shortUser(d.modified_by),
			text: "Cancelled",
			tone: "danger",
			icon: "pi pi-ban",
		})
	}

	return events.sort((a, b) =>
		String(b.when || "").localeCompare(String(a.when || "")),
	)
})

// ── Header derivations ──
const titleLine = computed(() => {
	const d = doc.value
	if (!d) return ""
	const bits = []
	for (const f of ["item", "supplier_name", "supplier", "process_name", "total_quantity"]) {
		if (d[f] != null && d[f] !== "") bits.push(String(d[f]))
	}
	if (bits.length) return bits.slice(0, 4).join(" · ")
	const tf = meta.value?.title_field
	if (tf && d[tf]) return String(d[tf])
	return ""
})

const DOCSTATUS_LABELS = { 0: "Draft", 1: "Submitted", 2: "Cancelled" }
const statusLabel = computed(() => {
	const d = doc.value
	if (!d) return ""
	if (isWorkflow.value && d.workflow_state) return d.workflow_state
	return d.status || DOCSTATUS_LABELS[d.docstatus] || "—"
})
const statusSeverity = computed(() => {
	const d = doc.value
	if (isWorkflow.value && d?.workflow_state) return WORKFLOW_SEVERITY[d.workflow_state] || "warn"
	const ds = d?.docstatus
	if (ds === 1) return "success"
	if (ds === 2) return "danger"
	return "warn"
})

// ── Quick Info (key meta pairs) ──
const quickInfo = computed(() => {
	const d = doc.value
	if (!d) return []
	const out = []
	const push = (label, val) => {
		if (val != null && val !== "") out.push({ label, value: String(val) })
	}
	const pref = isWorkOrder.value
		? [["process_name", "Process"], ["supplier", "Job-worker"], ["total_quantity", "Qty"], ["wo_date", "WO Date"]]
		: detailFields.value.slice(0, 5).map((f) => [f.fieldname, f.label])
	for (const [fn, label] of pref) {
		const f = detailFields.value.find((x) => x.fieldname === fn)
		push(label, f ? displayValue(d[fn], f.type) : d[fn])
	}
	push("Created by", shortUser(d.owner))
	push("Last updated", formatDateTime(d.modified))
	return out
})

// ── Navigation ──
const deskUrl = computed(() => {
	const slug = doctype.value.toLowerCase().replace(/ /g, "-")
	return `/app/${encodeURIComponent(slug)}/${encodeURIComponent(props.id)}`
})

function goHome() {
	router.push("/home")
}
function goList() {
	router.push(`/${props.docRoute}`)
}
function navigateDoc(dt, name) {
	const reg = getRegistryByDoctype(dt)
	if (reg) router.push(`/${reg.route}/${encodeURIComponent(name)}`)
	else {
		const slug = dt.toLowerCase().replace(/ /g, "-")
		window.open(`/app/${encodeURIComponent(slug)}/${encodeURIComponent(name)}`, "_blank")
	}
}
function navigateLink(field, value) {
	if (!value) return
	const mf = metaFieldMap.value[field.fieldname]
	const targetDt = mf?.options
	if (targetDt) navigateDoc(targetDt, value)
}
function goToFirst(group) {
	if (group.rows[0]) navigateDoc(group.doctype, group.rows[0].name)
}

// ── Approval gate hooks ──
function onApprovalState(s) {
	approvalState.value = s
}
async function onApprovalChanged() {
	await docState.load(props.id)
	docState.loadActivity(props.id)
}

// ── date helpers (form ↔ Frappe string) ──
// Parse date / datetime strings as LOCAL time (constructing from parts) so a
// pure "YYYY-MM-DD" doesn't shift a day in negative-offset timezones (the
// classic `new Date("2026-05-25")`-is-UTC pitfall).
function toDateObj(val) {
	if (!val) return null
	const s = String(val).trim()
	const [datePart, timePart] = s.split(/[ T]/)
	const [y, m, d] = (datePart || "").split("-").map(Number)
	if (!y || !m || !d) return null
	let hh = 0, mm = 0, ss = 0
	if (timePart) {
		const [h, mi, se] = timePart.split(":").map(Number)
		hh = h || 0
		mm = mi || 0
		ss = se || 0
	}
	const obj = new Date(y, m - 1, d, hh, mm, ss)
	return Number.isNaN(obj.getTime()) ? null : obj
}
function fromDateObj(d, withTime) {
	if (!d) return ""
	const pad = (n) => String(n).padStart(2, "0")
	const date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
	if (!withTime) return date
	return `${date} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// Time field (HH:MM:SS string) ↔ Date object for the timeOnly DatePicker.
function toTimeObj(val) {
	if (!val) return null
	const [h, mi, s] = String(val).split(":").map(Number)
	const d = new Date()
	d.setHours(h || 0, mi || 0, s || 0, 0)
	return d
}
function fromTimeObj(d) {
	if (!d) return ""
	const pad = (n) => String(n).padStart(2, "0")
	return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
function nowTimeStr() {
	return fromTimeObj(new Date())
}

// ── formatting helpers ──
function humanize(s) {
	return String(s)
		.replace(/_/g, " ")
		.replace(/\b\w/g, (c) => c.toUpperCase())
}
function mfTypeToDisplay(ft) {
	if (ft === "Date") return "Date"
	if (ft === "Datetime") return "Datetime"
	if (ft === "Currency") return "Currency"
	if (ft === "Float" || ft === "Percent") return "Float"
	if (ft === "Int") return "Int"
	if (ft === "Check") return "Check"
	if (ft === "Link") return "Link"
	return null
}
function displayValue(val, type) {
	if (val === null || val === undefined || val === "") return "—"
	if (type === "Check") return val ? "Yes" : "No"
	if (type === "Date") return formatDate(val)
	if (type === "Datetime") return formatDateTime(val)
	if (type === "Currency") return formatNumber(val)
	if (type === "Float" || type === "Int") return formatNumber(val)
	return String(val)
}
function formatDate(val) {
	if (!val) return "—"
	const datePart = String(val).split(" ")[0]
	const [y, m, d] = datePart.split("-")
	return y && m && d ? `${d}-${m}-${y}` : val
}
function formatDateTime(val) {
	if (!val) return "—"
	const [datePart, timePart] = String(val).split(" ")
	const [y, m, d] = (datePart || "").split("-")
	const dateStr = y && m && d ? `${d}-${m}-${y}` : datePart
	const timeStr = timePart ? timePart.slice(0, 5) : ""
	return timeStr ? `${dateStr} ${timeStr}` : dateStr
}
function formatNumber(val) {
	const n = Number(val)
	return Number.isNaN(n) ? String(val) : n.toLocaleString("en-IN")
}
function shortUser(u) {
	if (!u) return "—"
	return String(u).split("@")[0]
}
function stripHtml(s) {
	return String(s).replace(/<[^>]*>/g, "").trim()
}
</script>

<style scoped>
.doc-detail {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

/* Breadcrumb */
.crumbs {
	display: flex;
	align-items: center;
	gap: 7px;
	font-size: 12.5px;
	color: var(--mgk-muted);
}
.crumbs a {
	cursor: pointer;
	color: var(--mgk-muted);
}
.crumbs a:hover {
	color: var(--mgk-accent-700);
}
.crumbs .sep {
	color: var(--mgk-muted-2);
}
.crumbs .crumb-cur {
	font-size: 12.5px;
}

/* Header */
.detail-head {
	display: flex;
	align-items: flex-start;
	gap: 14px;
}
.id-block {
	display: flex;
	flex-direction: column;
	gap: 3px;
}
.doc-id {
	font-size: 18px;
	letter-spacing: -0.01em;
}
.doc-title {
	font-size: 13px;
	color: var(--mgk-muted);
}
.doc-title.edit-hint {
	color: var(--mgk-accent-700);
	font-weight: 600;
}
.head-status {
	align-self: center;
}
.head-actions {
	margin-left: auto;
	display: flex;
	gap: 8px;
	align-items: center;
}
.desk-link {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	font-size: 12.5px;
	color: var(--mgk-accent-700);
	padding: 6px 10px;
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius-sm);
}
.desk-link:hover {
	background: var(--mgk-accent-50);
}

/* States */
.state-block {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 10px;
	padding: 40px 0;
	color: var(--mgk-muted);
}
.state-block.sm {
	flex-direction: row;
	padding: 22px 0;
	font-size: 13px;
}

/* Two-column layout */
.detail-layout {
	display: grid;
	grid-template-columns: minmax(0, 1fr) 288px;
	gap: 16px;
	align-items: start;
}
@media (max-width: 980px) {
	.detail-layout {
		grid-template-columns: 1fr;
	}
}

.detail-main {
	background: var(--mgk-card);
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius);
	overflow: hidden;
}

/* ── Form (edit / create) ── */
.form-layout {
	display: block;
}
.form-card {
	padding: 18px 20px;
	display: flex;
	flex-direction: column;
	gap: 20px;
}
.form-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16px 28px;
}
@media (max-width: 700px) {
	.form-grid {
		grid-template-columns: 1fr;
	}
}
.form-field {
	display: flex;
	flex-direction: column;
	gap: 5px;
	min-width: 0;
}
.form-field.wide {
	grid-column: 1 / -1;
}
.form-field .fld {
	width: 100%;
}
.form-field .req {
	color: #be123c;
	margin-left: 2px;
}
.fld-check {
	display: flex;
	align-items: center;
	gap: 10px;
	padding-top: 2px;
}
.check-label {
	font-size: 13px;
	color: var(--mgk-ink-2);
}

/* Child-table editor */
.child-editor {
	display: flex;
	flex-direction: column;
	gap: 8px;
}
.child-editor-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
}
.child-editor-head h4 {
	margin: 0;
	font-size: 13.5px;
	font-weight: 600;
	color: var(--mgk-ink);
}
.child-cols-note {
	font-size: 12px;
	color: var(--mgk-muted);
	font-style: italic;
}
.child-cols-note.pivot-note {
	color: var(--mgk-accent-700);
	font-style: normal;
	font-size: 11.5px;
}
.edit-dt :deep(.cell-input) {
	width: 100%;
}
.edit-dt :deep(.p-datatable-tbody > tr > td) {
	padding: 6px 10px;
}

/* Tab badge */
.tab-badge {
	margin-left: 6px;
	background: var(--mgk-accent-50);
	color: var(--mgk-accent-700);
	font-size: 11px;
	font-weight: 600;
	padding: 1px 7px;
	border-radius: 999px;
}

/* Field grid (view) */
.field-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 14px 28px;
}
@media (max-width: 700px) {
	.field-grid {
		grid-template-columns: 1fr;
	}
}
.field {
	display: flex;
	flex-direction: column;
	gap: 4px;
	min-width: 0;
}
.field-label {
	font-size: 11.5px;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--mgk-muted);
	font-weight: 600;
}
.field-value {
	font-size: 13.5px;
	color: var(--mgk-ink);
	word-break: break-word;
}
.field-value.link {
	color: var(--mgk-accent-700);
	cursor: pointer;
}
.field-value.link:hover {
	text-decoration: underline;
}
.field-value.mgkmono {
	font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
	font-size: 13px;
}

.empty-inline {
	color: var(--mgk-muted);
	font-size: 13px;
	padding: 18px 2px;
}
.empty-inline.sm {
	padding: 6px 0;
	font-size: 12.5px;
}

/* Child table */
.child-dt {
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius-sm);
	overflow: hidden;
}
.table-empty {
	text-align: center;
	padding: 22px 0;
	color: var(--mgk-muted);
	font-size: 13px;
}

/* Timeline */
.mgk-timeline {
	padding: 6px 0;
}
.tl-dot {
	display: grid;
	place-items: center;
	width: 24px;
	height: 24px;
	border-radius: 50%;
	background: var(--mgk-card);
	border: 2px solid var(--mgk-line);
	color: var(--mgk-muted);
	font-size: 11px;
}
.tl-dot.good {
	border-color: #16a34a;
	color: #16a34a;
}
.tl-dot.danger {
	border-color: #be123c;
	color: #be123c;
}
.tl-dot.info {
	border-color: var(--mgk-accent);
	color: var(--mgk-accent);
}
.tl-when {
	font-size: 11.5px;
	color: var(--mgk-muted);
	margin-bottom: 2px;
}
.tl-msg {
	font-size: 13px;
	color: var(--mgk-ink);
	padding-bottom: 12px;
}
.txt-danger {
	color: #be123c;
}
.txt-good {
	color: #16a34a;
}
.tab-footnote {
	margin: 14px 2px 0;
	font-size: 12px;
	color: var(--mgk-muted);
}
.tab-footnote code,
.tl-msg code {
	font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
	font-size: 11.5px;
	background: var(--mgk-slate-50);
	padding: 1px 4px;
	border-radius: 3px;
}

/* Linked panel */
.linked-panel {
	display: flex;
	flex-direction: column;
	gap: 10px;
}
.linked-group {
	border: 1px solid var(--mgk-line);
	border-radius: var(--radius-sm);
	overflow: hidden;
}
.linked-group-head {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 9px 14px;
	background: var(--mgk-slate-50);
	border-bottom: 1px solid var(--mgk-line);
}
.linked-group-head h5 {
	margin: 0;
	font-size: 12.5px;
	font-weight: 600;
	color: var(--mgk-ink);
}
.linked-group-head .count {
	background: var(--mgk-accent-50);
	color: var(--mgk-accent-700);
	font-size: 11px;
	font-weight: 600;
	padding: 1px 7px;
	border-radius: 999px;
}
.linked-row {
	display: grid;
	grid-template-columns: 200px 1fr auto;
	gap: 12px;
	align-items: center;
	padding: 11px 14px;
	border-bottom: 1px solid var(--mgk-line);
	cursor: pointer;
	transition: background 0.1s;
}
.linked-row:last-child {
	border-bottom: 0;
}
.linked-row:hover {
	background: var(--mgk-slate-50);
}
.linked-row .lr-id {
	font-size: 12.5px;
}
.linked-row .lr-meta {
	font-size: 12.5px;
	color: var(--mgk-ink-2);
}
.linked-row .lr-arrow {
	color: var(--mgk-muted-2);
	transition: transform 0.12s, color 0.12s;
}
.linked-row:hover .lr-arrow {
	color: var(--mgk-accent);
	transform: translateX(2px);
}

/* Side panel */
.detail-side {
	display: flex;
	flex-direction: column;
	gap: 12px;
}
.side-card {
	border: 1px solid var(--mgk-line);
	box-shadow: none;
}
:deep(.side-card .p-card-body) {
	padding: 14px 16px;
}
:deep(.side-card .p-card-content) {
	padding: 0;
}
.side-title {
	font-size: 11.5px;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: var(--mgk-muted);
	font-weight: 600;
}
.meta-row {
	display: flex;
	justify-content: space-between;
	gap: 10px;
	font-size: 12.5px;
	padding: 6px 0;
	border-bottom: 1px solid var(--mgk-line);
}
.meta-row:last-child {
	border-bottom: 0;
}
.meta-row.col {
	flex-direction: column;
	gap: 3px;
}
.meta-row .k {
	color: var(--mgk-muted);
	flex-shrink: 0;
}
.meta-row .v {
	color: var(--mgk-ink);
	font-weight: 500;
	text-align: right;
	max-width: 65%;
	word-break: break-word;
}
.meta-row.col .v {
	max-width: 100%;
	text-align: left;
}
.meta-row .v.reason {
	font-weight: 400;
	font-style: italic;
	color: var(--mgk-ink-2);
}
.link-row {
	cursor: pointer;
}
.link-row:hover .k {
	color: var(--mgk-accent-700);
}
.count-pill {
	background: var(--mgk-accent-50);
	color: var(--mgk-accent-700);
	font-size: 11px;
	font-weight: 600;
	padding: 1px 8px;
	border-radius: 999px;
}
</style>
