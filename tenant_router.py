import streamlit as st
import os
import json

def get_current_tenant_slug():
    """Safely extract tenant slug from URL query parameters without altering core app state."""
    try:
        query_params = st.query_params
        if "tenant" in query_params:
            tenant_val = query_params["tenant"]
            return tenant_val[0] if isinstance(tenant_val, list) else tenant_val
        elif "client" in query_params:
            client_val = query_params["client"]
            return client_val[0] if isinstance(client_val, list) else client_val
    except Exception as e:
        print(f"Router query param warning: {e}")
    return None

def resolve_tenant_view():
    """Checks if a valid tenant is requested and returns tenant details if available."""
    slug = get_current_tenant_slug()
    if not slug:
        return None
        
    registry_path = "tenants_registry.json"
    if os.path.exists(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
                if slug in registry:
                    return registry[slug]
        except Exception as e:
            print(f"Error reading tenant registry: {e}")
    return None

