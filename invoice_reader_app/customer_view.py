from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Sum, FloatField, ExpressionWrapper, F
from django.core.paginator import Paginator
from django.contrib import messages
from invoice_reader_app.model_invoice import Customer, InvoiceItem
from django.db.models import F, Sum, FloatField, ExpressionWrapper, Min, Max
from invoice_reader_app.model_invoice import Supplier, InvoiceItem, Invoice
from invoice_reader_app.models_purchaseorder import BankPayment, PurchaseOrder, CashReceipt, BankPaymentAllocation
from django.db.models import Sum, OuterRef, Subquery, DecimalField
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect
from django.db.models import Sum, F
from decimal import Decimal
from django.db.models import Q
from django.utils import timezone



# --- Thêm khách hàng ---
def customer_add(request):
    if request.method == 'POST':
        ma_so_thue = request.POST.get('ma_so_thue')
        ten_khach_hang = request.POST.get('ten_khach_hang')
        dia_chi = request.POST.get('dia_chi')
        phan_loai = request.POST.get('phan_loai')
        email = request.POST.get('email')

        Customer.objects.create(
            ma_so_thue=ma_so_thue,
            ten_khach_hang=ten_khach_hang,
            dia_chi=dia_chi,
            phan_loai=phan_loai,
            email=email,
           
        )
        return redirect('customers')

    return render(request, 'customer_form.html', {'action': 'Thêm'})


# --- Chỉnh sửa khách hàng ---
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)


    # Nếu là "Cung cấp hàng hoá", lấy danh mục sản phẩm liên quan đến khách hàng
    products = []
    if customer.phan_loai == "Cung cấp hàng hoá":
        products = InvoiceItem.objects.filter(
            customer=customer,
            so_luong__gt=0
        ).values(
            'ten_hang'
        ).annotate(
            total_so_luong=Sum('so_luong'),
            total_thanh_tien=Sum('thanh_tien'),
            total_tien_thue=Sum('tien_thue'),
            avg_don_gia=ExpressionWrapper(
                (Sum('thanh_tien') + Sum('tien_thue')) / Sum('so_luong'),
                output_field=FloatField()
            )
        ).order_by('ten_hang')

    if request.method == 'POST':
        customer.ten_khach_hang = request.POST.get('ten_khach_hang', '').strip()
        customer.ma_so_thue = request.POST.get('ma_so_thue', '').strip()
        customer.dia_chi = request.POST.get('dia_chi', '').strip()
        customer.phan_loai = request.POST.get('phan_loai', '').strip()
        customer.email = request.POST.get('email', '').strip()
        customer.save()
        messages.success(request, "✅ Cập nhật khách hàng thành công!")
        return redirect('customers')

    return render(request, 'customer_form.html', {
        'customer': customer,
        'action': 'Chỉnh sửa',
        'products': products,
    })


# --- Xóa khách hàng ---
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.delete()
    messages.success(request, "Đã xóa khách hàng.")
    return redirect("customers")


# ------------------------
# Danh sách phiếu thu tổng hợp
# ------------------------
def payment_list(request):
    # XÓA PHIẾU (nếu có yêu cầu)
    if request.method == "POST" and "delete_ids" in request.POST:
        delete_ids = request.POST.getlist("delete_ids")
        if delete_ids:
            count, _ = BankPayment.objects.filter(id__in=delete_ids).delete()
            messages.success(request, f"Đã xóa {count} phiếu thu.")
        return redirect("payment_list")

    # Lấy tất cả phiếu thu tổng hợp mới tạo: credit > 0, doc_no bắt đầu NH
    payments_qs = BankPayment.objects.filter(
        credit__gt=0,
        doc_no__startswith='NH'
    ).order_by('doc_no')

    # Tạo danh sách final, không gom content
    final_payments = []
    for p in payments_qs:
        remaining = (p.amount or 0) - (p.credit or 0)  # còn phải thu, có thể âm
        final_payments.append({
            "id": p.id,
            "doc_no": p.doc_no,
            "payment_date": p.payment_date,
            "content": p.content,
            "amount": p.amount or 0,
            "credit": p.credit or 0,
            "remaining": remaining
        })

    # Tổng cộng
    total_amount = sum(p['amount'] for p in final_payments)
    total_credit = sum(p['credit'] for p in final_payments)

    return render(request, "payment_list.html", {
        "payments": final_payments,
        "total_amount": total_amount,
        "total_credit": total_credit,
    })





