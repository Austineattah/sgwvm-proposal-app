import os
import streamlit as st
from app_viewer import render_compendium_viewer

def render_compendium_section():
    st.markdown("## 📚 Legislative Compendium Explorer")
    st.markdown("Select an official compendium below to view its ultra-optimized pages instantly.")
    
    asset_dir = "assets"
    if not os.path.exists(asset_dir):
        st.warning("Assets directory not found.")
        return
        
    pdf_files = sorted([f for f in os.listdir(asset_dir) if f.endswith("_ultra_compressed.pdf") and "compressed_" not in f and "optimized_" not in f])
    
    if not pdf_files:
        st.error("No ultra-compressed compendiums found in assets.")
        return
        
    selected_file = st.selectbox("Choose Compendium Volume:", pdf_files)
    pdf_path = os.path.join(asset_dir, selected_file)
    
    render_compendium_viewer(pdf_path)

if __name__ == "__main__":
    st.set_page_config(page_title="NexusVault Developer Console", layout="wide")
    render_compendium_section()
