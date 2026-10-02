import sqlite3

DB = "E:/My Drive/Python Web/XML/271khohang/khohang271db.sqlite3"

tables = [
    "auth_user",
    "auth_group",
    "auth_permission",
    "auth_group_permissions",
    "auth_user_groups",
    "auth_user_user_permissions",
    "django_admin_log",
    "django_content_type",
]

conn = sqlite3.connect(DB)
cur = conn.cursor()

for t in tables:
    try:
        cur.execute(f"DROP TABLE IF EXISTS {t}")
        print(f"🧹 Dropped {t}")
    except Exception as e:
        print(f"⚠️ {t}: {e}")

cur.execute("DELETE FROM django_migrations WHERE app IN ('auth','admin','contenttypes')")
conn.commit()
conn.close()

print("✅ AUTH + ADMIN reset xong")



# python reset_auth_sqlite.py