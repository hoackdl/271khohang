import os
import subprocess
import sqlite3
import decimal
import datetime
import json
import uuid
import getpass

from sshtunnel import SSHTunnelForwarder
import psycopg2

# ==================================================
# AUTO FLAGS
# ==================================================
RESET_PROJECT   = True
AUTO_MIGRATE    = True
AUTO_SUPERUSER  = False
AUTO_RUNSERVER  = False

# ==================================================
# PATH / APP
# ==================================================
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_FILE    = os.path.join(BASE_DIR, "khohang271db.sqlite3")
DJANGO_APP = "invoice_reader_app"

# ==================================================
# SSH CONFIG
# ==================================================
SSH_HOST = "103.56.161.170"
SSH_PORT = 24700
SSH_USER = "root"

# ==================================================
# POSTGRES CONFIG
# ==================================================
PG_DB   = "khohang271db"
PG_USER = "khohanguser"

# ==================================================
# SQLITE CONFIG
# ==================================================
sqlite3.register_adapter(decimal.Decimal, float)

SKIP_TABLES = {
    # django core
    "django_migrations",
    "django_session",
    "django_admin_log",
    "django_content_type",

    # auth
    "auth_user",
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    "auth_user_groups",
    "auth_user_user_permissions",
}

# ==================================================
# UTILS
# ==================================================
def run(cmd):
    print(f"\n▶ {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def convert_value(val):
    if val is None:
        return None
    if isinstance(val, decimal.Decimal):
        return float(val)
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, (bytes, memoryview)):
        return val.decode("utf-8", errors="ignore")
    return val

# ==================================================
# RESET PROJECT
# ==================================================
def reset_project():
    print("\n🧹 RESET PROJECT")

    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("🗑 Deleted sqlite db")

# ==================================================
# DJANGO MIGRATE (CREATE SCHEMA)
# ==================================================
def django_migrate():
    print("\n🧩 DJANGO MIGRATIONS")

    run("python manage.py migrate contenttypes")
    run("python manage.py migrate auth")
    run("python manage.py migrate admin")
    run("python manage.py migrate sessions")

    run(f"python manage.py makemigrations {DJANGO_APP}")
    run(f"python manage.py migrate {DJANGO_APP}")

    run("python manage.py migrate")

# ==================================================
# IMPORT DATA PG → SQLITE
# ==================================================
def import_pg_to_sqlite():
    ssh_pass = getpass.getpass("🔑 SSH password: ")
    pg_pass  = getpass.getpass("🔑 PostgreSQL password: ")

    print("\n🔌 Opening SSH tunnel...")

    with SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_password=ssh_pass,
        remote_bind_address=("localhost", 5432),
        local_bind_address=("localhost", 5433),
    ):
        print("✅ SSH tunnel OK")

        pg = psycopg2.connect(
            host="localhost",
            port=5433,
            dbname=PG_DB,
            user=PG_USER,
            password=pg_pass
        )
        pg_cur = pg.cursor()

        sq = sqlite3.connect(DB_FILE)
        sq_cur = sq.cursor()

        pg_cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
        """)
        tables = [r[0] for r in pg_cur.fetchall()]

        print("📋 Tables:", tables)

        for table in tables:
            if table in SKIP_TABLES:
                print(f"⏭ Skip {table}")
                continue

            print(f"\n📦 Import {table}")

            pg_cur.execute(f'SELECT * FROM "{table}"')
            col_names = [desc[0] for desc in pg_cur.description]

            placeholders = ",".join(["?"] * len(col_names))
            cols_sql = ",".join(f'"{c}"' for c in col_names)

            total = 0
            while True:
                rows = pg_cur.fetchmany(1000)
                if not rows:
                    break

                rows = [
                    tuple(
                        "" if (col_names[i] == "stt" and v is None) else convert_value(v)
                        for i, v in enumerate(r)
                    )
                    for r in rows
                ]

                sq_cur.executemany(
                    f'INSERT INTO "{table}" ({cols_sql}) VALUES ({placeholders})',
                    rows
                )
                sq.commit()

                total += len(rows)
                print(f"   ↳ {total} rows", end="\r")

            print(f"\n   ✅ Done {table}: {total} rows")

        pg.close()
        sq.close()

    print("\n🎉 IMPORT HOÀN TẤT")

# ==================================================
# MAIN
# ==================================================
if __name__ == "__main__":

    if RESET_PROJECT:
        reset_project()

    if AUTO_MIGRATE:
        django_migrate()

    import_pg_to_sqlite()

    if AUTO_RUNSERVER:
        run("python manage.py runserver")

# Kéo dữ liệu từ server về local
# python reset_khohang271db.py
# python manage.py createsuperuser
# python manage.py runserver