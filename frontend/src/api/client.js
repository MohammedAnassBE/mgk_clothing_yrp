/**
 * Generic fetch wrapper for Frappe REST API.
 * Handles CSRF tokens, error responses, and provides typed helpers
 * for all standard Frappe resource and method endpoints.
 */

function getCsrfToken() {
  return window.csrf_token || window.frappe?.csrf_token || ''
}

function buildQueryString(params) {
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue
    if (typeof value === 'object') {
      qs.append(key, JSON.stringify(value))
    } else {
      qs.append(key, String(value))
    }
  }
  const str = qs.toString()
  return str ? `?${str}` : ''
}

async function request(url, options = {}) {
  const headers = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    'X-Frappe-CSRF-Token': getCsrfToken(),
    ...options.headers,
  }

  const config = {
    credentials: 'include',
    ...options,
    headers,
  }

  const response = await fetch(url, config)

  if (response.status === 401) {
    window.location.href = '/login'
    throw new Error('Session expired. Redirecting to login.')
  }

  if (response.status === 403) {
    const body = await response.json().catch(() => ({}))
    let msg = 'Permission denied'
    if (body._server_messages) {
      try {
        msg = JSON.parse(body._server_messages).map((m) => {
          try { return JSON.parse(m).message || m } catch { return m }
        }).join('\n')
      } catch { /* keep default */ }
    } else if (body.message) {
      msg = body.message
    }
    // Strip HTML tags for clean display
    msg = msg.replace(/<[^>]*>/g, '')
    throw new Error(msg)
  }

  if (response.status === 404 || response.status === 409 || response.status === 417) {
    // Frappe maps validate-throw failures to various 4xx codes (404 for
    // `DoesNotExistError`, 417 for `ValidationError`, 409 for stale-doc).
    // Frontend used to show generic "Not found" / "Conflict" toasts; instead
    // surface the real `_server_messages` payload so the user sees the
    // actual validation message (e.g. "Please set Stage values before
    // setting it as Dependent Attribute").
    const body = await response.json().catch(() => ({}))
    let msg = body.message || (
      response.status === 404
        ? 'Not found'
        : response.status === 409
          ? 'Conflict: document has been modified'
          : `Request failed with status ${response.status}`
    )
    if (body._server_messages) {
      try {
        const parts = JSON.parse(body._server_messages).map((m) => {
          try { return JSON.parse(m).message || m } catch { return m }
        })
        if (parts.length) msg = parts.join('\n')
      } catch { /* keep default */ }
    }
    // Strip HTML tags for clean display.
    msg = String(msg).replace(/<[^>]*>/g, '').trim()
    throw new Error(msg)
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const serverMessages = body._server_messages
      ? JSON.parse(body._server_messages).map((m) => {
          try { return JSON.parse(m).message || m } catch { return m }
        }).join('\n')
      : null
    throw new Error(serverMessages || body.message || `Request failed with status ${response.status}`)
  }

  // 204 No Content
  if (response.status === 204) return null

  const json = await response.json()

  // Frappe wraps errors in exc/exception keys
  if (json.exc) {
    const parsed = JSON.parse(json.exc)
    const errorMsg = Array.isArray(parsed) ? parsed.filter(Boolean).join('\n') : String(parsed)
    throw new Error(errorMsg || 'Server error')
  }

  return json
}

/**
 * Split a thrown error's message into individual readable lines for a persistent
 * inline banner (Q15). `request()` already parses `_server_messages` / `exc`,
 * strips HTML, and joins the parts with "\n", so the banner just needs the
 * per-line breakdown. Empty/whitespace lines are dropped and duplicates removed.
 * @returns {string[]}
 */
export function errorLines(err) {
  const msg = typeof err === "string" ? err : err?.message || ""
  const seen = new Set()
  const out = []
  for (const raw of String(msg).split("\n")) {
    const line = raw.trim()
    if (!line || seen.has(line)) continue
    seen.add(line)
    out.push(line)
  }
  return out
}

// ---------------------------------------------------------------------------
// Frappe Resource API helpers
// ---------------------------------------------------------------------------

/**
 * Fetch a list of documents.
 * @returns {{ data: object[], total_count: number }}
 */
