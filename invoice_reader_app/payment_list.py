from datetime import datetime
from decimal import Decimal, InvalidOperation
import math
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Sum, FloatField, ExpressionWrapper
from .models_purchaseorder import BankPayment, PurchaseOrder, CashReceipt
from django.db.models import Q




from django.shortcuts import render

from collections import OrderedDict

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
    search = request.GET.get("search", "").strip()
   

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

        bank_ids = []
        cash_ids = []

        for item in delete_ids:
            kind, obj_id = item.split("_")

            if kind == "bank":
                bank_ids.append(obj_id)

            elif kind == "cash":
                cash_ids.append(obj_id)

        count_bank = BankPayment.objects.filter(
            id__in=bank_ids
        ).delete()[0]

        count_cash = CashReceipt.objects.filter(
            id__in=cash_ids
        ).delete()[0]

        messages.success(
            request,
            f"Đã xóa {count_bank + count_cash} phiếu "
            f"(NH: {count_bank}, TM: {count_cash})"
        )

        return redirect("payment_list")

    # ------------------------
    # Lấy tất cả phiếu thu tổng hợp mới tạo: credit > 0, doc_no bắt đầu NH
    # ------------------------
    payments_qs = (
        BankPayment.objects
        .filter(
            credit__gt=0,
            doc_no__startswith="NH",
            is_summary=True
        )
    )


    if search:
        payments_qs = payments_qs.filter(
            Q(doc_no__icontains=search) |
            Q(content__icontains=search)
        )


    if current_year:
        payments_qs = payments_qs.filter(
            payment_date__year=current_year
        )


    payments_qs = payments_qs.order_by("-doc_no")
    cash_receipts = (
        CashReceipt.objects
        .filter(created_at__year=current_year)
        .select_related("invoice")
        .order_by("-created_at")
    )


    if search:
        cash_receipts = cash_receipts.filter(
            Q(receipt_no__icontains=search) |
            Q(invoice__so_hoa_don__icontains=search)
        )
    # ------------------------
    # Gom các phiếu trùng nội dung (PO giống nhau)
    # ------------------------
    grouped = OrderedDict()
    for p in payments_qs:
        key = (p.content, p.doc_no)
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
                "type": "bank",
                "doc_no": row["doc_no"],
                "payment_date": row["payment_date"],
                "content": key[0] if first_row else '',
                "amount": data["total_amount"] if first_row else 0,
                "credit": row["credit"],
                "remaining": max(
                    remaining - row["credit"],
                    row["credit"] - remaining
                ),
                "payment_type": "bank",
            })
            remaining -= row["credit"]
            first_row = False
    for c in cash_receipts:
        final_payments.append({
            "id": c.id,
            "type": "cash",
            "doc_no": getattr(c, "receipt_no", f"TM-{c.id:05d}"),
            "payment_date": c.created_at.date(),
            "content": (
                f"Thu tiền mặt HĐ {c.invoice.so_hoa_don}"
                if c.invoice else
                "Thu tiền mặt"
            ),
            "amount": c.amount,
            "credit": c.amount,
            "remaining": Decimal("0"),
            "payment_type": "cash",
        })

    final_payments.sort(
        key=lambda x: (
            x["payment_date"] or datetime.min.date(),
            str(x["doc_no"])
        ),
        reverse=True,
    )
    # ------------------------
    # Tính tổng cộng
    # ------------------------
    total_amount = sum(p['amount'] for p in final_payments)
    total_credit = sum(p['credit'] for p in final_payments)


    # ------------------------
    # PHÂN TRANG
    # ------------------------
    #print("SEARCH =", search)
    #print("PAYMENTS QS =", payments_qs.count())
    #print("FINAL =", len(final_payments))

    #for x in final_payments:
    #    print(x["doc_no"], x["content"])
    paginator = Paginator(final_payments, 15)  # 30 dòng/trang

    page = request.GET.get("page")

    try:
        payments = paginator.page(page)
    except PageNotAnInteger:
        payments = paginator.page(1)
    except EmptyPage:
        payments = paginator.page(paginator.num_pages)

    return render(request, "payment_list.html", {
        "payments": payments,
        "total_amount": total_amount,
        "total_credit": total_credit,
        "current_year": current_year,
        "year_list": year_list,
        "search": search,
    })


from django.http import HttpResponse

def payment_detail(request, pk):

    payment = get_object_or_404(
        BankPayment,
        pk=pk
    )


    summaries = BankPayment.objects.filter(
        parent_payment=payment,
        is_summary=True
    ).select_related(
        "customer"
    ).prefetch_related(
        "purchase_orders"
    )


    purchase_orders = PurchaseOrder.objects.filter(
        bank_payments__parent_payment=payment,
        bank_payments__is_summary=True
    ).distinct()


    return render(
        request,
        "payment_detail.html",
        {
            "payment": payment,
            "summaries": summaries,
            "purchase_orders": purchase_orders,
        }
    )