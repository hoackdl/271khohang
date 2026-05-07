import pandas as pd
from django.http import JsonResponse



from invoice_reader_app.models.account import AccountSystem, AccountGroup, Account


def import_account_system_from_excel(file_path):
    df = pd.read_excel(file_path)

    system_cache = {}
    group_cache = {}

    for _, row in df.iterrows():

        # 1. AccountSystem
        system_key = row["system_code"]

        if system_key not in system_cache:
            system, _ = AccountSystem.objects.get_or_create(
                code=system_key,
                defaults={
                    "name": row["system_name"],
                    "effective_from": "2026-01-01"
                }
            )
            system_cache[system_key] = system
        else:
            system = system_cache[system_key]

        # 2. AccountGroup
        group_key = (system.id, row["group_code"])

        if group_key not in group_cache:
            group, _ = AccountGroup.objects.get_or_create(
                system=system,
                code=row["group_code"],
                defaults={"name": row["group_name"]}
            )
            group_cache[group_key] = group
        else:
            group = group_cache[group_key]

        # 3. Account
        Account.objects.get_or_create(
            system=system,
            code=row["account_code"],
            defaults={
                "name": row["account_name"],
                "group": group,
                "account_type": row["account_type"]
            }
        )



def normalize_columns(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )
    return df



import pandas as pd
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt

from django.shortcuts import render
from django.http import JsonResponse


def coa_page(request):
    return render(request, "account/upload_excel_account_system.html")




import pandas as pd
from django.db import transaction
from django.http import JsonResponse

def import_coa_excel(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()

    system_cache = {}
    result = []

    with transaction.atomic():
        for _, row in df.iterrows():

            system_code = str(row.get("system_code")).strip()
            cap1 = str(row.get("CẤP 1") or "").strip()
            cap2 = str(row.get("CẤP 2") or "").strip()
            cap3 = str(row.get("CẤP 3") or "").strip()
            cap4 = str(row.get("CẤP 4") or "").strip()

            name = str(row.get("TÊN TÀI KHOẢN") or "").strip()
            acc_type = str(row.get("LOẠI TÀI KHOẢN") or "").strip()

            if system_code not in system_cache:
                system, _ = AccountSystem.objects.get_or_create(
                    code=system_code,
                    defaults={"name": system_code}
                )
                system_cache[system_code] = system

            system = system_cache[system_code]

            code = "".join([c for c in [cap1, cap2, cap3, cap4] if c])

            if not code:
                continue

            if "tài sản" in acc_type.lower():
                acc_type_db = "asset"
            elif "nợ" in acc_type.lower():
                acc_type_db = "liability"
            elif "vốn" in acc_type.lower():
                acc_type_db = "equity"
            elif "doanh thu" in acc_type.lower():
                acc_type_db = "revenue"
            else:
                acc_type_db = "expense"

            acc, _ = Account.objects.update_or_create(
                system=system,
                code=code,
                defaults={
                    "name": name,
                    "account_type": acc_type_db,
                }
            )

            result.append({
                "system": system.code,
                "code": acc.code,
                "name": acc.name,
                "type": acc.account_type
            })

    return result

from django.shortcuts import render
from django.http import JsonResponse

from django.shortcuts import redirect
from django.urls import reverse

@csrf_exempt
def coa_import(request):
    if request.method == "POST":
        file = request.FILES.get("file")

        if not file:
            return JsonResponse({"status": "error", "message": "No file"})

        try:
            import_coa_excel(file)

            return redirect("coa_result")

        except Exception as e:
            return render(request, "account/upload_excel_account_system.html", {
                "message": f"Lỗi import: {str(e)}"
            })

    return render(request, "account/upload_excel_account_system.html")



def coa_result(request):

    accounts = Account.objects.select_related("system").all().order_by("system__code", "code")

    return render(request, "account/coa_result.html", {
        "accounts": accounts,
        "message": "Import COA thành công"
    })