def customers_view(request):
    search_customer = request.GET.get('search_customer', '').strip()

    # Lấy danh sách khách hàng từ model Customer
    customers_qs = Customer.objects.all()

    # Tìm kiếm theo tên hoặc MST
    if search_customer:
        customers_qs = customers_qs.filter(
            Q(ten_khach_hang__icontains=search_customer) |
            Q(ma_so_thue__icontains=search_customer)
        )

    # (Tùy chọn) Tính tổng số lượng, tổng tiền, tổng tiền thuế từ hóa đơn liên quan
    customers_qs = customers_qs.annotate(
        total_so_luong=Sum('invoiceitem__so_luong'),
        total_thanh_tien=Sum(
            ExpressionWrapper(
                F('invoiceitem__so_luong') * F('invoiceitem__don_gia'),
                output_field=FloatField()
            )
        ),
        total_tien_thue=Sum(
            ExpressionWrapper(
                F('invoiceitem__so_luong') * F('invoiceitem__don_gia') * F('invoiceitem__thue_suat') / 100,
                output_field=FloatField()
            )
        )
    ).order_by('ten_khach_hang')

    # Phân trang: 10 khách hàng/trang
    paginator = Paginator(customers_qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Xử lý query params khác ngoài page (để giữ khi chuyển trang)
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')

    context = {
        'customers': page_obj,         # trang hiện tại
        'data': page_obj,              # nếu bạn dùng component pagination chung
        'search_customer': search_customer,
        'query_params': query_params.urlencode(),
        'label': 'khách hàng',
    }

    return render(request, 'customers.html', context)






from collections import OrderedDict
from decimal import Decimal
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date

def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    invoices = Invoice.objects.filter(ma_so_thue_mua=customer.ma_so_thue).order_by('-so_hoa_don')
    if start_date:
        invoices = invoices.filter(ngay_hd__gte=parse_date(start_date))
    if end_date:
        invoices = invoices.filter(ngay_hd__lte=parse_date(end_date))

    total_invoice = Decimal('0.00')
    total_paid_all = Decimal('0.00')
    invoice_data = []

    # Lấy tất cả PO liên quan đến invoices
    purchase_orders = PurchaseOrder.objects.filter(invoice__in=invoices)
    # Lấy tất cả BankPayment liên quan
    payments_qs = BankPayment.objects.filter(purchase_orders__in=purchase_orders).distinct()

    # Gom theo doc_no để merge nhiều PO, nhiều hóa đơn
    doc_summary = OrderedDict()
    for p in payments_qs:
        if p.doc_no not in doc_summary:
            doc_summary[p.doc_no] = {
                "credit": p.credit,
                "payment_date": p.payment_date,
                "content": p.content,
                "invoice_ids": [po.invoice.id for po in p.purchase_orders.all() if po.invoice],
            }
        else:
            doc_summary[p.doc_no]["credit"] += p.credit
            doc_summary[p.doc_no]["invoice_ids"].extend([po.invoice.id for po in p.purchase_orders.all() if po.invoice])
            doc_summary[p.doc_no]["invoice_ids"] = list(set(doc_summary[p.doc_no]["invoice_ids"]))

    printed_docs = set()

    for inv in invoices:
        inv_payments = []
        merged_total_paid = None

        # Kiểm tra doc nào liên quan đến invoice này
        for doc_no, doc in doc_summary.items():
            if inv.id in doc["invoice_ids"]:
                inv_payments.append({
                    "content": doc["content"],
                    "payment_date": doc["payment_date"],
                    "credit": doc["credit"]
                })
                if doc_no not in printed_docs:
                    merged_total_paid = doc["credit"]
                    total_paid_all += doc["credit"]  # ✅ chỉ cộng 1 lần cho doc này
                    printed_docs.add(doc_no)

        total_invoice += inv.tong_tien or Decimal('0.00')

       

        invoice_data.append({
            "invoice": inv,
            "payments": inv_payments,
            "merged_total_paid": merged_total_paid,
            "has_shared_payment": bool(inv_payments) and not merged_total_paid,
            "total_paid": sum(p["credit"] for p in inv_payments),
        })

    return render(request, "customer_detail.html", {
        "customer": customer,
        "invoice_data": invoice_data,
        "total_invoice": total_invoice,
        "total_paid_all": total_paid_all,
        "start_date": start_date,
        "end_date": end_date,
    })
from collections import OrderedDict
from decimal import Decimal
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import render


def customers_view(request):
    search_customer = request.GET.get('search_customer', '').strip()

    # Lấy danh sách khách hàng
    customers_qs = Customer.objects.all()

    # Tìm kiếm theo tên hoặc MST
    if search_customer:
        customers_qs = customers_qs.filter(
            Q(ten_khach_hang__icontains=search_customer) |
            Q(ma_so_thue__icontains=search_customer)
        )

    # (Tùy chọn) tính tổng số lượng và tổng tiền từ invoice items
    customers_qs = customers_qs.annotate(
        total_so_luong=Sum('invoiceitem__so_luong'),
        total_thanh_tien=Sum(
            ExpressionWrapper(
                F('invoiceitem__so_luong') * F('invoiceitem__don_gia'),
                output_field=DecimalField()
            )
        ),
        total_tien_thue=Sum(
            ExpressionWrapper(
                F('invoiceitem__so_luong') * F('invoiceitem__don_gia') * F('invoiceitem__thue_suat') / 100,
                output_field=DecimalField()
            )
        )
    ).order_by('ten_khach_hang')

    # Lấy tất cả invoices của các khách hàng
    invoices = Invoice.objects.filter(ma_so_thue_mua__in=[c.ma_so_thue for c in customers_qs])
    
    # Lấy tất cả PO liên quan
    purchase_orders = PurchaseOrder.objects.filter(invoice__in=invoices)
    
    # Lấy tất cả BankPayment liên quan
    payments_qs = BankPayment.objects.filter(purchase_orders__in=purchase_orders).distinct()

    # Gom theo doc_no để merge nhiều PO + nhiều hóa đơn
    doc_summary = OrderedDict()
    for p in payments_qs:
        if p.doc_no not in doc_summary:
            doc_summary[p.doc_no] = {
                "credit": p.credit,
                "invoice_ids": [po.invoice.id for po in p.purchase_orders.all() if po.invoice]
            }
        else:
            doc_summary[p.doc_no]["credit"] += p.credit
            doc_summary[p.doc_no]["invoice_ids"].extend([po.invoice.id for po in p.purchase_orders.all() if po.invoice])
            doc_summary[p.doc_no]["invoice_ids"] = list(set(doc_summary[p.doc_no]["invoice_ids"]))

    # Tính tổng invoice và tổng đã thu cho từng MST
    totals_by_customer = {}
    printed_docs = set()
    for inv in invoices:
        total_invoice = inv.tong_tien or Decimal('0.00')
        total_paid = Decimal('0.00')

        # Tổng đã thu: chỉ cộng mỗi doc 1 lần
        for doc_no, doc in doc_summary.items():
            if inv.id in doc["invoice_ids"] and doc_no not in printed_docs:
                total_paid += doc["credit"]
                printed_docs.add(doc_no)

        mst = inv.ma_so_thue_mua
        if mst not in totals_by_customer:
            totals_by_customer[mst] = {
                "total_invoice": total_invoice,
                "total_paid": total_paid
            }
        else:
            totals_by_customer[mst]["total_invoice"] += total_invoice
            totals_by_customer[mst]["total_paid"] += total_paid

    # Tính phần trăm đã thu và gắn thuộc tính cho template
    customer_data = []
    for customer in customers_qs:
        totals = totals_by_customer.get(customer.ma_so_thue, {"total_invoice": Decimal('0.00'), "total_paid": Decimal('0.00')})
        total_invoice = totals["total_invoice"]
        total_paid = totals["total_paid"]
        percent_paid = (total_paid / total_invoice * 100).quantize(Decimal('0.01')) if total_invoice else Decimal('0.00')

        customer.total_invoice_calc = total_invoice
        customer.total_paid_calc = total_paid
        customer.percent_paid_calc = percent_paid

        customer_data.append(customer)

    # Phân trang: 10 khách hàng/trang
    paginator = Paginator(customer_data, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')

    context = {
        'customers': page_obj,
        'data': page_obj,
        'search_customer': search_customer,
        'query_params': query_params.urlencode(),
        'label': 'khách hàng',
    }

    return render(request, 'customers.html', context)

# Trang nhập số dư đầu kỳ phải thu/phải trả



@require_http_methods(["GET", "POST"])
def customer_opening_balance(request):
    search_customer = request.GET.get('search_customer', '').strip()

    customers = Customer.objects.all().order_by('ten_khach_hang')
    if search_customer:
        customers = customers.filter(
            Q(ten_khach_hang__icontains=search_customer) |
            Q(ma_so_thue__icontains=search_customer)
        )

    # Tính tổng phải thu / phải trả hiện có (trên tất cả khách hàng đang hiển thị)
    totals = customers.aggregate(
        total_receivable=Sum(F('phai_thu_dau_ky')),
        total_payable=Sum(F('phai_tra_dau_ky'))
    )

    if request.method == 'POST':
        for customer in customers:
            receivable_key = f"receivable_{customer.id}"
            payable_key = f"payable_{customer.id}"

            receivable_val = request.POST.get(receivable_key, "0").replace(",", "")
            payable_val = request.POST.get(payable_key, "0").replace(",", "")

            try:
                customer.phai_thu_dau_ky = Decimal(receivable_val)
            except:
                customer.phai_thu_dau_ky = Decimal("0")

            try:
                customer.phai_tra_dau_ky = Decimal(payable_val)
            except:
                customer.phai_tra_dau_ky = Decimal("0")

            customer.save()

        return redirect(f'{request.path}?search_customer={search_customer}')  # reload trang sau khi lưu, giữ tìm kiếm

    context = {
        'customers': customers,
        'totals': totals,
        'search_customer': search_customer
    }
    return render(request, 'customer_opening_balance.html', context)


from collections import OrderedDict
from decimal import Decimal
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date

def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # =============================
    # 1. Fetch invoices and filter by date
    # =============================
    invoices = Invoice.objects.filter(
        ma_so_thue_mua=customer.ma_so_thue
    ).order_by('-ngay_hd', '-so_hoa_don')

    if start_date:
        invoices = invoices.filter(ngay_hd__gte=parse_date(start_date))
    if end_date:
        invoices = invoices.filter(ngay_hd__lte=parse_date(end_date))

    # =============================
    # 2. Remove duplicate invoices by invoice number
    # =============================
    seen_invoice_numbers = set()
    unique_invoices = []
    for inv in invoices:
        if inv.so_hoa_don not in seen_invoice_numbers:
            unique_invoices.append(inv)
            seen_invoice_numbers.add(inv.so_hoa_don)
    invoices = unique_invoices

    # =============================
    # 3. Fetch related purchase orders & payments
    # =============================
    purchase_orders = PurchaseOrder.objects.filter(invoice__in=invoices)
    payments = (
        BankPayment.objects
        .filter(purchase_orders__in=purchase_orders)
        .prefetch_related('purchase_orders__invoice')
        .distinct()
    )

    # =============================
    # 4. Aggregate payments by doc_no
    # =============================
    doc_map = OrderedDict()
    for p in payments:
        if p.doc_no not in doc_map:
            doc_map[p.doc_no] = {
                "credit": Decimal(p.credit or 0),
                "payment_date": p.payment_date,
                "content": p.content,
                "invoice_ids": set(),
            }
        for po in p.purchase_orders.all():
            if po.invoice:
                doc_map[p.doc_no]["invoice_ids"].add(po.invoice.id)

    # =============================
    # 5. Map invoice → payments
    # =============================
    invoice_data = []
    total_paid_all = Decimal('0.00')
    total_invoice = Decimal('0.00')
    printed_docs = set()  # avoid double-counting shared payments

    for inv in invoices:
        inv_payments = []

        for doc_no, doc in doc_map.items():
            if inv.id in doc["invoice_ids"]:
                inv_payments.append({
                    "doc_no": doc_no,
                    "content": doc["content"],
                    "payment_date": doc["payment_date"],
                    "credit": doc["credit"],
                })
                if doc_no not in printed_docs:
                    total_paid_all += doc["credit"]
                    printed_docs.add(doc_no)

        # Sum total invoice amount
        total_invoice += inv.tong_tien or Decimal('0.00')

        invoice_data.append({
            "invoice": inv,
            "payments": inv_payments,
            "merged_total_paid": sum(p["credit"] for p in inv_payments) if inv_payments else None,
            "has_shared_payment": False,
            "total_paid": sum(p["credit"] for p in inv_payments),
        })

    # =============================
    # 6. Opening and closing balances
    # =============================
    opening_balance = (customer.phai_thu_dau_ky or Decimal('0.00')) - (customer.phai_tra_dau_ky or Decimal('0.00'))
    closing_balance = opening_balance + total_invoice - total_paid_all

    return render(request, "customer_detail.html", {
        "customer": customer,
        "invoice_data": invoice_data,
        "total_invoice": total_invoice,
        "total_paid_all": total_paid_all,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "start_date": start_date,
        "end_date": end_date,
    })


from collections import defaultdict, OrderedDict
from decimal import Decimal
from django.db.models import Q, Sum, F, DecimalField, ExpressionWrapper
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils.dateparse import parse_date

def customers_view(request):
    search_customer = request.GET.get('search_customer', '').strip()
    customers_qs = Customer.objects.all()

    # Filter by search term
    if search_customer:
        customers_qs = customers_qs.filter(
            Q(ten_khach_hang__icontains=search_customer) |
            Q(ma_so_thue__icontains=search_customer)
        )

    # Annotate customers with invoice item totals
    customers_qs = customers_qs.annotate(
        total_so_luong=Sum('invoiceitem__so_luong'),
        total_thanh_tien=Sum(
            ExpressionWrapper(
                F('invoiceitem__so_luong') * F('invoiceitem__don_gia'),
                output_field=DecimalField()
            )
        ),
        total_tien_thue=Sum(
            ExpressionWrapper(
                F('invoiceitem__so_luong') * F('invoiceitem__don_gia') * F('invoiceitem__thue_suat') / 100,
                output_field=DecimalField()
            )
        )
    ).order_by('ten_khach_hang')

    # Fetch invoices for filtered customers
    invoices = Invoice.objects.filter(ma_so_thue_mua__in=[c.ma_so_thue for c in customers_qs]).order_by('ma_so_thue_mua', 'so_hoa_don')

    # Remove duplicate invoices by so_hoa_don per customer
    unique_invoices = []
    seen = defaultdict(set)
    for inv in invoices:
        if inv.so_hoa_don not in seen[inv.ma_so_thue_mua]:
            unique_invoices.append(inv)
            seen[inv.ma_so_thue_mua].add(inv.so_hoa_don)
    invoices = unique_invoices

    # Fetch all payments linked to these invoices through purchase orders
    purchase_orders = PurchaseOrder.objects.filter(invoice__in=invoices)
    payments = BankPayment.objects.filter(purchase_orders__in=purchase_orders).prefetch_related('purchase_orders__invoice').distinct()
    cash_receipts = CashReceipt.objects.filter(invoice__in=invoices)
    # Map invoices to their customer
    invoices_by_customer = defaultdict(list)
    for inv in invoices:
        invoices_by_customer[inv.ma_so_thue_mua].append(inv)

    # Aggregate payments per customer
    payments_by_customer = defaultdict(Decimal)
    cash_by_customer = defaultdict(Decimal)

    for receipt in cash_receipts:
        if receipt.invoice:
            cash_by_customer[
                receipt.invoice.ma_so_thue_mua
            ] += receipt.amount or Decimal("0")
    printed_docs = set()
    for p in payments:
        linked_invoices = [po.invoice for po in p.purchase_orders.all() if po.invoice]
        linked_customers = set(inv.ma_so_thue_mua for inv in linked_invoices)
        # Split payment per invoice to avoid double-counting
        credit_per_invoice = (p.credit or Decimal('0.00')) / max(len(linked_invoices), 1)
        for inv in linked_invoices:
            if (p.doc_no, inv.id) not in printed_docs:
                payments_by_customer[inv.ma_so_thue_mua] += credit_per_invoice
                printed_docs.add((p.doc_no, inv.id))

    # Attach totals to each customer object
    customer_data = []
    for customer in customers_qs:
        total_invoice = sum(inv.tong_tien or Decimal('0.00') for inv in invoices_by_customer.get(customer.ma_so_thue, []))
        bank_paid = payments_by_customer.get(
            customer.ma_so_thue,
            Decimal("0.00")
        )

        cash_paid = cash_by_customer.get(
            customer.ma_so_thue,
            Decimal("0.00")
        )

        total_paid = bank_paid + cash_paid
        percent_paid = (total_paid / total_invoice * 100).quantize(Decimal('0.01')) if total_invoice else Decimal('0.00')

        customer.total_invoice_calc = total_invoice
        customer.total_paid_calc = total_paid
        customer.percent_paid_calc = percent_paid
        customer_data.append(customer)

    # Paginate
    paginator = Paginator(customer_data, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop('page', None)

    return render(request, 'customers.html', {
        'customers': page_obj,
        'data': page_obj,
        'search_customer': search_customer,
        'query_params': query_params.urlencode(),
        'label': 'khách hàng',
    })


from django.core.paginator import Paginator
from decimal import Decimal
from collections import OrderedDict
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date

def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    page_number = request.GET.get("page", 1)

    # =============================
    # 1. Fetch invoices and filter by date
    # =============================
    invoices = Invoice.objects.filter(
        ma_so_thue_mua=customer.ma_so_thue
    ).order_by('-ngay_hd', '-so_hoa_don')

    if start_date:
        invoices = invoices.filter(ngay_hd__gte=parse_date(start_date))
    if end_date:
        invoices = invoices.filter(ngay_hd__lte=parse_date(end_date))

    # =============================
    # 2. Remove duplicate invoices by invoice number
    # =============================
    seen_invoice_numbers = set()
    unique_invoices = []
    for inv in invoices:
        if inv.so_hoa_don not in seen_invoice_numbers:
            unique_invoices.append(inv)
            seen_invoice_numbers.add(inv.so_hoa_don)
    invoices = unique_invoices

    # =============================
    # 3. Fetch related purchase orders & payments
    # =============================
    purchase_orders = PurchaseOrder.objects.filter(invoice__in=invoices)
    payments = (
        BankPayment.objects
        .filter(purchase_orders__in=purchase_orders)
        .prefetch_related('purchase_orders__invoice')
        .distinct()
    )

    # =============================
    # 4. Aggregate payments by doc_no
    # =============================
    doc_map = OrderedDict()
    for p in payments:
        if p.doc_no not in doc_map:
            doc_map[p.doc_no] = {
                "credit": Decimal(p.credit or 0),
                "payment_date": p.payment_date,
                "content": p.content,
                "invoice_ids": set(),
            }
        for po in p.purchase_orders.all():
            if po.invoice:
                doc_map[p.doc_no]["invoice_ids"].add(po.invoice.id)

    # =============================
    # 5. Map invoice → payments
    # =============================
    invoice_data = []
    total_paid_all = Decimal('0.00')
    total_invoice = Decimal('0.00')
    printed_docs = set()  # avoid double-counting shared payments
    cash_receipts = CashReceipt.objects.filter(invoice__in=invoices)

    cash_map = {}
    for c in cash_receipts:
        cash_map[c.invoice_id] = cash_map.get(c.invoice_id, Decimal("0")) + (c.amount or 0)   

    for inv in invoices:
        inv_payments = []
        bank_paid = Decimal("0")
        cash_paid = cash_map.get(inv.id, Decimal("0"))
        cash_receipt_list = CashReceipt.objects.filter(
            invoice=inv
        ).order_by("created_at")
        for doc_no, doc in doc_map.items():
            if inv.id in doc["invoice_ids"]:
                inv_payments.append({
                    "doc_no": doc_no,
                    "content": doc["content"],
                    "payment_date": doc["payment_date"],
                    "credit": doc["credit"],
                })
                bank_paid += doc["credit"]

        total_paid = bank_paid + cash_paid
        invoice_amount = inv.tong_tien or Decimal("0")
        con_no = invoice_amount - total_paid
        
        total_invoice += invoice_amount
    # THÊM DÒNG NÀY
        total_paid_all += total_paid
        invoice_data.append({
            "invoice": inv,
            "payments": inv_payments,
            "cash_receipts": cash_receipt_list,   # THÊM DÒNG NÀY
            "bank_paid": bank_paid,
            "cash_paid": cash_paid,
            "total_paid": total_paid,
            "con_no": con_no,
        })

    # =============================
    # 6. Opening and closing balances
    # =============================
    opening_balance = (customer.phai_thu_dau_ky or Decimal('0.00')) - (customer.phai_tra_dau_ky or Decimal('0.00'))
    closing_balance = opening_balance + total_invoice - total_paid_all

    # =============================
    # 7. Paginate invoice_data
    # =============================
    paginator = Paginator(invoice_data, 10)  # 10 invoices per page
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop('page', None)

    return render(request, "customer_detail.html", {
        "customer": customer,
        "invoice_data": page_obj,  # paginated invoices
        "total_invoice": total_invoice,
        "total_paid_all": total_paid_all,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "start_date": start_date,
        "end_date": end_date,
        "query_params": query_params.urlencode(),
        "paginator": paginator,

    })
from django.shortcuts import get_object_or_404, render, redirect
from decimal import Decimal
from django.db.models import Sum


def cash_receipt_create(request, invoice_id):

    invoice = get_object_or_404(Invoice, id=invoice_id)

    customer = get_object_or_404(
        Customer,
        ma_so_thue=invoice.ma_so_thue_mua
    )


    # =============================
    # TÍNH ĐÃ THU (BANK + CASH)
    # =============================

    cash_paid = (
        CashReceipt.objects
        .filter(invoice=invoice)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )


    bank_paid = (
        BankPayment.objects
        .filter(purchase_orders__invoice=invoice)
        .aggregate(total=Sum("credit"))["total"]
        or Decimal("0")
    )


    paid = cash_paid + bank_paid


    con_no = (
        invoice.tong_tien or Decimal("0")
    ) - paid



    # =============================
    # LƯU PHIẾU THU
    # =============================

    if request.method == "POST":

        amount = Decimal(
            request.POST.get("amount", "0")
        )

        note = request.POST.get("note", "")


        if amount <= 0:
            return render(
                request,
                "cash_receipt_create.html",
                {
                    "invoice": invoice,
                    "customer": customer,
                    "paid": paid,
                    "cash_paid": cash_paid,
                    "bank_paid": bank_paid,
                    "con_no": con_no,
                    "error": "Số tiền không hợp lệ"
                }
            )


        if amount > con_no:
            return render(
                request,
                "cash_receipt_create.html",
                {
                    "invoice": invoice,
                    "customer": customer,
                    "paid": paid,
                    "cash_paid": cash_paid,
                    "bank_paid": bank_paid,
                    "con_no": con_no,
                    "error": "Số tiền thu lớn hơn công nợ"
                }
            )

        receipt_no = generate_cash_receipt_no()

        CashReceipt.objects.create(
            invoice=invoice,
            receipt_no=receipt_no,
            amount=amount,
            note=note
        )


        return redirect(
            "customer_detail",
            pk=customer.id
        )



    return render(
        request,
        "cash_receipt_create.html",
        {
            "invoice": invoice,
            "customer": customer,
            "paid": paid,
            "cash_paid": cash_paid,
            "bank_paid": bank_paid,
            "con_no": con_no,
        }
    )



from django.utils import timezone
from django.db.models import Max
import re


def generate_cash_receipt_no():
    today = timezone.now().strftime("%y%m%d")
    prefix = f"TM{today}-"

    last_receipt = (
        CashReceipt.objects
        .filter(receipt_no__startswith=prefix)
        .order_by("-receipt_no")
        .first()
    )

    if last_receipt:
        last_number = int(
            last_receipt.receipt_no.split("-")[1]
        )
        next_number = last_number + 1
    else:
        next_number = 1

    return f"{prefix}{next_number:04d}"


from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render


def cash_receipt_update(request, pk):
    receipt = get_object_or_404(CashReceipt, pk=pk)

    invoice = receipt.invoice
    customer = get_object_or_404(
        Customer,
        ma_so_thue=invoice.ma_so_thue_mua
    )

    invoice_amount = invoice.tong_tien or Decimal("0")

    other_cash_paid = (
        CashReceipt.objects
        .filter(invoice=invoice)
        .exclude(pk=receipt.pk)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )

    bank_paid = (
        BankPayment.objects
        .filter(purchase_orders__invoice=invoice)
        .aggregate(total=Sum("credit"))["total"]
        or Decimal("0")
    )

    max_amount = invoice_amount - bank_paid - other_cash_paid

    if request.method == "POST":

        amount = Decimal(request.POST.get("amount", "0"))
        note = request.POST.get("note", "").strip()

        if amount <= 0:
            return render(request, "cash_receipt_update.html", {
                "receipt": receipt,
                "invoice": invoice,
                "customer": customer,
                "bank_paid": bank_paid,
                "cash_paid": other_cash_paid,
                "max_amount": max_amount,
                "error": "Số tiền không hợp lệ",
            })

        if amount > max_amount:
            return render(request, "cash_receipt_update.html", {
                "receipt": receipt,
                "invoice": invoice,
                "customer": customer,
                "bank_paid": bank_paid,
                "cash_paid": other_cash_paid,
                "max_amount": max_amount,
                "error": "Số tiền thu vượt công nợ",
            })

        receipt.amount = amount
        receipt.note = note
        receipt.save()

        return redirect("customer_detail", pk=customer.id)

    return render(request, "cash_receipt_update.html", {
        "receipt": receipt,
        "invoice": invoice,
        "customer": customer,
        "bank_paid": bank_paid,
        "cash_paid": other_cash_paid,
        "max_amount": max_amount,
    })




from django.views.decorators.http import require_POST

@require_POST
def cash_receipt_delete(request, pk):

    receipt = get_object_or_404(
        CashReceipt,
        pk=pk
    )

    customer_id = Customer.objects.get(
        ma_so_thue=receipt.invoice.ma_so_thue_mua
    ).id

    receipt.delete()

    return redirect(
        "customer_detail",
        pk=customer_id
    )


def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    page_number = request.GET.get("page", 1)

    # =============================
    # 1. Lấy hóa đơn của khách hàng
    # =============================
    invoices = Invoice.objects.filter(
        ma_so_thue_mua=customer.ma_so_thue
    ).order_by(
        "-ngay_hd",
        "-so_hoa_don"
    )

    if start_date:
        invoices = invoices.filter(
            ngay_hd__gte=parse_date(start_date)
        )

    if end_date:
        invoices = invoices.filter(
            ngay_hd__lte=parse_date(end_date)
        )


    # =============================
    # 2. Loại hóa đơn trùng số HĐ
    # =============================
    seen_invoice_numbers = set()
    unique_invoices = []

    for inv in invoices:
        if inv.so_hoa_don not in seen_invoice_numbers:
            unique_invoices.append(inv)
            seen_invoice_numbers.add(inv.so_hoa_don)

    invoices = unique_invoices


    # =============================
    # 3. Lấy PO của hóa đơn
    # =============================
    purchase_orders = (
        PurchaseOrder.objects
        .filter(invoice__in=invoices)
        .select_related(
            "invoice",
            "customer"
        )
    )


    # =============================
    # 4. Lấy phân bổ thu tiền thực tế
    # =============================
    allocations = (
        BankPaymentAllocation.objects
        .filter(
            purchase_order__in=purchase_orders
        )
        .select_related(
            "payment",
            "payment__parent_payment",
            "purchase_order",
            "purchase_order__invoice"
        )
    )


    # invoice_id -> danh sách phiếu thu
    invoice_payment_map = {}

    for alloc in allocations:

        po = alloc.purchase_order

        if not po.invoice:
            continue


        invoice_id = po.invoice.id


        invoice_payment_map.setdefault(invoice_id, []).append({
            "doc_no": alloc.payment.doc_no,
            # Phiếu tổng hợp
            "summary_doc_no": alloc.payment.doc_no,
            "summary_date": alloc.payment.payment_date,

            # Phiếu NH gốc
            "bank_doc_no": (
                alloc.payment.parent_payment.doc_no
                if alloc.payment.parent_payment else ""
            ),
            "bank_date": (
                alloc.payment.parent_payment.payment_date
                if alloc.payment.parent_payment else None
            ),
            "bank_content": (
                alloc.payment.parent_payment.content
                if alloc.payment.parent_payment else ""
            ),

            "content": alloc.payment.content,
            "payment_date": alloc.payment.payment_date,
            "credit": alloc.allocated_amount,
        })

    # =============================
    # 4.5. Lấy phiếu thu nợ đầu kỳ
    # =============================

    opening_payments = (
        BankPayment.objects.filter(
            is_summary=True,
            customer=customer,
            content__startswith="Thu nợ đầu kỳ KH:",
        )
        .order_by("payment_date")
    )
    
    opening_paid = Decimal("0")

    opening_payment_list = []


    for p in opening_payments:

        amount = (
            p.credit
            or Decimal("0")
        )

        opening_paid += amount


        opening_payment_list.append({

            "doc_no": p.doc_no,

            "content": p.content,

            "payment_date": p.payment_date,

            "credit": amount,

        })


    # =============================
    # Phiếu thu trực tiếp khách hàng
    # =============================

    customer_payments = (
        BankPayment.objects
        .filter(
            is_summary=True,
            customer=customer
        )
        .exclude(
            content__startswith="Thu nợ đầu kỳ KH:"
        )
        .exclude(
            purchase_orders__isnull=False
        )
        .distinct()
        .order_by("payment_date")
    )
    customer_payment_list = []

    customer_payment_paid = Decimal("0")

    for p in customer_payments:

        amount = (
            p.credit
            or Decimal("0")
        )

        customer_payment_paid += amount

        customer_payment_list.append({
             "payment":p, 

            "doc_no": p.doc_no,

            "content": p.content,

            "payment_date": p.payment_date,

            "credit": amount,

        })
    # =============================
    # 5. Thu tiền mặt
    # =============================
    cash_receipts = (
        CashReceipt.objects
        .filter(
            invoice__in=invoices
        )
        .order_by(
            "created_at"
        )
    )


    cash_map = {}

    for c in cash_receipts:

        cash_map[c.invoice_id] = (
            cash_map.get(
                c.invoice_id,
                Decimal("0")
            )
            +
            (c.amount or Decimal("0"))
        )


    # =============================
    # 6. Gắn thanh toán vào hóa đơn
    # =============================
    invoice_data = []

    total_invoice = Decimal("0")

    total_paid_all = Decimal("0")


    for inv in invoices:


        inv_payments = []

        bank_paid = Decimal("0")


        # lấy đúng số tiền đã phân bổ
        for item in invoice_payment_map.get(
            inv.id,
            []
        ):

            inv_payments.append({
                "doc_no": item["doc_no"],
                "summary_doc_no": item["summary_doc_no"],
                "summary_date": item["summary_date"],
                "bank_doc_no": item["bank_doc_no"],
                "bank_date": item["bank_date"],
                "bank_content": item["bank_content"],
                "content": item["content"],
                "payment_date": item["payment_date"],
                "credit": item["credit"],
            })


            bank_paid += item["credit"]



        cash_paid = cash_map.get(
            inv.id,
            Decimal("0")
        )


        total_paid = (
            bank_paid
            +
            cash_paid
        )


        invoice_amount = (
            inv.tong_tien
            or Decimal("0")
        )


        con_no = (
            invoice_amount
            -
            total_paid
        )


        total_invoice += invoice_amount

        total_paid_all += total_paid



        invoice_data.append({

            "invoice": inv,

            "payments": inv_payments,


            "cash_receipts": CashReceipt.objects.filter(
                invoice=inv
            ).order_by(
                "created_at"
            ),


            "bank_paid": bank_paid,

            "cash_paid": cash_paid,

            "total_paid": total_paid,

            "con_no": con_no,

        })


    # =============================
    # 7. Công nợ đầu kỳ / cuối kỳ
    # =============================
    opening_balance = (
        customer.phai_thu_dau_ky
        or Decimal("0")
    ) - (
        customer.phai_tra_dau_ky
        or Decimal("0")
    )


    closing_balance = (       opening_balance        +        total_invoice        -        total_paid_all        -        opening_paid -customer_payment_paid    )
    # =============================
    # 8. Phân trang
    # =============================
    paginator = Paginator(
        invoice_data,
        10
    )

    page_obj = paginator.get_page(
        page_number
    )


    query_params = request.GET.copy()

    query_params.pop(
        "page",
        None
    )


    return render(
        request,
        "customer_detail.html",
        {

            "customer": customer,

            "invoice_data": page_obj,

            "total_invoice": total_invoice,

            "total_paid_all": total_paid_all,

            "opening_balance": opening_balance,

            "closing_balance": closing_balance,

            "start_date": start_date,

            "end_date": end_date,

            "query_params": query_params.urlencode(),

            "paginator": paginator,
            "opening_payments": opening_payment_list,
                "opening_paid": opening_paid,
                "customer_payment_list": customer_payment_list,
        }
    )


def search_customer(request):

    q = request.GET.get("q", "").strip()

    print("SEARCH CUSTOMER:", q)

    customers = Customer.objects.filter(
        Q(ten_khach_hang__icontains=q) |
        Q(ma_so_thue__icontains=q)
    )[:30]


    print("COUNT:", customers.count())


    results=[]

    for c in customers:
        print(c.ten_khach_hang)

        results.append({
            "id":c.id,
            "text":f"{c.ten_khach_hang} - {c.ma_so_thue}"
        })


    return JsonResponse({
        "results":results
    })


from django.http import JsonResponse
