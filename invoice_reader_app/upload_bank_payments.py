from datetime import datetime
from decimal import Decimal, InvalidOperation
import math
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Sum, FloatField, ExpressionWrapper
from .models_purchaseorder import BankPayment, PurchaseOrder
from invoice_reader_app.model_invoice import Customer, InvoiceItem
from django.utils import timezone

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

def get_existing_summary(payment_date, content, po_ids=None):
    qs = BankPayment.objects.filter(
        is_summary=True,
        payment_date=payment_date,
        content=content
    )
    if po_ids:
        qs = qs.filter(purchase_orders__id__in=po_ids)
    return qs.first()


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


import re
from django.http import JsonResponse
from django.db.models import Q
from .models_purchaseorder import PurchaseOrder
import re
from django.http import JsonResponse
from django.db.models import Q
from .models_purchaseorder import PurchaseOrder


def normalize_invoice_no(val):
    return re.sub(r'^0+', '', val or '')


def find_po_by_mst_invoice(request):
    mst = request.GET.get("mst", "").strip()
    sohd_raw = request.GET.get("sohd", "").strip()

    if not mst:
        return JsonResponse({"found": False, "pos": []})

    sohd_list = [
        normalize_invoice_no(x.strip())
        for x in sohd_raw.split(",")
        if x.strip()
    ]

    qs = PurchaseOrder.objects.all()

    # 🔹 DEBIT (PO nhập)
    debit_q = Q(invoice__ma_so_thue=mst)

    # 🔹 CREDIT (PO xuất)
    credit_q = Q(customer__ma_so_thue=mst)

    qs = qs.filter(debit_q | credit_q)

    # 🔹 Filter số hóa đơn (cả debit + credit)
    if sohd_list:
        q_sohd = Q()
        for sohd in sohd_list:
            q_sohd |= (
                Q(invoice__so_hoa_don__endswith=sohd) |
                Q(customer__so_hoa_don__endswith=sohd)
            )
        qs = qs.filter(q_sohd)

    qs = (
        qs.select_related("customer", "invoice")
        .order_by("-invoice__so_hoa_don", "-id")
        .distinct()
    )


    return JsonResponse({
        "found": qs.exists(),
        "pos": [
            {
                "id": po.id,
                "po_number": po.po_number,
            }
            for po in qs
        ]
    })




from django.db.models import Prefetch
from django.db.models.functions import ExtractYear

PER_PAGE_OPTIONS = ["10", "20", "50", "all"]


def bank_payments_manage(request):
    # ---- NĂM TÀI CHÍNH ----
    selected_year = request.GET.get("year")
    if selected_year:
        try:
            request.session["fiscal_year"] = int(selected_year)
        except ValueError:
            pass

    current_year = request.session.get("fiscal_year", datetime.now().year)

    # ---- DANH SÁCH NĂM THEO BANK PAYMENT ----
    years_qs = (
        BankPayment.objects
        .exclude(payment_date__isnull=True)
        .annotate(y=ExtractYear("payment_date"))
        .values_list("y", flat=True)
        .distinct()
    )

    years = set(years_qs)
    years.add(current_year)

    year_list = sorted(years)


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

    # Lấy tất cả phiếu NH đã tạo
    nh_payments = BankPayment.objects.filter(
        is_summary=True,
        doc_no__startswith="NH"
    ).prefetch_related("purchase_orders")

    # Map PO id -> list doc_no phiếu NH đã lập
    bank_payment_nh_map = {}
    for nh in nh_payments:
        for po in nh.purchase_orders.all():
            bank_payment_nh_map.setdefault(po.id, []).append(nh.doc_no)


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
    payments_qs = BankPayment.objects.prefetch_related("purchase_orders")\
        .filter(
            is_summary=False,
            payment_date__year=current_year
        )\
        .order_by("-payment_date", "-id")

    # Lấy tất cả phiếu tổng hợp + NH
    summary_payments = BankPayment.objects.filter(
        Q(is_summary=True) | Q(content__icontains="NH"),  # hoặc Q(doc_no__startswith="NH")
        payment_date__year=current_year
    ).prefetch_related("purchase_orders")


    # Map PO id -> list doc_no đã lập
    po_summary_map = {}
    for sp in summary_payments:
        for po in sp.purchase_orders.all():
            po_summary_map.setdefault(po.id, []).append(sp.doc_no)




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
    opening_record = BankPayment.objects.filter(
        content="Opening Balance",
        payment_date__year=current_year
    ).first()
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
        "po_summary_map": po_summary_map,  # <-- thêm
        "bank_payment_nh_map": bank_payment_nh_map,  # thêm map NH
        "current_year": current_year,
        "year_list": year_list,
    })




