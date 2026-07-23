import pandas as pd
from datetime import date
from django.db import transaction

import io
from invoice_reader_app.models_fiscalyear import FiscalYear
from invoice_reader_app.models.account import AccountSystem, AccountGroup, Account


# =========================================================
# CLEAN DATA
# =========================================================
def clean(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


def normalize_code(v):
    if pd.isna(v):
        return ""

    v = str(v).strip()
    v = v.replace(" ", "")

    if v.endswith(".0"):
        v = v[:-2]

    return v


# =========================================================
# ACCOUNT TYPE MAP
# =========================================================
GROUP_TYPE_MAP = {
    "1": "asset",
    "2": "asset",
    "3": "liability",
    "4": "equity",
    "5": "revenue",
    "6": "expense",
    "7": "other_income",
    "81": "other_expense",
    "8": "tax_expense",
    "9": "profit_loss",
}

TEXT_TYPE_MAP = {
    "tài sản": "asset",
    "nợ phải trả": "liability",
    "vốn chủ sở hữu": "equity",
    "doanh thu": "revenue",
    "thu nhập khác": "other_income",
    "chi phí": "expense",
}


def resolve_account_type(group_code, text):
    if group_code and group_code in GROUP_TYPE_MAP:
        return GROUP_TYPE_MAP[group_code]

    if text:
        return TEXT_TYPE_MAP.get(str(text).strip().lower(), "expense")

    return "expense"


# =========================================================
# FIND PARENT (LONGEST PREFIX MATCH)
# =========================================================
def find_parent(system, code, cache):
    candidates = []

    for (sys_id, c), acc in cache.items():
        if sys_id != system.id:
            continue

        if c != code and code.startswith(c):
            candidates.append((len(c), acc))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]

from django.http import HttpResponseBadRequest

def import_coa_excel(file, reset=True):
    import io
    import pandas as pd
    from datetime import date
    from django.db import transaction

    # =========================
    # SAFE READ EXCEL
    # =========================
    file.seek(0)
    file_bytes = io.BytesIO(file.read())

    df = pd.read_excel(file_bytes, engine="openpyxl", dtype=str)
    df.columns = df.columns.str.strip()

    fiscal_year = FiscalYear.objects.get_or_create(year=2026)[0]

    system_cache = {}
    account_cache = {}

    # =========================
    # CLEAN HELPERS
    # =========================
    def clean(v):
        if pd.isna(v):
            return ""
        return str(v).strip()

    def norm(v):
        if pd.isna(v):
            return ""
        v = str(v).strip().replace(" ", "")
        if v.endswith(".0"):
            v = v[:-2]
        return v

    # =========================
    with transaction.atomic():

        if reset:
            Account.objects.all().delete()
            AccountGroup.objects.all().delete()
            AccountSystem.objects.all().delete()

        # =========================
        # PASS 1: CREATE SYSTEM + ACCOUNT
        # =========================
        for _, row in df.iterrows():

            system_code = norm(row.get("system_code"))
            system_name = clean(row.get("system_name"))

            code = norm(row.get("account_code"))
            name = clean(row.get("account_name"))
            group_code = clean(row.get("group_code"))

            if not system_code or not code:
                continue

            # =========================
            # SYSTEM
            # =========================
            if system_code not in system_cache:
                system, _ = AccountSystem.objects.get_or_create(
                    code=system_code,
                    defaults={
                        "name": system_name or system_code,
                        "effective_from": date(2026, 1, 1),
                        "fiscal_year": fiscal_year,
                    }
                )
                system_cache[system_code] = system

            system = system_cache[system_code]

            # =========================
            # GROUP
            # =========================
            group, _ = AccountGroup.objects.get_or_create(
                system=system,
                code=group_code or "DEFAULT",
                defaults={"name": f"Group {group_code}"}
            )

            # =========================
            # ACCOUNT
            # =========================
            key = (system.id, code)

            acc, created = Account.objects.get_or_create(
                system=system,
                code=code,
                defaults={
                    "name": name or code,
                    "group": group,
                    "parent": None
                }
            )

            # update nếu đã tồn tại
            if not created:
                updated = False

                if name and acc.name != name:
                    acc.name = name
                    updated = True

                if acc.group_id != group.id:
                    acc.group = group
                    updated = True

                if updated:
                    acc.save()

            account_cache[key] = acc

        # =========================
        # PASS 2: BUILD TREE (AUTO PARENT BY PREFIX)
        # =========================
        def find_parent(system, code):
            for i in range(len(code) - 1, 0, -1):
                parent_code = code[:i]
                parent = account_cache.get((system.id, parent_code))
                if parent:
                    return parent
            return None

        for (system_id, code), acc in account_cache.items():

            system = acc.system
            parent = find_parent(system, code)

            if parent and parent.id != acc.id:
                if acc.parent_id != parent.id:
                    acc.parent = parent
                    acc.save()

    print("✅ DONE IMPORT COA 2026")