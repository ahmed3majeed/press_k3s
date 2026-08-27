import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from press_k3s import apply_agent_patch, apply_site_patch


CUSTOM_FIELDS = {
    "Server": [
        {
            "fieldname": "custom_k3s_enabled",
            "label": "K3s Enabled",
            "fieldtype": "Check",
            "insert_after": "is_self_hosted",
            "description": "Use kagent (k3s) instead of the Docker agent URL.",
        },
        {
            "fieldname": "custom_k3s_agent_url",
            "label": "K3s Agent URL",
            "fieldtype": "Data",
            "insert_after": "custom_k3s_enabled",
            "depends_on": "eval:doc.custom_k3s_enabled",
            "default": "http://127.0.0.1:25052",
            "description": "Base URL of kagent, no trailing /agent.",
        },
    ],
    "Bench": [
        {
            "fieldname": "custom_k3s_bench_name",
            "label": "K3s Bench Name",
            "fieldtype": "Data",
            "insert_after": "status",
            "description": "kagent bench id, e.g. bench-v15.",
        },
    ],
}


def after_install():
    create_custom_fields(CUSTOM_FIELDS, update=True)
    apply_agent_patch()
    apply_site_patch()


def after_migrate():
    create_custom_fields(CUSTOM_FIELDS, update=True)
    apply_agent_patch()
    apply_site_patch()
