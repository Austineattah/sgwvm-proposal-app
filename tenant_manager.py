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

import os
import json

def load_tenants_registry():
    registry_path = 'tenants_registry.json'
    if not os.path.exists(registry_path):
        return {}
    try:
        with open(registry_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_tenant(client_slug, tenant_info):
    registry_path = 'tenants_registry.json'
    registry = load_tenants_registry()
    registry[client_slug] = tenant_info
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=4)
