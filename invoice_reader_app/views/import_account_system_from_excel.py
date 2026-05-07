import pandas as pd
from datetime import date

from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.http import JsonResponse
from invoice_reader_app.models_fiscalyear import FiscalYear
from invoice_reader_app.models.account import AccountSystem, AccountGroup, Account



# =========================
# PAGE
# =========================
def coa_page(request):
    return render(request, "account/upload_excel_account_system.html")

@csrf_exempt
def coa_delete(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        ids = data.get("ids", [])

        Account.objects.filter(id__in=ids).delete()

        return JsonResponse({"status": "ok"})
    

@csrf_exempt
def coa_delete_all(request):
    if request.method == "POST":
        Account.objects.all().delete()
        AccountGroup.objects.all().delete()
        AccountSystem.objects.all().delete()

        return JsonResponse({"status": "ok"})
    

# =========================
# VIEW IMPORT
# =========================
@csrf_exempt
def coa_import(request):
    if request.method == "POST":
        file = request.FILES.get("file")

        if not file:
            return render(request, "account/upload_excel_account_system.html", {
                "message": "Không có file upload"
            })

        try:
            # 🔥 RESET FULL TRƯỚC KHI IMPORT
            import_coa_excel(file, reset=True)

            return redirect("coa_result")

        except Exception as e:
            return render(request, "account/upload_excel_account_system.html", {
                "message": f"Lỗi import: {str(e)}"
            })

    return render(request, "account/upload_excel_account_system.html")


# =========================
# RESULT
# =========================
def coa_result(request):
    accounts = Account.objects.select_related(
        "system", "parent", "group"
    ).order_by("system__code", "code")

    return render(request, "account/coa_result.html", {
        "accounts": accounts,
        "message": "Import COA thành công"
    })

import pandas as pd
from datetime import date
from django.db import transaction

from invoice_reader_app.models_fiscalyear import FiscalYear
from invoice_reader_app.models.account import AccountSystem, AccountGroup, Account


def clear_all_coa():
    """
    Xóa toàn bộ COA trước khi import mới
    """
    Account.objects.all().delete()
    AccountGroup.objects.all().delete()
    AccountSystem.objects.all().delete()



# =========================
# UTIL MAP TYPE
# =========================
def resolve_account_type(group_code, text):
    if group_code:
        gc = str(group_code).strip()
        if gc in GROUP_TYPE_MAP:
            return GROUP_TYPE_MAP[gc]

    if text:
        t = str(text).strip().lower()
        return TEXT_TYPE_MAP.get(t, "expense")

    return "expense"


# =========================
# FIND PARENT (SAFE ERP)
# =========================
def find_parent(system, code):
    if not code:
        return None

    for i in range(len(code) - 1, 0, -1):
        parent_code = code[:i]

        parent = Account.objects.filter(
            system=system,
            code=parent_code
        ).first()

        if parent:
            return parent

    return None

# =========================
# CLEAN + NORMALIZE
# =========================
def clean(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


def normalize_code(v):
    """
    Fix lỗi Excel:
    811.0 -> 811
    """
    v = clean(v)
    if not v:
        return ""



    return v


# =========================
# TYPE MAP
# =========================
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
    "chi phí khác": "other_expense",
    "chi phí thuế tndn": "tax_expense",
    "xác định kết quả kinh doanh": "profit_loss",
}


def resolve_account_type(group_code, text):
    if group_code:
        gc = str(group_code).strip()
        if gc in GROUP_TYPE_MAP:
            return GROUP_TYPE_MAP[gc]

    if text:
        t = str(text).strip().lower()
        return TEXT_TYPE_MAP.get(t, "expense")

    return "expense"


# =========================
# IMPORT CORE
# =========================
def import_coa_excel(file, reset=True):
    df = pd.read_excel(file, dtype=str)
    df.columns = df.columns.str.strip()

    fiscal_year = FiscalYear.objects.get_or_create(year=2026)[0]

    system_cache = {}
    account_cache = {}

    with transaction.atomic():

        # =========================
        # RESET DATA
        # =========================
        if reset:
            Account.objects.all().delete()
            AccountGroup.objects.all().delete()
            AccountSystem.objects.all().delete()

        for _, row in df.iterrows():

            # =========================
            # READ EXCEL
            # =========================
            system_code = normalize_code(row.get("system_code"))
            if not system_code:
                continue

            cap1 = normalize_code(row.get("account_code"))
            cap2 = normalize_code(row.get("account_code 2"))

            name = clean(row.get("account_name"))
            group_code = clean(row.get("group_code"))
            acc_type_raw = row.get("account_type")

            if not cap1:
                continue

            # =========================
            # SYSTEM
            # =========================
            if system_code not in system_cache:
                system, _ = AccountSystem.objects.get_or_create(
                    code=system_code,
                    defaults={
                        "name": row.get("system_name"),
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
                code=group_code,
                defaults={"name": f"Group {group_code}"}
            )

            # =========================
            # TYPE
            # =========================
            acc_type_db = resolve_account_type(group_code, acc_type_raw)

            # =========================
            # CAP1 (PARENT)
            # =========================
            cap1_key = (system.id, cap1)

            if cap1_key not in account_cache:
                cap1_acc, _ = Account.objects.update_or_create(
                    system=system,
                    code=cap1,
                    defaults={
                        "name": name,
                        "group": group,
                        "account_type": acc_type_db,
                        "parent": None
                    }
                )
                account_cache[cap1_key] = cap1_acc
            else:
                cap1_acc = account_cache[cap1_key]

            # =========================
            # CAP2 (CHILD)
            # =========================
            if cap2:
                cap2_key = (system.id, cap2)

                if cap2_key not in account_cache:
                    cap2_acc, _ = Account.objects.update_or_create(
                        system=system,
                        code=cap2,
                        defaults={
                            "name": name,
                            "group": group,
                            "account_type": acc_type_db,
                            "parent": cap1_acc
                        }
                    )
                    account_cache[cap2_key] = cap2_acc
                else:
                    cap2_acc = account_cache[cap2_key]
                    cap2_acc.parent = cap1_acc
                    cap2_acc.save()

def import_coa_excel(file, reset=True):
    df = pd.read_excel(file, dtype=str)
    df.columns = df.columns.str.strip()

    fiscal_year = FiscalYear.objects.get_or_create(year=2026)[0]

    system_cache = {}
    account_cache = {}

    with transaction.atomic():

        if reset:
            Account.objects.all().delete()
            AccountGroup.objects.all().delete()
            AccountSystem.objects.all().delete()

        for _, row in df.iterrows():

            system_code = normalize_code(row.get("system_code"))
            cap1 = normalize_code(row.get("account_code"))
            cap2 = normalize_code(row.get("account_code 2"))

            name = clean(row.get("account_name"))
            group_code = clean(row.get("group_code"))

            if not system_code or not cap1:
                continue

            # =========================
            # SYSTEM
            # =========================
            if system_code not in system_cache:
                system, _ = AccountSystem.objects.get_or_create(
                    code=system_code,
                    defaults={
                        "name": row.get("system_name"),
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
                code=group_code,
                defaults={"name": f"Group {group_code}"}
            )

            # =========================
            # TYPE
            # =========================
            acc_type_db = resolve_account_type(group_code, row.get("account_type"))

            # =========================
            # CAP1 (LUÔN TẠO + LUÔN UPDATE)
            # =========================
            cap1_key = (system.id, cap1)

            if cap1_key not in account_cache:
                cap1_acc, _ = Account.objects.get_or_create(
                    system=system,
                    code=cap1,
                    defaults={
                        "name": name or cap1,
                        "group": group,
                        "account_type": acc_type_db,
                        "parent": None
                    }
                )
                account_cache[cap1_key] = cap1_acc
            else:
                cap1_acc = account_cache[cap1_key]

            # 🔥 FIX QUAN TRỌNG: LUÔN UPDATE CAP1
            is_real_cap1 = (not cap2) or (cap2 == cap1)

            if is_real_cap1:
                updated = False

                if name and cap1_acc.name != name:
                    cap1_acc.name = name
                    updated = True

                if cap1_acc.group_id != group.id:
                    cap1_acc.group = group
                    updated = True

                if cap1_acc.account_type != acc_type_db:
                    cap1_acc.account_type = acc_type_db
                    updated = True

                if cap1_acc.parent is not None:
                    cap1_acc.parent = None
                    updated = True

                if updated:
                    cap1_acc.save()

            # =========================
            # CAP2 (NẾU KHÁC CAP1)
            # =========================
            if cap2 and cap2 != cap1:

                cap2_key = (system.id, cap2)

                if cap2_key not in account_cache:
                    cap2_acc = Account.objects.create(
                        system=system,
                        code=cap2,
                        name=name,
                        group=group,
                        account_type=acc_type_db,
                        parent=cap1_acc
                    )
                    account_cache[cap2_key] = cap2_acc
                else:
                    cap2_acc = account_cache[cap2_key]

                    updated = False

                    if cap2_acc.name != name:
                        cap2_acc.name = name
                        updated = True

                    if cap2_acc.group_id != group.id:
                        cap2_acc.group = group
                        updated = True

                    if cap2_acc.account_type != acc_type_db:
                        cap2_acc.account_type = acc_type_db
                        updated = True

                    if cap2_acc.parent_id != cap1_acc.id:
                        cap2_acc.parent = cap1_acc
                        updated = True

                    if updated:
                        cap2_acc.save()


def import_coa_excel(file, reset=True):
    import pandas as pd
    from datetime import date
    from django.db import transaction

    df = pd.read_excel(file, dtype=str)
    df.columns = df.columns.str.strip()

    fiscal_year = FiscalYear.objects.get_or_create(year=2026)[0]

    # =========================
    # CLEAN
    # =========================
    def clean(v):
        if pd.isna(v):
            return ""
        return str(v).strip()

    def normalize_code(v):
        if pd.isna(v):
            return ""

        v = str(v).strip()

        # remove .0
        if v.endswith(".0"):
            v = v[:-2]

        # remove space giữa (rất hay gặp)
        v = v.replace(" ", "")

        return v
    def ensure_parent_exists(system, code, cache):
        for i in range(1, len(code)):
            parent_code = code[:i]
            key = (system.id, parent_code)

            if key not in cache:
                parent = Account.objects.create(
                    system=system,
                    code=parent_code,
                    name=parent_code,
                    parent=None
                )
                cache[key] = parent
        # =========================
    # FIND PARENT
    # =========================
    def find_parent(system, code, cache):
        code = str(code).strip()

        candidates = []

        for (sys_id, c), acc in cache.items():
            if sys_id != system.id:
                continue

            c = str(c).strip()

            # 🔥 parent phải là prefix NGẮN HƠN
            if code.startswith(c) and code != c:
                candidates.append((len(c), acc))

        if not candidates:
            return None

        # 🔥 lấy prefix DÀI NHẤT (cha gần nhất)
        candidates.sort(key=lambda x: x[0], reverse=True)

        return candidates[0][1]

    system_cache = {}
    account_cache = {}

    with transaction.atomic():

        # =========================
        # RESET
        # =========================
        if reset:
            Account.objects.all().delete()
            AccountGroup.objects.all().delete()
            AccountSystem.objects.all().delete()

        # =========================
        # PASS 1: TẠO ACCOUNT (KHÔNG PARENT)
        # =========================
        for _, row in df.iterrows():

            system_code = normalize_code(row.get("system_code"))
            code = normalize_code(row.get("account_code"))

            name = clean(row.get("account_name"))
            group_code = clean(row.get("group_code"))

            if not system_code or not code:
                continue

            # SYSTEM
            if system_code not in system_cache:
                system, _ = AccountSystem.objects.get_or_create(
                    code=system_code,
                    defaults={
                        "name": row.get("system_name"),
                        "effective_from": date(2026, 1, 1),
                        "fiscal_year": fiscal_year,
                    }
                )
                system_cache[system_code] = system

            system = system_cache[system_code]

            # GROUP
            group, _ = AccountGroup.objects.get_or_create(
                system=system,
                code=group_code,
                defaults={"name": f"Group {group_code}"}
            )

            # TYPE
            acc_type_db = resolve_account_type(group_code, row.get("account_type"))

            key = (system.id, code)

            acc, _ = Account.objects.get_or_create(
                system=system,
                code=code,
                defaults={
                    "name": name or code,
                    "group": group,
                    "account_type": acc_type_db,
                    "parent": None
                }
            )

            # update nếu đã tồn tại
            updated = False

            if name and acc.name != name:
                acc.name = name
                updated = True

            if acc.group_id != group.id:
                acc.group = group
                updated = True

            if acc.account_type != acc_type_db:
                acc.account_type = acc_type_db
                updated = True

            if updated:
                acc.save()

            account_cache[key] = acc

        # =========================
        # PASS 2: BUILD TREE (SET PARENT)
        # =========================
        for key, acc in account_cache.items():
            system_id, code = key

            system = acc.system

            ensure_parent_exists(system, code, account_cache)
            parent = find_parent(system, code, account_cache)

            if parent and parent.id != acc.id:
                if acc.parent_id != parent.id:
                    acc.parent = parent
                    acc.save()

        # =========================
        # DONE
        # =========================
        print("✅ Import COA DONE (2-pass)")
        print(f"{acc.code} -> parent: {parent.code if parent else None}")




