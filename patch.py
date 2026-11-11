import pathlib

sec_path = pathlib.Path("tests/test_session_security.py")
if sec_path.exists():
    content = sec_path.read_text(encoding="utf-8")
    target = "APP_HARNESS = \"\"\""
    replacement = "APP_HARNESS = \"\"\"\nfrom app import _handle_primary_workspace_change"
    if target in content and "_handle_primary_workspace_change" not in content:
        content = content.replace(target, replacement, 1)
        sec_path.write_text(content, encoding="utf-8")
        print("Successfully updated tests/test_session_security.py")

box_path = pathlib.Path("tests/test_committee_sandbox.py")
if box_path.exists():
    content = box_path.read_text(encoding="utf-8")
    target = "_WORKSPACE_HARNESS = \"\"\""
    replacement = "_WORKSPACE_HARNESS = \"\"\"\nimport streamlit as st"
    if target in content and "import streamlit as st" not in content:
        content = content.replace(target, replacement, 1)
        box_path.write_text(content, encoding="utf-8")
        print("Successfully updated tests/test_committee_sandbox.py")