export async function getList(doctype, { fields, filters, or_filters, order_by, limit_start, limit_page_length } = {}) {
  const params = {}
  if (fields) params.fields = fields
  if (filters) params.filters = filters
  if (or_filters) params.or_filters = or_filters
  if (order_by) params.order_by = order_by
  if (limit_start !== undefined) params.limit_start = limit_start
  if (limit_page_length !== undefined) params.limit_page_length = limit_page_length

  const qs = buildQueryString(params)
  const json = await request(`/api/resource/${encodeURIComponent(doctype)}${qs}`, { method: 'GET' })
  return { data: json.data || [], total_count: json.total_count }
}

/**
 * List via `frappe.desk.reportview.get` — the same endpoint the Frappe Desk list
 * uses. Unlike the REST /api/resource path (and frappe.client.get_list, both of
 * which silently ignore `distinct`), reportview.get actually applies it. That is
 * required for CHILD-TABLE filters: the server LEFT JOINs the child table and
 * emits one row per matching child, so without distinct a parent appears N times.
 * reportview.get paginates the DISTINCT set, so paging stays correct.
 *
 * @returns {{ data: object[], total_count: undefined }} (count comes from getCount)
 */
export async function getListView(doctype, { fields, filters, or_filters, order_by, limit_start, limit_page_length } = {}) {
  const args = { doctype, distinct: 1 }
  if (fields) args.fields = fields
  if (filters) args.filters = filters
  if (or_filters) args.or_filters = or_filters
  if (order_by) args.order_by = order_by
  if (limit_start !== undefined) args.limit_start = limit_start
  if (limit_page_length !== undefined) args.limit_page_length = limit_page_length
  const msg = await callMethod('frappe.desk.reportview.get', args)
  // reportview returns a compressed columnar payload: { keys, values: [[...]] }.
  const keys = msg?.keys || []
  const values = msg?.values || msg?.data || []
  const data = values.map((row) => {
    const o = {}
    keys.forEach((k, i) => { o[k] = row[i] })
    return o
  })
  return { data, total_count: undefined }
}

/**
 * Fetch a single document by name.
 *
 * Uses `frappe.client.get` so the response carries `_comments` (and other
 * `_*` sidecar fields) used by the detail page's Activity timeline. The
 * REST `/api/resource/<dt>/<name>` endpoint strips those.
 */
export async function getDoc(doctype, name) {
  const result = await callMethod('frappe.client.get', { doctype, name })
  return result
}

/**
 * Create a new document.
 */
