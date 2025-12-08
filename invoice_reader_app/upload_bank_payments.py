from datetime import datetime
from decimal import Decimal, InvalidOperation
import math
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Sum, FloatField, ExpressionWrapper
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



# Hàm tính số dư đầu kỳ
def get_opening_balance(start_date):
    """
    Số dư đầu kỳ:
    - Lấy balance lớn nhất trong ngày đầu kỳ
    - Trừ tổng credit + cộng tổng debit trong ngày đầu
    - Nếu không có ngày đầu, lấy số dư cuối cùng trước ngày đầu
    """
    payments_on_start = BankPayment.objects.filter(payment_date=start_date)
    if payments_on_start.exists():
        max_balance = payments_on_start.aggregate(Max('balance'))['balance__max'] or 0
        total_credit = payments_on_start.aggregate(Sum('credit'))['credit__sum'] or 0
        total_debit = payments_on_start.aggregate(Sum('debit'))['debit__sum'] or 0
        opening_balance = max_balance - total_credit + total_debit
        return opening_balance
    else:
        prev_payment = BankPayment.objects.filter(payment_date__lt=start_date).order_by('-payment_date').first()
        return prev_payment.balance if prev_payment else 0

PER_PAGE_OPTIONS = ["10", "20", "50", "all"]

def bank_payments_manage(request):
    # -----------------------
    # Nhập số dư đầu kỳ
    # -----------------------
    if request.method == 'POST' and 'opening_balance' in request.POST:
        ob_date_str = request.POST.get('opening_date')
        ob_amount = parse_decimal_excel(request.POST.get('opening_balance'))

        if ob_date_str:
            ob_date = datetime.strptime(ob_date_str, "%Y-%m-%d").date()
        else:
            ob_date = datetime.today().date()

        # Kiểm tra đã tồn tại số dư đầu kỳ chưa
        opening_record = BankPayment.objects.filter(content="Opening Balance").first()
        if opening_record:
            # Cập nhật nếu muốn thay đổi số dư đầu kỳ
            opening_record.balance = ob_amount
            opening_record.payment_date = ob_date
            opening_record.save()
            messages.success(request, f"Đã cập nhật số dư đầu kỳ: {ob_amount} ngày {ob_date}")
        else:
            # Tạo mới nếu chưa tồn tại
            BankPayment.objects.create(
                payment_date=ob_date,
                balance=ob_amount,
                debit=0,
                credit=0,
                content="Opening Balance",
                doc_no="OB"
            )
            messages.success(request, f"Đã tạo số dư đầu kỳ: {ob_amount} ngày {ob_date}")

        return redirect("bank_payments_manage")


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
        delete_ids = request.POST.getlist("delete_ids")
        if delete_ids:
            count = BankPayment.objects.filter(id__in=delete_ids).delete()[0]
            messages.success(request, f"Đã xóa {count} giao dịch.")

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
    payments_qs = BankPayment.objects.prefetch_related("purchase_orders").order_by("-payment_date", "-id")

    # Lọc tìm kiếm
    search = request.GET.get("search", "")
    if search:
        payments_qs = payments_qs.filter(
            Q(content__icontains=search) |
            Q(doc_no__icontains=search) |
            Q(purchase_orders__po_number__icontains=search)
        ).distinct()

    # Lọc theo ngày (nếu muốn)
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    else:
        first_payment = BankPayment.objects.order_by('payment_date').first()
        start_date = first_payment.payment_date if first_payment else datetime.today().date()

    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        payments_qs = payments_qs.filter(payment_date__range=[start_date, end_date])

    # -----------------------
    # Phân trang
    # -----------------------
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

    # Lấy số dư đầu kỳ nếu có, hoặc 0
    opening_record = BankPayment.objects.filter(content="Opening Balance").first()
    if opening_record:
        opening_balance = opening_record.balance
    else:
        opening_balance = Decimal(0)  # mặc định nếu chưa có


    total_debit = payments_qs.aggregate(sum=Sum("debit"))["sum"] or 0
    total_credit = payments_qs.aggregate(sum=Sum("credit"))["sum"] or 0
    closing_balance = opening_balance + total_credit - total_debit

    return render(request, "bank_payments_manage.html", {
        "payments": payments,
        "purchase_orders": purchase_orders,
        "paginator": paginator,
        "per_page": per_page,
        "search": search,
        "start_date": start_date,
        "end_date": end_date_str if end_date_str else "",
        "opening_balance": opening_balance,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "closing_balance": closing_balance,
        "per_page_options": PER_PAGE_OPTIONS,
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


from django.db.models import Max, Sum, Q
from datetime import datetime, timedelta
