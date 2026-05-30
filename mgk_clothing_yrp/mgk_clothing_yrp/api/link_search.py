"""Title-aware Link search for the /web SPA.

The SPA's `searchLink` originally queried only the `name` (ID) column
(`frappe.client.get_list` with `name like %txt%`). That breaks for doctypes whose
human-readable label lives in a separate field — e.g. yrp's `Item` is autonamed
`Item-.#####` (so `name` = "Item-00012") while the descriptive name is in
`name1` ("Greige Yarn"). Typing "Greige" matched nothing.

`link_search` mirrors what the Frappe Desk link search does: match the typed text
against `name` AND the doctype's title / search fields, and return both the `name`
(the value a Link stores) and a `label` (what to show the user). It is
meta-driven — it auto-detects the title field from the doctype meta plus a few
yrp/Frappe conventions (`name1`, `item_name`, `<doctype>_name`, `title`) — so it
needs no per-doctype configuration and degrades to a plain name search when there
is no title field.
"""

import json

import frappe

# Common "human label" field names to probe when a doctype has no explicit
# title_field configured (checked against meta.has_field, so unknowns are safe).
_TITLE_GUESSES = ("name1", "item_name", "title", "full_name", "label")


def _title_fields(meta):
	"""Ordered, de-duplicated list of real fields to search/label by (besides name)."""
	cand = []
	if meta.title_field:
		cand.append(meta.title_field)
	if meta.search_fields:
		cand += [f.strip() for f in meta.search_fields.split(",") if f.strip()]
	cand.append(frappe.scrub(meta.name) + "_name")  # e.g. supplier_name, customer_name
	cand += list(_TITLE_GUESSES)
	seen, out = set(), []
	for f in cand:
		if f and f not in seen and f != "name" and meta.has_field(f):
			seen.add(f)
			out.append(f)
	return out


@frappe.whitelist()
def link_search(doctype, txt="", filters=None, page_length=20):
	"""Search `doctype` by name + title/search fields. Returns [{name, label}].

	`filters` (AND) narrow the result set (e.g. attribute_name for Item Attribute
	Value); the typed `txt` is matched as an OR across name + title fields.
	"""
	if not doctype:
		return []
	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except (TypeError, ValueError):
			filters = {}
	filters = filters or {}

	meta = frappe.get_meta(doctype)
	title_fields = _title_fields(meta)
	txt = (txt or "").strip()

	like = f"%{txt}%"
	or_filters = [["name", "like", like]] + [[f, "like", like] for f in title_fields]
	# Fetch name + the primary title field (for the label).
	label_field = title_fields[0] if title_fields else None
	fields = ["name"] + ([label_field] if label_field else [])

	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters if txt else None,
		fields=fields,
		limit_page_length=int(page_length or 20),
		order_by="modified desc",
	)
	out = []
	for r in rows:
		label = (r.get(label_field) if label_field else None) or r["name"]
		out.append({"name": r["name"], "label": label})
	return out
