export function slugify(value) {
	return String(value || "")
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-+|-+$/g, "")
}

export const TRANSACTION_GROUPS = [
	{
		key: "po",
		code: "PO",
		label: "Purchase Order",
		doctype: "Purchase Order",
		description: "Orders placed with yarn and material suppliers.",
		cover: "po",
		fields: [
			"name", "supplier", "supplier_name", "po_date", "expected_delivery_date",
			"delivery_warehouse", "total_qty", "grand_total", "open_status", "status",
			"docstatus", "modified",
		],
		columns: [
			{ field: "name", label: "Order", type: "id" },
			{ field: "supplier_name", fallback: "supplier", label: "Supplier" },
			{ field: "po_date", label: "Order Date", type: "date" },
			{ field: "total_qty", label: "Quantity", type: "quantity" },
			{ field: "grand_total", label: "Grand Total", type: "currency" },
			{ field: "status", label: "Status", type: "status" },
		],
		detailFields: [
			"supplier", "supplier_name", "po_date", "expected_delivery_date",
			"delivery_warehouse", "mgk_agent", "mgk_goods_routing", "mgk_handling_supplier",
			"total_qty", "total", "total_tax", "grand_total", "open_status", "status",
		],
		books: [
			{
				key: "karigan-order",
				label: "Karigan Order Book",
				short: "Karigan Order",
				note: "Purchase Orders containing Karigan items.",
				filters: [["Purchase Order Item", "item_variant", "like", "%Karigan%"]],
			},
			{
				key: "salavai-cone-order",
				label: "Salavai Cone Order Book",
				short: "Salavai Cone Order",
				note: "Purchase Orders containing Salavai items.",
				filters: [["Purchase Order Item", "item_variant", "like", "%Salavai%"]],
			},
			{
				key: "other-orders",
				label: "Other Orders Book",
				short: "Other Orders",
				note: "All remaining Purchase Orders.",
				filters: [
					["Purchase Order Item", "item_variant", "not like", "%Karigan%"],
					["Purchase Order Item", "item_variant", "not like", "%Salavai%"],
				],
			},
		],
	},
	{
		key: "grn",
		code: "GRN",
		label: "Goods Received Note",
		doctype: "Goods Received Note",
		description: "Materials received against Purchase Orders or Work Orders.",
		cover: "grn",
		fields: [
			"name", "supplier", "against", "against_id", "posting_date", "to_warehouse",
			"total_received_quantity", "total", "transfer_complete", "docstatus", "modified",
		],
		columns: [
			{ field: "name", label: "GRN", type: "id" },
			{ field: "supplier", label: "Supplier" },
			{ field: "against_id", fallback: "against", label: "Against" },
			{ field: "posting_date", label: "Posting Date", type: "date" },
			{ field: "total_received_quantity", label: "Received Qty", type: "quantity" },
			{ field: "docstatus", label: "Status", type: "status" },
		],
		detailFields: [
			"against", "against_id", "supplier", "posting_date", "posting_time", "process_name",
			"item", "from_warehouse", "to_warehouse", "supplier_document_no", "vehicle_no",
			"total_received_quantity", "total", "freight_charges", "transfer_complete",
		],
		books: [
			{ key: "goods-received", label: "Goods Received Book", short: "Goods Received", note: "All incoming material receipts.", filters: [] },
		],
	},
	{
		key: "pi",
		code: "PI",
		label: "Billing",
		doctype: "Purchase Invoice",
		description: "Supplier invoices connected to received materials and job work.",
		cover: "pi",
		fields: [
			"name", "supplier", "billing_supplier", "bill_no", "posting_date", "bill_date",
			"total_quantity", "grand_total", "status", "docstatus", "modified",
		],
		columns: [
			{ field: "name", label: "Invoice", type: "id" },
			{ field: "supplier", label: "Supplier" },
			{ field: "bill_no", label: "Supplier Bill" },
			{ field: "posting_date", label: "Posting Date", type: "date" },
			{ field: "grand_total", label: "Grand Total", type: "currency" },
			{ field: "status", label: "Status", type: "status" },
		],
		detailFields: [
			"supplier", "billing_supplier", "against", "bill_no", "bill_date", "posting_date",
			"due_date", "total_quantity", "total", "total_tax", "grand_total", "status",
		],
		books: [
			{ key: "purchase-invoices", label: "Purchase Invoice Book", short: "Purchase Invoice", note: "All supplier billing entries.", filters: [] },
		],
	},
	{
		key: "ipd",
		code: "IPD",
		label: "Item Production Detail",
		doctype: "Item Production Detail",
		description: "Approved production routes, BOMs and process definitions.",
		cover: "ipd",
		fields: ["name", "item", "version", "approval_status", "docstatus", "modified"],
		columns: [
			{ field: "name", label: "Production Detail", type: "id" },
			{ field: "item", label: "Item" },
			{ field: "version", label: "Version" },
			{ field: "approval_status", label: "Approval", type: "status" },
			{ field: "modified", label: "Last Updated", type: "datetime" },
		],
		detailFields: [
			"item", "version", "approval_status", "approved_by", "primary_item_attribute",
			"dependent_attribute", "dependent_attribute_mapping", "yarn_item",
		],
		books: [
			{ key: "production-details", label: "Production Detail Book", short: "Production Detail", note: "All Item Production Details.", filters: [] },
		],
	},
	{
		key: "wo",
		code: "WO",
		label: "Work Order",
		doctype: "Work Order",
		description: "Job-work instructions separated by the process people recognise.",
		cover: "wo",
		fields: [
			"name", "supplier", "supplier_name", "process_name", "item", "wo_date",
			"planned_start_date", "expected_delivery_date", "total_quantity", "status",
			"open_status", "docstatus", "modified",
		],
		columns: [
			{ field: "name", label: "Work Order", type: "id" },
			{ field: "supplier_name", fallback: "supplier", label: "Supplier" },
			{ field: "process_name", label: "Process" },
			{ field: "wo_date", label: "WO Date", type: "date" },
			{ field: "total_quantity", label: "Quantity", type: "quantity" },
			{ field: "status", label: "Status", type: "status" },
		],
		detailFields: [
			"supplier", "supplier_name", "process_name", "item", "wo_date", "planned_start_date",
			"planned_end_date", "expected_delivery_date", "delivery_location", "process_cost",
			"total_quantity", "planned_quantity", "open_status", "status", "is_internal_unit",
		],
		books: [
			{ key: "dyeing", label: "Dyeing Work Order Book", short: "Dyeing", note: "Work Orders for the Dyeing process.", filters: [["process_name", "=", "Dyeing"]] },
			{ key: "doubling", label: "Doubling Work Order Book", short: "Doubling", note: "Work Orders for the Doubling process.", filters: [["process_name", "=", "Doubling"]] },
			{ key: "other-job-work", label: "Other Job Work Book", short: "Other Job Work", note: "All other Work Order processes.", filters: [["process_name", "not in", ["Dyeing", "Doubling"]]] },
		],
	},
	{
		key: "dc",
		code: "DC",
		label: "Delivery Challan",
		doctype: "Delivery Challan",
		description: "Materials dispatched against Work Orders.",
		cover: "dc",
		fields: [
			"name", "work_order", "supplier", "process_name", "posting_date", "from_warehouse",
			"to_warehouse", "total_delivered_qty", "total_value", "transfer_complete",
			"docstatus", "modified",
		],
		columns: [
			{ field: "name", label: "Challan", type: "id" },
			{ field: "supplier", label: "Supplier" },
			{ field: "work_order", label: "Work Order" },
			{ field: "posting_date", label: "Posting Date", type: "date" },
			{ field: "total_delivered_qty", label: "Delivered Qty", type: "quantity" },
			{ field: "docstatus", label: "Status", type: "status" },
		],
		detailFields: [
			"work_order", "supplier", "process_name", "item", "posting_date", "posting_time",
			"from_location", "from_warehouse", "to_warehouse", "vehicle_no", "total_delivered_qty",
			"stock_value", "total_value", "transfer_complete",
		],
		books: [
			{ key: "delivery-challans", label: "Delivery Challan Book", short: "Delivery Challan", note: "All outward job-work dispatches.", filters: [] },
		],
	},
]

