app_name = "mgk_clothing_yrp"
app_title = "MGK Clothing YRP"
app_publisher = "anas@essdee.fit"
app_description = "Tiwel Manufacturing"
app_email = "anas@essdee.fit"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "mgk_clothing_yrp",
		"logo": "/assets/mgk_clothing_yrp/frontend/favicon.png",
		"title": "MGK Clothing",
		"route": "/web",
	}
]

# SPA catch-all: deep links under /web (the Vue router runs in history mode with
# base "/web") all resolve to the web.html template, which boots the SPA.
website_route_rules = [
	{"from_route": "/web/<path:app_path>", "to_route": "web"},
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/mgk_clothing_yrp/css/mgk_clothing_yrp.css"
# app_include_js = "/assets/mgk_clothing_yrp/js/mgk_clothing_yrp.js"

# include js, css files in header of web template
# web_include_css = "/assets/mgk_clothing_yrp/css/mgk_clothing_yrp.css"
# web_include_js = "/assets/mgk_clothing_yrp/js/mgk_clothing_yrp.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "mgk_clothing_yrp/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "mgk_clothing_yrp/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# Post-login landing: ordinary users land on the custom /web work hub;
# System Manager / Administrator keep the Desk default (function returns None
# for them, so Frappe falls through). See mgk_clothing_yrp/www_home.py.
get_website_user_home_page = "mgk_clothing_yrp.www_home.get_website_user_home_page"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "mgk_clothing_yrp.utils.jinja_methods",
# 	"filters": "mgk_clothing_yrp.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "mgk_clothing_yrp.install.before_install"
# after_install = "mgk_clothing_yrp.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "mgk_clothing_yrp.uninstall.before_uninstall"
# after_uninstall = "mgk_clothing_yrp.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "mgk_clothing_yrp.utils.before_app_install"
# after_app_install = "mgk_clothing_yrp.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "mgk_clothing_yrp.utils.before_app_uninstall"
# after_app_uninstall = "mgk_clothing_yrp.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "mgk_clothing_yrp.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mgk_clothing_yrp.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"mgk_clothing_yrp.tasks.all"
# 	],
# 	"daily": [
# 		"mgk_clothing_yrp.tasks.daily"
# 	],
# 	"hourly": [
# 		"mgk_clothing_yrp.tasks.hourly"
# 	],
# 	"weekly": [
# 		"mgk_clothing_yrp.tasks.weekly"
# 	],
# 	"monthly": [
# 		"mgk_clothing_yrp.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "mgk_clothing_yrp.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "mgk_clothing_yrp.custom.task.CustomTaskMixin"
# }

# Override Controller Class
# ------------------------------
#
# Per-row yarn process costing: MGKWorkOrder subclasses yrp's Work Order
# controller and overrides set_receivable_process_costs so item-less (mgk_items)
# yarn WOs cost each receivable by its own yarn item's Process Cost. Non-yarn
# WOs defer to base behaviour.

override_doctype_class = {
	"Work Order": "mgk_clothing_yrp.overrides.work_order_class.MGKWorkOrder",
}

# Overriding Methods
# ------------------------------

override_whitelisted_methods = {
	"yrp.yrp.doctype.purchase_invoice.purchase_invoice.fetch_grn_details": "mgk_clothing_yrp.overrides.purchase_invoice.fetch_grn_details",
}

# Fixtures
# ------------------
# Custom Fields owned by this app (module-tagged) travel with it.

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "MGK Clothing YRP"]]},
	{
		"dt": "Property Setter",
		"filters": [
			[
				"name",
				"in",
				[
					"Work Order-item-reqd",
					"Work Order-item-hidden",
					"Work Order-production_detail-hidden",
					"Item Production Detail-tech_pack_version-hidden",
					"Item Production Detail-pattern_version-hidden",
					"Work Order-main-field_order",
				],
			]
		],
	},
]

# Document Events
# ---------------

doc_events = {
	"Purchase Order": {
		"validate": "mgk_clothing_yrp.overrides.purchase_order.validate",
		"before_submit": "mgk_clothing_yrp.overrides.purchase_order.before_submit",
	},
	"Work Order": {
		"before_submit": "mgk_clothing_yrp.overrides.work_order.before_submit",
	},
}

# include js in doctype views
doctype_js = {
	"Purchase Order": "public/js/purchase_order_mgk.js",
	"Work Order": "public/js/work_order_mgk.js",
	"Item Production Detail": "public/js/item_production_detail_mgk.js",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mgk_clothing_yrp.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["mgk_clothing_yrp.utils.before_request"]
# after_request = ["mgk_clothing_yrp.utils.after_request"]

# Job Events
# ----------
# before_job = ["mgk_clothing_yrp.utils.before_job"]
# after_job = ["mgk_clothing_yrp.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"mgk_clothing_yrp.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
