import admin_portal

print('🔍 Functions and attributes available in admin_portal.py:')
for attr in dir(admin_portal):
    if not attr.startswith('__'):
        print(f' - {attr}')
