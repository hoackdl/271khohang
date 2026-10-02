import os
import subprocess
import sqlite3
import decimal
import datetime
import json
import uuid
import getpass
import sys

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
# SQLITE
# ==================================================

sqlite3.register_adapter(decimal.Decimal, float)


# ==================================================
# TABLES TO SKIP
# ==================================================

SKIP_TABLES = {
    # Django core
    "django_migrations",
    "django_session",
    "django_admin_log",
    "django_content_type",

    # Auth
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
# RESET SQLITE
# ==================================================

def reset_project():
    print("\n" + "=" * 60)
    print("🧹 RESET PROJECT")
    print("=" * 60)

    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"🗑 Deleted: {DB_FILE}")
    else:
        print("ℹ SQLite DB chưa tồn tại")


# ==================================================
# DJANGO MIGRATIONS
# ==================================================

def django_migrate():
    print("\n" + "=" * 60)
    print("🧩 DJANGO MIGRATIONS")
    print("=" * 60)

    run(f"python manage.py makemigrations {DJANGO_APP}")
    run("python manage.py migrate")


# ==================================================
# GET SQLITE TABLE COLUMNS
# ==================================================

def get_sqlite_columns(sq_cur, table):
    """
    Lấy danh sách cột thực tế của SQLite.
    """

    sq_cur.execute(f'PRAGMA table_info("{table}")')

    rows = sq_cur.fetchall()

    # PRAGMA table_info:
    # cid, name, type, notnull, dflt_value, pk

    return [row[1] for row in rows]


# ==================================================
# GET SQLITE PRIMARY KEY
# ==================================================

def get_sqlite_primary_keys(sq_cur, table):
    sq_cur.execute(f'PRAGMA table_info("{table}")')

    rows = sq_cur.fetchall()

    return [
        row[1]
        for row in rows
        if row[5] > 0
    ]


# ==================================================
# CHECK POSTGRES TABLE EXISTS
# ==================================================

def postgres_table_exists(pg_cur, table):
    pg_cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = %s
        )
        """,
        (table,)
    )

    return pg_cur.fetchone()[0]


# ==================================================
# GET POSTGRES COLUMNS
# ==================================================

def get_postgres_columns(pg_cur, table):
    pg_cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,)
    )

    return [row[0] for row in pg_cur.fetchall()]


# ==================================================
# CHECK DUPLICATE PRIMARY KEY
# ==================================================

def check_duplicate_ids(pg_cur, table, pk_column):
    """
    Kiểm tra PK PostgreSQL có bị trùng không.
    """

    print(
        f"   🔎 Checking duplicate {pk_column}..."
    )

    pg_cur.execute(
        f'''
        SELECT "{pk_column}", COUNT(*)
        FROM "{table}"
        GROUP BY "{pk_column}"
        HAVING COUNT(*) > 1
        LIMIT 20
        '''
    )

    duplicates = pg_cur.fetchall()

    if duplicates:
        print()
        print("❌ PHÁT HIỆN ID TRÙNG TRONG POSTGRESQL")
        print(f"   Table : {table}")
        print(f"   PK    : {pk_column}")

        for value, count in duplicates:
            print(
                f"   - {pk_column}={value!r}: {count} rows"
            )

        raise RuntimeError(
            f"PostgreSQL table {table} có "
            f"{pk_column} bị trùng."
        )

    print("   ✅ Không có ID trùng")


# ==================================================
# RESET SQLITE TABLE DATA
# ==================================================

def clear_sqlite_table(sq_cur, table):
    """
    Xóa dữ liệu trước khi import.
    """

    sq_cur.execute(
        f'DELETE FROM "{table}"'
    )


# ==================================================
# UPDATE SQLITE AUTOINCREMENT
# ==================================================

def update_sqlite_sequence(sq_cur, table):
    """
    Nếu bảng có id INTEGER PRIMARY KEY AUTOINCREMENT,
    cập nhật sqlite_sequence để lần INSERT tiếp theo
    không đụng ID đã import.
    """

    try:
        sq_cur.execute(
            f'''
            SELECT MAX("id")
            FROM "{table}"
            '''
        )

        result = sq_cur.fetchone()

        if not result or result[0] is None:
            return

        max_id = result[0]

        sq_cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name='sqlite_sequence'
            """
        )

        if not sq_cur.fetchone():
            return

        sq_cur.execute(
            """
            INSERT INTO sqlite_sequence(name, seq)
            VALUES (?, ?)
            ON CONFLICT(name)
            DO UPDATE SET seq=excluded.seq
            """,
            (table, max_id)
        )

    except sqlite3.Error:
        # Không phải bảng nào cũng có sqlite_sequence.
        pass


