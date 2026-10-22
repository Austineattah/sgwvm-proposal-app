import json
import os

TENANT_FILE = "tenants_registry.json"

def load_tenants():
    if not os.path.exists(TENANT_FILE):
        return {}
    try:
        with open(TENANT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_tenant(slug, tenant_data):
    tenants = load_tenants()
    tenants[slug] = tenant_data
    with open(TENANT_FILE, "w", encoding="utf-8") as f:
        json.dump(tenants, f, indent=4)

def get_tenant(slug):
    tenants = load_tenants()
    return tenants.get(slug)
