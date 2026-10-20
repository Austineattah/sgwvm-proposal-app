import database as db

db.init_db()
val = db.get_setting("pass_admin", "NexusExec2026!")
print(f'Raw value from DB: {repr(val)}')
print(f'Match with "NexusExec2026!": {val == "NexusExec2026!"}')
