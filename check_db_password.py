import database as db

db.init_db()
pass_admin_val = db.get_setting("pass_admin", "NexusExec2026!")
pass_staff_val = db.get_setting("pass_staff", "NexusStaff2026!")

print(f'🔑 Current DB pass_admin: {pass_admin_val}')
print(f'🔑 Current DB pass_staff: {pass_staff_val}')
