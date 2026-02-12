from datetime import datetime
from decimal import Decimal, InvalidOperation
import math
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Sum, FloatField, ExpressionWrapper
from .models_purcharoder import BankPayment, PurchaseOrder

from django.shortcuts import render, get_object_or_404
from .models_purcharoder import BankPayment
from django.utils import timezone
from .models_purcharoder import BankPayment
from django.db.models import Q
from django.shortcuts import render
from .models_purcharoder import BankPayment


from django.shortcuts import render
from .models_purcharoder import BankPayment
from collections import OrderedDict
from collections import OrderedDict
from django.shortcuts import render
from .models_purcharoder import BankPayment
from collections import OrderedDict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models_purcharoder import BankPayment
from django.db.models.functions import ExtractYear

def payment_list(request):
        # ---- NĂM TÀI CHÍNH ----
    selected_year = request.GET.get("year")
    if selected_year:
        try:
            request.session["fiscal_year"] = int(selected_year)
        except ValueError:
            pass

    current_year = request.session.get("fiscal_year", datetime.now().year)
   

    years_qs = (
        BankPayment.objects
        .filter(credit__gt=0, doc_no__startswith='NH')
        .exclude(payment_date__isnull=True)
        .annotate(y=ExtractYear("payment_date"))
        .values_list("y", flat=True)
        .distinct()
    )

    year_list = sorted(set(years_qs) | {current_year})

    # ------------------------
    # XÓA PHIẾU (nếu có yêu cầu)
    # ------------------------
    if request.method == "POST" and "delete_ids" in request.POST:
        delete_ids = request.POST.getlist("delete_ids")
        if delete_ids:
            count = BankPayment.objects.filter(id__in=delete_ids).delete()[0]
            messages.success(request, f"Đã xóa {count} phiếu thu.")
        return redirect("payment_list")

    # ------------------------
    # Lấy tất cả phiếu thu tổng hợp mới tạo: credit > 0, doc_no bắt đầu NH
    # ------------------------
    payments_qs = BankPayment.objects.filter(
        credit__gt=0,
        doc_no__startswith='NH',
        payment_date__year=current_year
    ).order_by('-doc_no')  # giảm dần theo số phiếu

    # ------------------------
    # Gom các phiếu trùng nội dung (PO giống nhau)
    # ------------------------
    grouped = OrderedDict()
    for p in payments_qs:
        key = p.content
        if key not in grouped:
            grouped[key] = {
                "total_amount": p.amount,
                "rows": []
            }
        grouped[key]["rows"].append({
            "id": p.id,
            "doc_no": p.doc_no,
            "payment_date": p.payment_date,
            "credit": p.credit,
        })

    # ------------------------
    # Tạo danh sách cuối cùng với remaining
    # ------------------------
    final_payments = []
    for key, data in grouped.items():
        remaining = data["total_amount"]
        first_row = True
        for row in data["rows"]:
            final_payments.append({
                "id": row["id"],
                "doc_no": row["doc_no"],
                "payment_date": row["payment_date"],
                "content": key if first_row else '',  # chỉ hiển thị 1 lần
                "amount": data["total_amount"] if first_row else 0,  # tổng thu chỉ 1 lần
                "credit": row["credit"],
                "remaining": max(remaining - row["credit"],row["credit"]-remaining )
            })
            remaining -= row["credit"]
            first_row = False

    # ------------------------
    # Tính tổng cộng
    # ------------------------
    total_amount = sum(p['amount'] for p in final_payments)
    total_credit = sum(p['credit'] for p in final_payments)

    return render(request, "payment_list.html", {
        "payments": final_payments,
        "total_amount": total_amount,
        "total_credit": total_credit,
        "current_year": current_year,
        "year_list": year_list,
    })