# ==================================================
# IMPORT ONE TABLE
# ==================================================

def import_one_table(
    pg_cur,
    sq_cur,
    sq,
    table
):

    print("\n" + "-" * 60)
    print(f"📦 IMPORT: {table}")
    print("-" * 60)

    # --------------------------------------------------
    # PostgreSQL columns
    # --------------------------------------------------

    pg_columns = get_postgres_columns(
        pg_cur,
        table
    )

    if not pg_columns:
        print("⚠ Không có cột PostgreSQL")
        return

    # --------------------------------------------------
    # SQLite columns
    # --------------------------------------------------

    sqlite_columns = get_sqlite_columns(
        sq_cur,
        table
    )

    if not sqlite_columns:
        print(
            f"⚠ SQLite không có bảng {table}"
        )
        print(
            "   → Bỏ qua bảng này"
        )
        return

    # --------------------------------------------------
    # Compare columns
    # --------------------------------------------------

    pg_set = set(pg_columns)
    sqlite_set = set(sqlite_columns)

    common_columns = [
        col
        for col in pg_columns
        if col in sqlite_set
    ]

    pg_only = [
        col
        for col in pg_columns
        if col not in sqlite_set
    ]

    sqlite_only = [
        col
        for col in sqlite_columns
        if col not in pg_set
    ]

    print(
        f"   PostgreSQL columns : {len(pg_columns)}"
    )

    print(
        f"   SQLite columns     : {len(sqlite_columns)}"
    )

    print(
        f"   Common columns     : {len(common_columns)}"
    )

    if pg_only:
        print(
            "   ⚠ PG-only columns:"
        )

        for col in pg_only:
            print(f"      - {col}")

    if sqlite_only:
        print(
            "   ℹ SQLite-only columns:"
        )

        for col in sqlite_only:
            print(f"      - {col}")

    # --------------------------------------------------
    # Primary key
    # --------------------------------------------------

    sqlite_pks = get_sqlite_primary_keys(
        sq_cur,
        table
    )

    if sqlite_pks:
        print(
            f"   🔑 SQLite PK: {sqlite_pks}"
        )

    # --------------------------------------------------
    # IMPORTANT:
    #
    # Nếu SQLite có id nhưng PostgreSQL KHÔNG có id,
    # KHÔNG import id.
    #
    # SQLite/Django sẽ tự tạo id.
    # --------------------------------------------------

    if "id" in sqlite_columns and "id" not in pg_columns:

        print(
            "   ℹ PostgreSQL không có cột id"
        )

        print(
            "   ℹ SQLite có id → SQLite sẽ tự sinh ID"
        )

    # --------------------------------------------------
    # If SQLite has id and PG has id,
    # check duplicates.
    # --------------------------------------------------

    if "id" in sqlite_columns and "id" in pg_columns:
        check_duplicate_ids(
            pg_cur,
            table,
            "id"
        )

    # --------------------------------------------------
    # No common columns
    # --------------------------------------------------

    if not common_columns:
        print(
            "⚠ Không có cột chung → bỏ qua"
        )
        return

    # --------------------------------------------------
    # Clear existing SQLite data
    # --------------------------------------------------

    print("🧹 Clear SQLite table...")

    clear_sqlite_table(
        sq_cur,
        table
    )

    sq.commit()

    # --------------------------------------------------
    # SELECT only common columns
    # --------------------------------------------------

    select_columns = ",".join(
        f'"{c}"'
        for c in common_columns
    )

    pg_cur.execute(
        f'''
        SELECT {select_columns}
        FROM "{table}"
        '''
    )

    placeholders = ",".join(
        ["?"] * len(common_columns)
    )

    cols_sql = ",".join(
        f'"{c}"'
        for c in common_columns
    )

    insert_sql = (
        f'INSERT INTO "{table}" '
        f'({cols_sql}) '
        f'VALUES ({placeholders})'
    )

    # --------------------------------------------------
    # Import
    # --------------------------------------------------

    total = 0

    while True:

        rows = pg_cur.fetchmany(1000)

        if not rows:
            break

        converted_rows = []

        for row in rows:

            converted = tuple(
                convert_value(v)
                for v in row
            )

            converted_rows.append(
                converted
            )

        try:

            sq_cur.executemany(
                insert_sql,
                converted_rows
            )

            sq.commit()

        except sqlite3.IntegrityError as e:

            sq.rollback()

            print()
            print(
                "❌ SQLITE INTEGRITY ERROR"
            )
            print(
                f"   Table: {table}"
            )
            print(
                f"   Error: {e}"
            )

            print()
            print(
                "   SQL:"
            )
            print(
                f"   {insert_sql}"
            )

            print()
            print(
                "   First problematic batch:"
            )

            for row in converted_rows[:5]:
                print(
                    "   ",
                    row
                )

            raise

        total += len(converted_rows)

        print(
            f"   ↳ {total} rows",
            end="\r"
        )

    print()
    print(
        f"   ✅ Done {table}: {total} rows"
    )

    # --------------------------------------------------
    # Update AUTOINCREMENT
    # --------------------------------------------------

    if "id" in sqlite_columns:
        update_sqlite_sequence(
            sq_cur,
            table
        )

        sq.commit()


