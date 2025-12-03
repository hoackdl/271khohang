from datetime import datetime
from decimal import Decimal, InvalidOperation
import math
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from .models_purcharoder import BankPayment, PurchaseOrder


# ---------------------------
# PARSE HỖ TRỢ
# ---------------------------
def parse_decimal_excel(value):
    if value is None:
        return Decimal('0')
    if isinstance(value, float) and math.isnan(value):
        return Decimal('0')
    if isinstance(value, (int, Decimal)):
        return Decimal(value)
    if isinstance(value, str):
        value = value.replace(',', '').replace(' ', '')
        try:
            return Decimal(value)
        except InvalidOperation:
            return Decimal('0')
    return Decimal('0')


def parse_date_excel(value):
    if pd.isna(value) or value in [None, ""]:
        return None
    if hasattr(value, "date"):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None

from django.db.models import Q

def bank_payments_manage(request):
    # -----------------------
    # UPLOAD EXCEL
    # -----------------------
    if request.method == 'POST' and 'excel_file' in request.FILES:
        file = request.FILES['excel_file']
        try:
            df = pd.read_excel(file, engine="openpyxl")
        except Exception as e:
            messages.error(request, f"Lỗi đọc file Excel: {e}")
            return redirect("bank_payments_manage")

        df.rename(columns={
            'Ngày hiệu lực2/\nEffective date': 'payment_date',
            'Số tiền ghi có/\nCredit': 'credit',
            'Số tiền ghi nợ/\nDebit': 'debit',
            'Số dư/\nBalance': 'balance',
            'Nội dung chi tiết/\nTransactions in detail': 'content',
            'Ngày1/\nTNX Date/ Số CT/ Doc No': 'doc_no',
            'STT\nNo.': 'stt'
        }, inplace=True)

        added_count = 0
        for _, row in df.iterrows():
            content = str(row.get("content", ""))
            credit = parse_decimal_excel(row.get("credit"))
            debit = parse_decimal_excel(row.get("debit"))
            balance = parse_decimal_excel(row.get("balance"))
            payment_date = parse_date_excel(row.get("payment_date"))
            doc_no = str(row.get("doc_no", ""))

            exists = BankPayment.objects.filter(
                doc_no=doc_no,
                payment_date=payment_date,
                credit=credit,
                debit=debit
            ).exists()
            if exists:
                continue

            BankPayment.objects.create(
                credit=credit,
                debit=debit,
                balance=balance,
                payment_date=payment_date,
                content=content,
                doc_no=doc_no,
                stt=row.get("stt")
            )
            added_count += 1

        messages.success(request, f"Đã import {added_count} giao dịch!")
        return redirect("bank_payments_manage")

    # -----------------------
    # XÓA + CẬP NHẬT PO
    # -----------------------
    if request.method == 'POST' and 'update_delete' in request.POST:
        # XÓA nhiều
        delete_ids = request.POST.getlist("delete_ids")
        if delete_ids:
            count = BankPayment.objects.filter(id__in=delete_ids).delete()[0]
            messages.success(request, f"Đã xóa {count} giao dịch.")

        # CẬP NHẬT PO (many to many)
        for key in request.POST:
            if key.startswith("po_ids_"):
                bank_id = key.replace("po_ids_", "")
                po_ids = request.POST.getlist(key)
                try:
                    payment = BankPayment.objects.get(id=bank_id)
                    payment.purchase_orders.set(po_ids)
                except BankPayment.DoesNotExist:
                    continue

        return redirect("bank_payments_manage")

    # -----------------------
    # TÌM KIẾM + PHÂN TRANG
    # -----------------------
    payments_qs = BankPayment.objects.prefetch_related("purchase_orders").order_by("-payment_date")

    # Lọc tìm kiếm
    search = request.GET.get("search", "")
    payments_qs = BankPayment.objects.prefetch_related("purchase_orders").order_by("-payment_date")

    if search:
        payments_qs = payments_qs.filter(
            Q(content__icontains=search) |
            Q(doc_no__icontains=search) |
            Q(purchase_orders__po_number__icontains=search)
        ).distinct()

    # Phân trang
    page = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 20)

    if per_page == "all":
        payments = payments_qs
        paginator = None
    else:
        paginator = Paginator(payments_qs, per_page)
        try:
            payments = paginator.page(page)
        except PageNotAnInteger:
            payments = paginator.page(1)
        except EmptyPage:
            payments = paginator.page(paginator.num_pages)

    purchase_orders = PurchaseOrder.objects.all()

    return render(request, "bank_payments_manage.html", {
        "payments": payments,
        "purchase_orders": purchase_orders,
        "paginator": paginator,
        "per_page": per_page,
        "search": search,
    })


# ---------------------------
# FORM CHI TIẾT
# ---------------------------
def bank_payment_detail(request, pk):

    payment = get_object_or_404(BankPayment, pk=pk)
    purchase_orders = PurchaseOrder.objects.all()

    if request.method == "POST":

        # ManyToMany
        po_ids = request.POST.getlist("po_id")
        payment.purchase_orders.set(po_ids)

        # credit / debit
        try:
            payment.debit = Decimal(request.POST.get("debit", "0").replace(",", ""))
        except:
            payment.debit = Decimal("0")

        try:
            payment.credit = Decimal(request.POST.get("credit", "0").replace(",", ""))
        except:
            payment.credit = Decimal("0")

        payment.content = request.POST.get("content", payment.content)

        payment.save()
        messages.success(request, "Cập nhật thành công!")
        return redirect("bank_payments_manage")

    return render(request, "bank_payment_detail.html", {
        "payment": payment,
        "purchase_orders": purchase_orders
    })