export const MASTER_GROUPS = [
	{
		key: "items", code: "ITM", label: "Items", doctype: "Item",
		description: "Yarn, fabric and other stock or purchase items.",
		usage: ["Purchase Order", "GRN", "Purchase Invoice", "Production"],
		fields: ["name", "name1", "item_group", "default_unit_of_measure", "hsn_code", "is_stock_item", "is_purchase_item", "disabled", "modified"],
		columns: [
			{ field: "name1", fallback: "name", label: "Item", type: "id" },
			{ field: "item_group", label: "Item Group" },
			{ field: "default_unit_of_measure", label: "UOM" },
			{ field: "hsn_code", label: "HSN" },
			{ field: "disabled", label: "Status", type: "enabled" },
		],
	},
	{
		key: "suppliers", code: "SUP", label: "Suppliers & Addresses", doctype: "Supplier",
		description: "Suppliers with their primary linked Address.",
		usage: ["Purchase Order", "GRN", "Purchase Invoice"],
		fields: ["name", "supplier_name", "gstin", "pan", "disabled", "modified"],
		columns: [
			{ field: "supplier_name", fallback: "name", label: "Supplier", type: "id" },
			{ field: "primary_address", label: "Primary Address" },
			{ field: "gstin", label: "GSTIN" },
			{ field: "phone", label: "Phone" },
			{ field: "disabled", label: "Status", type: "enabled" },
		],
	},
	{
		key: "agents", code: "AGT", label: "MGK Agents", doctype: "MGK Agent",
		description: "Agents and their commission reference.", usage: ["Purchase Order"],
		fields: ["name", "agent_name", "commission_terms", "disabled", "modified"],
		columns: [
			{ field: "agent_name", fallback: "name", label: "Agent", type: "id" },
			{ field: "commission_terms", label: "Commission Terms" },
			{ field: "disabled", label: "Status", type: "enabled" },
		],
	},
	{
		key: "warehouses", code: "WH", label: "Warehouses", doctype: "Warehouse",
		description: "Company stores and supplier-linked warehouses.", usage: ["Purchase Order", "GRN", "Stock"],
		fields: ["name", "name1", "supplier", "disabled", "modified"],
		columns: [
			{ field: "name1", fallback: "name", label: "Warehouse", type: "id" },
			{ field: "supplier", label: "Linked Supplier" },
			{ field: "warehouse_type", label: "Type" },
			{ field: "disabled", label: "Status", type: "enabled" },
		],
	},
	{
		key: "item-prices", code: "₹", label: "Item Prices", doctype: "Item Price",
		description: "Supplier/item/UOM purchasing prices and approval state.", usage: ["Purchase Order", "Purchase Invoice"],
		fields: ["name", "item", "supplier", "uom", "from_date", "to_date", "tax_slab", "docstatus", "modified"],
		columns: [
			{ field: "item", label: "Item", type: "id" },
			{ field: "supplier", label: "Supplier" },
			{ field: "uom", label: "UOM" },
			{ field: "from_date", label: "Valid From", type: "date" },
			{ field: "docstatus", label: "Status", type: "status" },
		],
	},
	{
		key: "process-costs", code: "PC", label: "Process Costs", doctype: "Process Cost",
		description: "Supplier/process/item-specific job-work costs.", usage: ["Item Production Detail", "Work Order"],
		fields: ["name", "process_name", "item", "supplier", "uom", "from_date", "to_date", "docstatus", "modified"],
		columns: [
			{ field: "name", label: "Process Cost", type: "id" },
			{ field: "process_name", label: "Process" },
			{ field: "item", label: "Item" },
			{ field: "supplier", label: "Supplier" },
			{ field: "docstatus", label: "Status", type: "status" },
		],
	},
	{
		key: "users", code: "USR", label: "Users & Access", doctype: "User",
		description: "Users, enabled state and access information.", usage: ["Administrator only", "Roles", "UI Preference"], adminOnly: true,
		fields: ["name", "full_name", "email", "mobile_no", "enabled", "last_active", "modified"],
		columns: [
			{ field: "full_name", fallback: "name", label: "User", type: "id" },
			{ field: "email", fallback: "name", label: "Email" },
			{ field: "mobile_no", label: "Mobile" },
			{ field: "last_active", label: "Last Active", type: "datetime" },
			{ field: "enabled", label: "Status", type: "user_enabled" },
		],
	},
]

export function getTransactionGroup(key) {
	return TRANSACTION_GROUPS.find((group) => group.key === key) || null
}

export function getMasterGroup(key) {
	return MASTER_GROUPS.find((group) => group.key === key) || null
}

export function getBook(groupKey, bookKey) {
	return getTransactionGroup(groupKey)?.books.find((book) => book.key === bookKey) || null
}

export function hasChildTableFilters(doctype, filters = []) {
	return filters.some((filter) => Array.isArray(filter) && filter.length >= 4 && filter[0] !== doctype)
}
