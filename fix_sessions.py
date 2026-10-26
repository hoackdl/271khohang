import sqlite3

DB_PATH = "E:/My Drive/Python Web/XML/271khohang/khohang271db.sqlite3"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("🔍 Checking django_migrations for sessions...")

cur.execute("SELECT * FROM django_migrations WHERE app='sessions'")
rows = cur.fetchall()
print("Before:", rows)

cur.execute("DELETE FROM django_migrations WHERE app='sessions'")
conn.commit()

print("✅ Deleted sessions migrations")

conn.close()


# python fix_sessions.py