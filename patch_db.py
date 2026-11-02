import database
import os

code_to_add = '''
import pandas as pd

def get_all_tenants():
    \"\"\"Retrieve all onboarded tenant records from the persistent database.\"\"\"
    try:
        conn = sqlite3.connect(\"database.db\")
        query = \"SELECT * FROM tenants\"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()
'''

with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'def get_all_tenants' not in content:
    with open('database.py', 'a', encoding='utf-8') as f:
        f.write(code_to_add)
    print('get_all_tenants successfully appended to database.py!')
else:
    print('get_all_tenants already exists in database.py.')
