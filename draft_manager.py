import json
import os
from datetime import datetime

DRAFT_FILE = "nexusvault_form_drafts.json"

def save_draft(form_type, data_dict):
    """Saves form input progress to local persistent JSON file."""
    drafts = get_all_drafts()
    data_dict["last_saved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    drafts[form_type] = data_dict
    
    with open(DRAFT_FILE, "w", encoding="utf-8") as f:
        json.dump(drafts, f, indent=4)

def get_all_drafts():
    """Fetches all saved form drafts."""
    if not os.path.exists(DRAFT_FILE):
        return {}
    try:
        with open(DRAFT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def get_draft(form_type):
    """Retrieves draft for specific form category."""
    drafts = get_all_drafts()
    return drafts.get(form_type, None)

def clear_draft(form_type):
    """Clears saved draft after successful submission."""
    drafts = get_all_drafts()
    if form_type in drafts:
        del drafts[form_type]
        with open(DRAFT_FILE, "w", encoding="utf-8") as f:
            json.dump(drafts, f, indent=4)