export async function createDoc(doctype, data) {
  const json = await request(`/api/resource/${encodeURIComponent(doctype)}`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
  return json.data
}

/**
 * Update an existing document.
 */
export async function updateDoc(doctype, name, data) {
  const json = await request(
    `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`,
    { method: 'PUT', body: JSON.stringify(data) },
  )
  return json.data
}

/**
 * Delete a document.
 */
export async function deleteDoc(doctype, name) {
  await request(
    `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`,
    { method: 'DELETE' },
  )
  return { ok: true }
}

// ---------------------------------------------------------------------------
// Whitelisted method calls
// ---------------------------------------------------------------------------

/**
 * Call a whitelisted @frappe.whitelist() method.
 * @param {string} method  Dotted path, e.g. "albion.albion.doctype.order.order.get_item_details"
 * @param {object} args    Keyword arguments passed as JSON body
 */
export async function callMethod(method, args = {}) {
  const json = await request(`/api/method/${method}`, {
    method: 'POST',
    body: JSON.stringify(args),
  })
  return json.message
}

export async function getBulkEditFields(doctype) {
  const result = await callMethod(
    'mgk_clothing_yrp.mgk_clothing_yrp.api.bulk_edit.get_bulk_edit_fields',
    { doctype },
  )
  return Array.isArray(result) ? result : []
}

export async function bulkUpdateField(doctype, docnames, field, value) {
  return callMethod(
    'mgk_clothing_yrp.mgk_clothing_yrp.api.bulk_edit.bulk_update_field',
    {
      doctype,
      docnames,
      fieldname: field.fieldname,
      value,
      child_doctype: field.child_doctype || null,
      parent_table_field: field.parent_table_field || null,
    },
  )
}

// ---------------------------------------------------------------------------
// Meta + linked-document helpers (read-only detail page)
// ---------------------------------------------------------------------------

/**
 * Fetch the DocType meta bundle (the doctype + every child-table doctype).
 * `frappe.desk.form.load.getdoctype` returns the meta in `frappe.response.docs`
 * (NOT `message`), so we read the raw JSON rather than going through callMethod.
 *
 * @returns {object[]} meta docs — index 0 is the parent DocType, the rest are
 *   the child-table DocTypes referenced by its Table fields.
 */
export async function getMeta(doctype) {
  const json = await request(
    `/api/method/frappe.desk.form.load.getdoctype?doctype=${encodeURIComponent(doctype)}`,
    { method: 'GET' },
  )
  return json.docs || []
}

/**
 * Fetch a document via the desk form-load endpoint so the server runs its
 * `onload` hook and the response carries `__onload`. This is how the Desk gets
 * the transient grouped `item_details` (size-pivot JSON) that `frappe.client.get`
 * does NOT include. Used by the stock-pivot edit path to round-trip grouped JSON.
 *
 * `frappe.desk.form.load.getdoc` returns the doc in `frappe.response.docs[0]`
 * (NOT `message`), so we read the raw JSON like getMeta does.
 *
 * @returns {object|null} the doc dict (with `__onload`), or null if not found.
 */
export async function getDocWithOnload(doctype, name) {
  const json = await request(
    `/api/method/frappe.desk.form.load.getdoc?doctype=${encodeURIComponent(doctype)}&name=${encodeURIComponent(name)}`,
    { method: 'GET' },
  )
  const docs = json.docs || []
  return docs[0] || null
}

/**
 * Discover documents that link to (doctype, name) across the whole site.
 * Wraps `frappe.desk.form.linked_with.get` which returns
 * `{ <LinkedDocType>: [ {name, ...}, ... ], ... }`.
 */
export async function getLinkedDocs(doctype, name) {
  const result = await callMethod('frappe.desk.form.linked_with.get', {
    doctype,
    docname: name,
  })
  return result || {}
}

/**
 * Full activity payload (comments, versions, communications, view logs…).
 * Wraps `frappe.desk.form.load.get_docinfo`.
 */
export async function getDocInfo(doctype, name) {
  const result = await callMethod('frappe.desk.form.load.get_docinfo', {
    doctype,
    name,
  })
  return result || {}
}

// ---------------------------------------------------------------------------
// Convenience helpers
// ---------------------------------------------------------------------------

/**
 * Get the count of documents matching filters.
 */
export async function getCount(doctype, filters = {}, or_filters = null, distinct = false) {
  // Route through reportview.get_count (NOT frappe.client.get_count): it honors
  // or_filters AND supports `distinct`, which is required for child-table filters —
  // their LEFT JOIN would otherwise count one row per matching child and inflate the
  // total. Omitting `limit` makes Frappe return an accurate (un-capped) count.
  const args = { doctype, filters }
  if (or_filters) args.or_filters = or_filters
  if (distinct) args.distinct = 1
  const result = await callMethod('frappe.desk.reportview.get_count', args)
  return result
}

/**
 * Search for link-field values (type-ahead / autocomplete).
 */
// Title-aware Link search. Delegates to the server `link_search`, which matches
// the typed text against `name` AND the doctype's title_field / search_fields
// (so e.g. an Item autonamed `Item-00012` is found by its descriptive `name1`
// = "Greige Yarn"). Returns [{ name, label }] — `name` is the value a Link
// stores, `label` is what to show the user. Back-compat: every existing caller
// reads `r.name`, which is still present.
export async function searchLink(doctype, txt, filters = {}) {
  const result = await callMethod(
    'mgk_clothing_yrp.mgk_clothing_yrp.api.link_search.link_search',
    { doctype, txt: txt || '', filters, page_length: 20 },
  )
  return result || []
}

/**
 * Autocomplete Addresses belonging to a party (Supplier/Customer/…).
 * The Address ↔ party relation is a Dynamic Link child table, so a plain
 * filter on `tabAddress` can't express it. Frappe's whitelisted
 * `address_query` is the same path the Desk uses — it joins Dynamic Link
 * rows and returns one row per matching Address as a tuple
 * `(name, address_line1, link_doctype, link_name)`. We project to
 * `{ name }` to keep the LinkField shape uniform with `searchLink`.
 */
export async function searchAddressForParty(partyDoctype, partyName, txt) {
  if (!partyDoctype || !partyName) return []
  const rows = await callMethod('frappe.contacts.doctype.address.address.address_query', {
    doctype: 'Address',
    txt: txt || '',
    searchfield: 'name',
    start: 0,
    page_len: 20,
    filters: { link_doctype: partyDoctype, link_name: partyName },
  })
  if (!Array.isArray(rows)) return []
  return rows.map((row) => ({ name: Array.isArray(row) ? row[0] : row.name }))
}

// ---------------------------------------------------------------------------
// Workflow helpers for submittable DocTypes
// ---------------------------------------------------------------------------

/**
 * Submit a document (set docstatus = 1).
 */
export async function submitDoc(doctype, name) {
  const json = await request(
    `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`,
    { method: 'PUT', body: JSON.stringify({ docstatus: 1 }) },
  )
  return json.data
}

/**
 * Cancel a submitted document (set docstatus = 2).
 */
export async function cancelDoc(doctype, name) {
  const json = await request(
    `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`,
    { method: 'PUT', body: JSON.stringify({ docstatus: 2 }) },
  )
  return json.data
}

/**
 * Amend a cancelled document (creates a new amended copy as draft).
 * Fetches the cancelled doc, strips system fields, sets amended_from, and creates a new doc.
 */
export async function amendDoc(doctype, name) {
  const orig = await getDoc(doctype, name)
  const systemFields = new Set([
    'name', 'creation', 'modified', 'modified_by', 'owner', 'docstatus',
    '_user_tags', '_comments', '_assign', '_liked_by',
  ])
  const childSystemFields = new Set([
    'name', 'creation', 'modified', 'modified_by', 'owner', 'docstatus',
    'parent', 'parentfield', 'parenttype',
  ])
  const newDoc = {}
  for (const [key, value] of Object.entries(orig)) {
    if (systemFields.has(key)) continue
    if (Array.isArray(value)) {
      newDoc[key] = value.map(row => {
        const clean = {}
        for (const [k, v] of Object.entries(row)) {
          if (!childSystemFields.has(k)) clean[k] = v
        }
        return clean
      })
    } else {
      newDoc[key] = value
    }
  }
  newDoc.amended_from = name
  return createDoc(doctype, newDoc)
}

// ---------------------------------------------------------------------------
// Workflow transition helpers (workflow-managed DocTypes — Process Cost, Item
// Price). Both core methods are @frappe.whitelist(): get_transitions is
// role-filtered server-side; apply_workflow enforces role + self-approval. The
// `doc` arg is passed as a JSON string (the methods parse_json it + load_from_db).
// ---------------------------------------------------------------------------

/**
 * Allowed workflow transitions for `doc`, given the current user + workflow_state.
 * @returns {object[]} transition rows ({ action, next_state, allowed, ... }); [] if none.
 */
export async function getWorkflowTransitions(doc) {
  const result = await callMethod('frappe.model.workflow.get_transitions', {
    doc: JSON.stringify(doc),
  })
  return Array.isArray(result) ? result : []
}

/**
 * Apply a workflow action (e.g. "Submit" / "Approve" / "Reject") to `doc`.
 * @returns the updated doc dict.
 */
export async function applyWorkflowAction(doc, action) {
  return await callMethod('frappe.model.workflow.apply_workflow', {
    doc: JSON.stringify(doc),
    action,
  })
}

/**
 * Add a timeline comment to a document (used to record a workflow reject reason).
 * Wraps the whitelisted `frappe.desk.form.utils.add_comment`.
 */
export async function addComment(doctype, name, content) {
  // Both comment_email and comment_by must be the acting user's id. The user just
  // performed an authenticated action, so session.user is reliably set.
  const user = window.frappe?.session?.user || window.frappe?.boot?.user?.name || 'Administrator'
  return await callMethod('frappe.desk.form.utils.add_comment', {
    reference_doctype: doctype,
    reference_name: name,
    content,
    comment_email: user,
    comment_by: user,
  })
}
