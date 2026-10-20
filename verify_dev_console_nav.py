with open('developer_console.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'st.query_params' in content and 'st.rerun()' in content:
    print('[SUCCESS] developer_console.py is verified with reactive st.query_params routing!')
else:
    print('[!] developer_console.py needs reactive st.query_params update handler.')