# ==================================================
# IMPORT PG → SQLITE
# ==================================================

def import_pg_to_sqlite():

    ssh_pass = getpass.getpass(
        "🔑 SSH password: "
    )

    pg_pass = getpass.getpass(
        "🔑 PostgreSQL password: "
    )

    print("\n" + "=" * 60)
    print("🔌 OPENING SSH TUNNEL")
    print("=" * 60)

    with SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_password=ssh_pass,
        remote_bind_address=("localhost", 5432),
        local_bind_address=("localhost", 6543),
    ):

        print("✅ SSH tunnel OK")

        # --------------------------------------------------
        # PostgreSQL
        # --------------------------------------------------

        pg = psycopg2.connect(
            host="localhost",
            port=6543,
            dbname=PG_DB,
            user=PG_USER,
            password=pg_pass
        )

        pg_cur = pg.cursor()

        # --------------------------------------------------
        # SQLite
        # --------------------------------------------------

        sq = sqlite3.connect(
            DB_FILE
        )

        sq_cur = sq.cursor()

        # --------------------------------------------------
        # Foreign keys OFF during bulk import
        # --------------------------------------------------

        sq_cur.execute(
            "PRAGMA foreign_keys = OFF"
        )

        # --------------------------------------------------
        # Get PostgreSQL tables
        # --------------------------------------------------

        pg_cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )

        tables = [
            row[0]
            for row in pg_cur.fetchall()
        ]

        print("\n📋 PostgreSQL TABLES:")

        for table in tables:
            print(
                f"   - {table}"
            )

        # --------------------------------------------------
        # Import
        # --------------------------------------------------

        for table in tables:

            if table in SKIP_TABLES:

                print(
                    f"\n⏭ Skip {table}"
                )

                continue

            if not postgres_table_exists(
                pg_cur,
                table
            ):
                continue

            import_one_table(
                pg_cur,
                sq_cur,
                sq,
                table
            )

        # --------------------------------------------------
        # Re-enable FK
        # --------------------------------------------------

        sq_cur.execute(
            "PRAGMA foreign_keys = ON"
        )

        # --------------------------------------------------
        # Check foreign keys
        # --------------------------------------------------

        print(
            "\n🔎 Checking SQLite foreign keys..."
        )

        sq_cur.execute(
            "PRAGMA foreign_key_check"
        )

        fk_errors = sq_cur.fetchall()

        if fk_errors:

            print(
                f"⚠ Có {len(fk_errors)} lỗi foreign key:"
            )

            for error in fk_errors[:20]:
                print(
                    "   ",
                    error
                )

        else:

            print(
                "✅ Foreign key check OK"
            )

        sq.commit()

        pg.close()
        sq.close()

    print("\n" + "=" * 60)
    print("🎉 IMPORT HOÀN TẤT")
    print("=" * 60)


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":

    try:

        if RESET_PROJECT:
            reset_project()

        if AUTO_MIGRATE:
            django_migrate()

        import_pg_to_sqlite()

        if AUTO_SUPERUSER:
            run(
                "python manage.py createsuperuser"
            )

        if AUTO_RUNSERVER:
            run(
                "python manage.py runserver"
            )

    except KeyboardInterrupt:

        print(
            "\n\n⛔ Đã hủy bởi người dùng."
        )

        sys.exit(1)

    except Exception as e:

        print("\n" + "=" * 60)
        print("❌ SCRIPT FAILED")
        print("=" * 60)

        print(
            f"{type(e).__name__}: {e}"
        )

        sys.exit(1)




# Kéo dữ liệu từ server về local
# python reset_khohang271db.py
# python manage.py createsuperuser
# $env:DEBUG="true"; python manage.py runserver 8001

# xBushN52hb1**8KC&GkF
# StrongPassword123