from django.http import JsonResponse
from django.db.models import Q

def normalize_invoice_no(no):
    return no.lstrip("0")  # nếu cần chuẩn hóa số hóa đơn

def find_po_by_mst_invoice(request):
    mst = request.GET.get("mst", "").strip()
    sohd_raw = request.GET.get("sohd", "").strip()

    if not mst and not sohd_raw:
        return JsonResponse({"found": False, "pos": []})

    sohd_list = [
        normalize_invoice_no(x.strip())
        for x in sohd_raw.split(",")
        if x.strip()
    ]

    qs = PurchaseOrder.objects.all()

    # 🔹 Filter theo MST (nếu có)
    if mst:
        debit_q = Q(invoice__ma_so_thue=mst)
        credit_q = Q(customer__ma_so_thue=mst)
        qs = qs.filter(debit_q | credit_q)

    # 🔹 Filter theo Số hóa đơn (nếu có)
    if sohd_list:
        q_sohd = Q()
        for sohd in sohd_list:
            q_sohd |= (
                Q(invoice__so_hoa_don__endswith=sohd) |
                Q(customer__so_hoa_don__endswith=sohd)
            )
        qs = qs.filter(q_sohd)

    qs = (
        qs.select_related("customer", "invoice")
        .order_by("-invoice__so_hoa_don", "-id")
        .distinct()
    )

    return JsonResponse({
        "found": qs.exists(),
        "pos": [
            {
                "id": po.id,
                "po_number": po.po_number,
                "total_payment": po.total_payment,
                "customer_name": po.customer.ten_khach_hang if po.customer else "—",
                "customer_mst": po.customer.ma_so_thue if po.customer else "—",
                "so_hoa_don": po.invoice.so_hoa_don if po.invoice else "—",
            }
            for po in qs
        ]
    })





def generate_doc_no(payment_date):
    date_str = payment_date.strftime("%y%m%d")
    last_payment = BankPayment.objects.filter(
        doc_no__startswith=f"NH{date_str}-"
    ).order_by("-doc_no").first()

    last_seq = int(last_payment.doc_no.split("-")[-1]) if last_payment else 0
    return f"NH{date_str}-{last_seq + 1:03d}"

