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
			"mgk_is_karigan_order", "mgk_is_salavai_cone_order", "docstatus", "modified",
		],
		columns: [
			{ field: "name", label: "Order", type: "id" },
			{ field: "supplier_name", fallback: "supplier", label: "Supplier", linkTarget: "Supplier", linkValue: "supplier" },
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
				termKeys: {
					label: "purchase_order.books.karigan_order.label",
					short: "purchase_order.books.karigan_order.short",
				},
				note: "Purchase Orders containing Karigan items.",
				filters: [["mgk_is_karigan_order", "=", 1]],
			},
			{
				key: "salavai-cone-order",
				label: "Salavai Cone Order Book",
				short: "Salavai Cone Order",
				termKeys: {
					label: "purchase_order.books.salavai_cone_order.label",
					short: "purchase_order.books.salavai_cone_order.short",
				},
				note: "Purchase Orders containing Salavai items.",
				filters: [["mgk_is_salavai_cone_order", "=", 1]],
			},
			{
				key: "other-orders",
				label: "Other Orders Book",
				short: "Other Orders",
				note: "All remaining Purchase Orders.",
				filters: [
					["mgk_is_karigan_order", "=", 0],
					["mgk_is_salavai_cone_order", "=", 0],
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
			{ field: "supplier", label: "Supplier", linkTarget: "Supplier" },
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
			{
				key: "work-order-grn",
				label: "Work Order GRN Book",
				short: "Work Order GRN",
				note: "Materials received against Work Orders.",
				filters: [["against", "=", "Work Order"]],
			},
			{
				key: "po-grn",
				label: "PO GRN Book",
				short: "PO GRN",
				note: "Materials received against Purchase Orders.",
				filters: [["against", "=", "Purchase Order"]],
			},
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
			{ field: "supplier", label: "Supplier", linkTarget: "Supplier" },
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
			{
				key: "job-work-billing",
				label: "Job Work Billing Book",
				short: "Job Work Billing",
				note: "Supplier bills against Work Orders.",
				filters: [["against", "=", "Work Order"]],
			},
			{
				key: "po-billing",
				label: "PO Billing Book",
				short: "PO Billing",
				note: "Supplier bills against Purchase Orders.",
				filters: [["against", "=", "Purchase Order"]],
			},
		],
	},
	{
		key: "ipd",
		code: "IPD",
		label: "Item Production Detail",
		doctype: "Item Production Detail",
		directList: true,
		description: "Approved production routes, BOMs and process definitions.",
		cover: "ipd",
		fields: ["name", "item", "version", "approval_status", "docstatus", "modified"],
		columns: [
			{ field: "name", label: "Production Detail", type: "id" },
			{ field: "item", label: "Item", linkTarget: "Item" },
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
			{ field: "supplier_name", fallback: "supplier", label: "Supplier", linkTarget: "Supplier", linkValue: "supplier" },
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
		key: "woc",
		code: "WOC",
		label: "Work Order Correction",
		doctype: "Work Order Correction",
		directList: true,
		directPreview: "All Work Order corrections",
		description: "Add manual deliverables or receivables to an existing Work Order.",
		cover: "woc",
		fields: [
			"name", "work_order", "supplier", "process_name", "item", "correction_date",
			"status", "docstatus", "modified",
		],
		columns: [
			{ field: "name", label: "Correction", type: "id" },
			{ field: "work_order", label: "Work Order", linkTarget: "Work Order" },
			{ field: "supplier", label: "Job-worker", linkTarget: "Supplier" },
			{ field: "process_name", label: "Process" },
			{ field: "correction_date", label: "Correction Date", type: "date" },
			{ field: "status", label: "Status", type: "status" },
		],
		detailFields: [
			"work_order", "correction_date", "reason", "process_name", "item",
			"production_detail", "supplier", "delivery_location", "wo_date", "status",
		],
		books: [
			{ key: "work-order-corrections", label: "Work Order Corrections", short: "Corrections", note: "All manual Work Order corrections.", filters: [] },
		],
	},
	{
		key: "dc",
		code: "DC",
		label: "Delivery Challan",
		doctype: "Delivery Challan",
		directList: true,
		directPreview: "All dispatch entries",
		description: "Materials dispatched against Work Orders.",
		cover: "dc",
		fields: [
			"name", "work_order", "supplier", "process_name", "posting_date", "from_warehouse",
			"to_warehouse", "total_delivered_qty", "total_value", "transfer_complete",
			"docstatus", "modified",
		],
		columns: [
			{ field: "name", label: "Challan", type: "id" },
			{ field: "supplier", label: "Supplier", linkTarget: "Supplier" },
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
	{
		key: "se",
		code: "SE",
		label: "Stock Entry",
		doctype: "Stock Entry",
		directList: true,
		directPreview: "All stock movements",
		description: "Issue, receive, consume, or move stock between warehouses.",
		cover: "se",
		fields: [
			"name", "purpose", "posting_date", "from_supplier", "from_warehouse",
			"to_supplier", "to_warehouse", "total_amount", "per_transferred",
			"docstatus", "modified",
		],
		columns: [
			{ field: "name", label: "Stock Entry", type: "id" },
			{ field: "purpose", label: "Purpose" },
			{ field: "posting_date", label: "Posting Date", type: "date" },
			{ field: "from_warehouse", label: "From Warehouse", linkTarget: "Warehouse" },
			{ field: "to_warehouse", label: "To Warehouse", linkTarget: "Warehouse" },
			{ field: "total_amount", label: "Value", type: "currency" },
			{ field: "docstatus", label: "Status", type: "status" },
		],
		detailFields: [
			"purpose", "posting_date", "posting_time", "from_supplier", "from_warehouse",
			"to_supplier", "to_warehouse", "vehicle_no", "additional_amount",
			"total_amount", "per_transferred",
		],
		books: [
			{ key: "stock-entries", label: "Stock Entry Book", short: "Stock Entry", note: "All stock movements.", filters: [] },
		],
	},
	{
		key: "inspection",
		code: "IE",
		label: "Inspection Entry",
		doctype: "Inspection Entry",
		directList: true,
		directPreview: "GRN inspections",
		description: "Inspect GRN quantities and classify them by Received Type.",
		cover: "inspection",
		fields: [
			"name", "against", "against_id", "posting_date", "inspector",
			"status", "is_converted", "docstatus", "modified",
		],
		columns: [
			{ field: "name", label: "Inspection", type: "id" },
			{ field: "against_id", label: "Goods Received Note" },
			{ field: "posting_date", label: "Posting Date", type: "date" },
			{ field: "inspector", label: "Inspector" },
			{ field: "status", label: "Status", type: "status" },
		],
		detailFields: [
			"against_id", "posting_date", "posting_time", "inspector", "status", "is_converted",
		],
		books: [
			{
				key: "grn-inspections",
				label: "GRN Inspection Book",
				short: "GRN Inspection",
				note: "Inspection Entries created against submitted Goods Received Notes.",
				filters: [["against", "=", "Goods Received Note"]],
			},
		],
	},
]

export const MASTER_GROUPS = [
	{
		key: "items", route: "item", code: "ITM", label: "Items", doctype: "Item",
		description: "Yarn, fabric and other stock or purchase items.",
		fields: ["name", "name1", "mgk_tamil_name", "item_group", "default_unit_of_measure", "hsn_code", "is_stock_item", "is_purchase_item", "disabled", "modified"],
		columns: [
			{ field: "name1", fallback: "name", label: "Item", type: "id", localizedDoctype: "Item", linkValue: "name" },
			{ field: "item_group", label: "Item Group" },
			{ field: "default_unit_of_measure", label: "UOM" },
			{ field: "hsn_code", label: "HSN" },
			{ field: "disabled", label: "Status", type: "enabled" },
		],
	},
	{
		key: "suppliers", route: "supplier", code: "SUP", label: "Suppliers & Addresses", doctype: "Supplier",
		description: "Suppliers with their primary linked Address.",
		fields: ["name", "supplier_name", "mgk_tamil_name", "gstin", "pan", "disabled", "modified"],
		columns: [
			{ field: "supplier_name", fallback: "name", label: "Supplier", type: "id", localizedDoctype: "Supplier", linkValue: "name" },
			{ field: "primary_address", label: "Primary Address" },
			{ field: "gstin", label: "GSTIN" },
			{ field: "phone", label: "Phone" },
			{ field: "disabled", label: "Status", type: "enabled" },
		],
	},
	{
		key: "agents", route: "mgk-agent", code: "AGT", label: "MGK Agents", doctype: "MGK Agent",
		description: "Agents and their commission reference.",
		fields: ["name", "agent_name", "mgk_tamil_name", "commission_terms", "disabled", "modified"],
		columns: [
			{ field: "agent_name", fallback: "name", label: "Agent", type: "id", localizedDoctype: "MGK Agent", linkValue: "name" },
			{ field: "commission_terms", label: "Commission Terms" },
			{ field: "disabled", label: "Status", type: "enabled" },
		],
	},
	{
		key: "processes", route: "process", code: "PRC", label: "Processes", doctype: "Process",
		description: "Production and job-work stages, defaults, and transformation rules.",
		fields: [
			"name", "process_name", "is_yarn_process", "is_item_conversion", "is_group",
			"is_manual_entry_in_grn", "input_uom", "output_uom", "default_wastage",
			"default_excess", "default_lead_time_days", "wo_excess_allowed_percentage", "modified",
		],
		columns: [
			{ field: "process_name", fallback: "name", label: "Process", type: "id" },
			{ field: "input_uom", label: "Input UOM" },
			{ field: "output_uom", label: "Output UOM" },
			{ field: "is_yarn_process", label: "Yarn Process", type: "check" },
			{ field: "is_item_conversion", label: "Item Conversion", type: "check" },
		],
	},
	{
		key: "received-types", route: "received-type", code: "RT", label: "Received Types", doctype: "Received Type",
		description: "Stock receipt classifications used by GRNs and inspections.",
		fields: ["name", "received_type_name", "is_default", "modified"],
		columns: [
			{ field: "received_type_name", fallback: "name", label: "Received Type", type: "id" },
			{ field: "is_default", label: "Default", type: "check" },
			{ field: "modified", label: "Last Updated", type: "datetime" },
		],
	},
	{
		key: "warehouses", route: "warehouse", code: "WH", label: "Warehouses", doctype: "Warehouse",
		description: "Company stores and supplier-linked warehouses.",
		fields: ["name", "name1", "mgk_tamil_name", "supplier", "disabled", "modified"],
		columns: [
			{ field: "name1", fallback: "name", label: "Warehouse", type: "id", localizedDoctype: "Warehouse", linkValue: "name" },
			{ field: "supplier", label: "Linked Supplier", linkTarget: "Supplier" },
			{ field: "warehouse_type", label: "Type" },
			{ field: "disabled", label: "Status", type: "enabled" },
		],
	},
	{
		key: "item-prices", route: "item-price", code: "₹", label: "Item Prices", doctype: "Item Price",
		section: "prices-costs",
		description: "Supplier/item/UOM purchasing prices and approval state.",
		fields: ["name", "item_name", "supplier", "uom", "from_date", "to_date", "tax", "workflow_state", "docstatus", "modified"],
		columns: [
			{ field: "item_name", label: "Item", type: "id", linkTarget: "Item" },
			{ field: "supplier", label: "Supplier", linkTarget: "Supplier" },
			{ field: "uom", label: "UOM" },
			{ field: "from_date", label: "Valid From", type: "date" },
			{ field: "workflow_state", fallback: "docstatus", label: "Status", type: "status" },
		],
	},
	{
		key: "process-costs", route: "process-cost", code: "PC", label: "Process Costs", doctype: "Process Cost",
		section: "prices-costs",
		description: "Supplier/process/item-specific job-work costs.",
		fields: ["name", "process_name", "item", "supplier", "uom", "from_date", "to_date", "workflow_state", "docstatus", "modified"],
		columns: [
			{ field: "name", label: "Process Cost", type: "id" },
			{ field: "process_name", label: "Process" },
			{ field: "item", label: "Item", linkTarget: "Item" },
			{ field: "supplier", label: "Supplier", linkTarget: "Supplier" },
			{ field: "workflow_state", fallback: "docstatus", label: "Status", type: "status" },
		],
	},
	{
		key: "users", route: "user", code: "USR", label: "Users & Access", doctype: "User",
		description: "Users, enabled state and access information.", adminOnly: true,
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
