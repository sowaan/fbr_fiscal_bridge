app_name = "fbr_fiscal_bridge"
app_title = "FBR Fiscal Bridge"
app_publisher = "Fariz Khanzada"
app_description = "This app is used to fiscalize the Invoices through FBR IMS"
app_email = "khanzadafariz@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []
# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "fbr_fiscal_bridge",
# 		"logo": "/assets/fbr_fiscal_bridge/logo.png",
# 		"title": "FBR Fiscal Bridge",
# 		"route": "/fbr_fiscal_bridge",
# 		"has_permission": "fbr_fiscal_bridge.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/fbr_fiscal_bridge/css/fbr_fiscal_bridge.css"
# app_include_js = "/assets/fbr_fiscal_bridge/js/pos_offline_submit.js"
# include js in POS
# app_include_js = [
#     "/assets/fbr_fiscal_bridge/js/pos_fbr_override.js"
# ]
# app_include_js = "/assets/fbr_fiscal_bridge/js/qrcode.js"
# include js, css files in header of web template
# web_include_css = "/assets/fbr_fiscal_bridge/css/fbr_fiscal_bridge.css"
# web_include_js = "/assets/fbr_fiscal_bridge/js/fbr_fiscal_bridge.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "fbr_fiscal_bridge/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_js = {"Sales Invoice" : "public/js/sales_invoice.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "fbr_fiscal_bridge/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "fbr_fiscal_bridge.utils.jinja_methods",
# 	"filters": "fbr_fiscal_bridge.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "fbr_fiscal_bridge.install.before_install"
# after_install = "fbr_fiscal_bridge.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "fbr_fiscal_bridge.uninstall.before_uninstall"
# after_uninstall = "fbr_fiscal_bridge.uninstall.after_uninstall"
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["name", "in", [
                "Sales Invoice-custom_fbr_fiscal_invoice_number",
                "POS Profile-custom_pos_id",
                "Item-custom_pct_code",
                "Sales Invoice-ntn_no", 
                "Sales Invoice-fbr_invoice_no",
                "Sales Invoice-pos_id",
                "POS Profile-ntn_no",
                "POS Profile-pos_id",
                "POS Profile-pos_token",
                "POS Profile User-fbr_user",
                "POS Profile-is_fbr"
            ]]
        ],
        "module": "FBR Fiscal Bridge"
    }
]

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "fbr_fiscal_bridge.utils.before_app_install"
# after_app_install = "fbr_fiscal_bridge.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "fbr_fiscal_bridge.utils.before_app_uninstall"
# after_app_uninstall = "fbr_fiscal_bridge.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "fbr_fiscal_bridge.notifications.get_notification_config"

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

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
#     "Sales Invoice": {
#         "on_submit": "fbr_fiscal_bridge.fbr_fiscal_bridge.api.fbr_fiscal_component.send_offline_invoice"
#     }
# }
# doc_events = {
# 	"Sales Invoice": {
# 		"after_insert": "fbr_fiscal_bridge.events.sales_invoice.send_pos_invoice_fbr",
# 	}
# }


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"fbr_fiscal_bridge.tasks.all"
# 	],
# 	"daily": [
# 		"fbr_fiscal_bridge.tasks.daily"
# 	],
# 	"hourly": [
# 		"fbr_fiscal_bridge.tasks.hourly"
# 	],
# 	"weekly": [
# 		"fbr_fiscal_bridge.tasks.weekly"
# 	],
# 	"monthly": [
# 		"fbr_fiscal_bridge.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "fbr_fiscal_bridge.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
    "posawesome.posawesome.api.invoices.submit_invoice": 
        "fbr_fiscal_bridge.overrides.submit_invoice.submit_invoice"
}

#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "fbr_fiscal_bridge.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["fbr_fiscal_bridge.utils.before_request"]
# after_request = ["fbr_fiscal_bridge.utils.after_request"]

# Job Events
# ----------
# before_job = ["fbr_fiscal_bridge.utils.before_job"]
# after_job = ["fbr_fiscal_bridge.utils.after_job"]

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
# 	"fbr_fiscal_bridge.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

