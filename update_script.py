path = 'sector_logic.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''        entity_type = st.selectbox(
            \"Select Organization / Entity Category*\",
            [
                \"Public University / Polytechnic / Research Institute (Academic Sector)\",
                \"Multinational Funder / UN Agency / International NGO (Humanitarian Sector)\",
                \"National Assembly / Parliament / Legislative Directorate\",
                \"Federal Ministry, Department, or Agency (MDA)\",
                \"State Ministry, Department, or Agency (MDA)\",
                \"Private Limited Company / Enterprise (Commercial Sector)\",
                \"Non-Profit Foundation / Civil Society Organization\"
            ]
        )'''

replacement = '''        entity_options = [
            \"Public University / Polytechnic / Research Institute (Academic Sector)\",
            \"Multinational Funder / UN Agency / International NGO (Humanitarian Sector)\",
            \"National Assembly / Parliament / Legislative Directorate\",
            \"Federal Ministry, Department, or Agency (MDA)\",
            \"State Ministry, Department, or Agency (MDA)\",
            \"Private Limited Company / Enterprise (Commercial Sector)\",
            \"Non-Profit Foundation / Civil Society Organization\",
            \"Others (Specify Custom Entity Category)\"
        ]

        entity_type_selection = st.selectbox(
            \"Select Organization / Entity Category*\",
            entity_options,
            key=\"entity_type_select\"
        )

        if entity_type_selection == \"Others (Specify Custom Entity Category)\":
            entity_type_custom = st.text_input(
                \"Please Specify Custom Entity Category*\",
                placeholder=\"e.g., Specialized Public Commission / Private Trust\",
                key=\"entity_type_custom_input\"
            )
            entity_type = entity_type_custom
        else:
            entity_type = entity_type_selection'''

if target in content:
    new_content = content.replace(target, replacement)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('SUCCESS: sector_logic.py updated with absolute precision.')
else:
    print('NOTICE: Exact target block formatting differed slightly. Applying regex/line-based update...')
    import re
    # Fallback pattern replacement for entity_type selection block
    pattern = r'entity_type\s*=\s*st\.selectbox\(\s*"Select Organization / Entity Category\*".*?\]\s*\)'
    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count > 0:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('SUCCESS: sector_logic.py updated via regex fallback.')
    else:
        print('ERROR: Could not locate target block.')