def bank_payment_credit(request, pk):
    payment = get_object_or_404(BankPayment, pk=pk)

    purchase_orders = (
        PurchaseOrder.objects
        .select_related("customer", "invoice")
        .filter(po_number__startswith="PX")
        .order_by("-invoice__so_hoa_don", "-id")
    )

    customers_with_opening_debt = Customer.objects.filter(phai_thu_dau_ky__gt=0)

    # Ngày nhập
    payment_date_str = request.POST.get("payment_date")
    if payment_date_str:
        payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
    else:
        payment_date = timezone.now().date()

    # Hàm kiểm tra phiếu summary đã tồn tại
    def get_existing_summary(payment_date, content, po_ids=None):
        qs = BankPayment.objects.filter(
            is_summary=True,
            payment_date=payment_date,
            content=content
        )
        if po_ids:
            qs = qs.filter(purchase_orders__id__in=po_ids)
        return qs.first()

    if request.method == "POST":
        payment_type = request.POST.get("payment_type", "po")

        # Cập nhật credit phiếu gốc
        credit_amount = parse_decimal_excel(request.POST.get("credit", "0"))
        payment.credit = credit_amount

        # ===== 1. THU THEO PO =====
        po_ids = request.POST.getlist("po_id")
        if payment_type == "po" and po_ids:
            selected_pos = PurchaseOrder.objects.filter(id__in=po_ids)
            payment.purchase_orders.set(po_ids)

            po_numbers = [po.po_number for po in selected_pos]
            content_summary = f"Thu tiền PO: {', '.join(po_numbers)}"
            total_po_amount = sum(po.invoice.tong_tien or 0 for po in selected_pos)
            doc_no = generate_doc_no(payment_date)

            existing_summary = get_existing_summary(payment_date, content_summary, po_ids)
            if existing_summary:
                # Cập nhật phiếu cũ
                existing_summary.credit = credit_amount
                existing_summary.amount = total_po_amount
                existing_summary.save(update_fields=["credit", "amount"])
            else:
                # Tạo mới
                BankPayment.objects.create(
                    credit=credit_amount,
                    amount=total_po_amount,
                    content=content_summary,
                    payment_date=payment_date,
                    doc_no=doc_no,
                    is_summary=True
                )

        # ===== 2. THU CHUYỂN KHOẢN =====
        if payment_type == "transfer" and credit_amount > 0:
            content_summary = payment.content
            doc_no = generate_doc_no(payment_date)

            existing_summary = get_existing_summary(payment_date, content_summary)
            if existing_summary:
                existing_summary.credit = credit_amount
                existing_summary.amount = credit_amount
                existing_summary.save(update_fields=["credit", "amount"])
            else:
                BankPayment.objects.create(
                    credit=credit_amount,
                    amount=credit_amount,
                    content=content_summary,
                    payment_date=payment_date,
                    doc_no=doc_no,
                    is_summary=True
                )

        # ===== 3. THU TIỀN LÃI =====
        if payment_type == "interest" and credit_amount > 0:
            content_summary = payment.content
            doc_no = generate_doc_no(payment_date)

            existing_summary = get_existing_summary(payment_date, content_summary)
            if existing_summary:
                existing_summary.credit = credit_amount
                existing_summary.amount = credit_amount
                existing_summary.save(update_fields=["credit", "amount"])
            else:
                BankPayment.objects.create(
                    credit=credit_amount,
                    amount=credit_amount,
                    content=content_summary,
                    payment_date=payment_date,
                    doc_no=doc_no,
                    is_summary=True
                )

        # ===== 4. THU NỢ ĐẦU KỲ KH =====
        if payment_type == "opening_customer":
            customer_id = request.POST.get("customer_id")
            opening_amount = parse_decimal_excel(request.POST.get("opening_amount", "0"))

            if customer_id and opening_amount > 0:
                customer = get_object_or_404(Customer, id=customer_id)
                content_summary = f"Thu nợ đầu kỳ KH: {customer.name}"
                doc_no = generate_doc_no(payment_date)

                existing_summary = get_existing_summary(payment_date, content_summary)
                if existing_summary:
                    existing_summary.credit = opening_amount
                    existing_summary.amount = opening_amount
                    existing_summary.save(update_fields=["credit", "amount"])
                else:
                    BankPayment.objects.create(
                        credit=opening_amount,
                        amount=opening_amount,
                        content=content_summary,
                        payment_date=payment_date,
                        doc_no=doc_no,
                        is_summary=True
                    )

                # Trừ nợ đầu kỳ khách hàng
                customer.phai_thu_dau_ky -= opening_amount
                customer.save(update_fields=["phai_thu_dau_ky"])

        # Cập nhật phiếu gốc
        payment.content = request.POST.get("content", payment.content)
        payment.save(update_fields=["credit", "content"])

        messages.success(request, "Tạo phiếu thu thành công!")
        return redirect("payment_list")

    return render(request, "bank_payment_credit.html", {
        "payment": payment,
        "purchase_orders": purchase_orders,
        "customers_with_opening_debt": customers_with_opening_debt
    })



def normalize_invoice_no(sohd):
    return sohd.lstrip("0")  # ví dụ normalize

def find_po_by_mst_invoice(request):
    mst = request.GET.get("mst", "").strip()
    sohd_raw = request.GET.get("sohd", "").strip()
    customer_name = request.GET.get("customer_name", "").strip()

    if not mst and not sohd_raw and not customer_name:
        return JsonResponse({"found": False, "pos": []})

    sohd_list = [normalize_invoice_no(x.strip()) for x in sohd_raw.split(",") if x.strip()]
    qs = PurchaseOrder.objects.select_related("customer", "invoice").all()

    if mst:
        qs = qs.filter(Q(customer__ma_so_thue=mst) | Q(invoice__ma_so_thue=mst))

    if sohd_list:
        q_sohd = Q()
        for sohd in sohd_list:
            q_sohd |= Q(invoice__so_hoa_don__endswith=sohd, invoice__isnull=False)
        qs = qs.filter(q_sohd)

    if customer_name:
        qs = qs.filter(customer__ten_khach_hang__icontains=customer_name)

    qs = qs.order_by("-invoice__so_hoa_don", "-id").distinct()

    return JsonResponse({
        "found": qs.exists(),
        "pos": [
            {
                "id": po.id,
                "po_number": po.po_number,
                "total_payment": po.total_payment,
                "customer_name": po.customer.ten_khach_hang if po.customer else "—",
                "customer_mst": po.customer.ma_so_thue if po.customer else "—",
                "so_hoa_don": po.invoice.so_hoa_don if po.invoice else "—",
            }
            for po in qs
        ]
    })
