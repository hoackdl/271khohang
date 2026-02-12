from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

import json
from django.db.models import Max
from invoice_reader_app.models_purcharoder import PurchaseOrder, PurchaseOrderItem
from invoice_reader_app.model_invoice import Invoice, ProductName, Supplier
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
from django.db.models import Sum, F, FloatField
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.db.models import Sum
from django.core.paginator import Paginator
from datetime import datetime
from django.db.models import Min, Max




def normalize_tax(tax_value):
    """
    Chuyển giá trị thuế (có thể là string, None) sang Decimal.
    """
    try:
        return Decimal(str(tax_value or 0).replace("%", "").strip())
    except:
        return Decimal("0")

def sync_po_items_from_invoice(po, invoice):
    items = invoice.items.all()
    if not items.exists():
        return False

    with transaction.atomic():
        # Xóa item cũ
        po.items.all().delete()

        items_to_create = []

        for item in items:
            # Lấy thông tin product nếu có
            product = ProductName.objects.filter(ten_hang__iexact=item.ten_hang).first()
            sku = item.sku or (product.sku if product else "")
            ten_goi_chung = item.ten_goi_chung or (product.ten_goi_chung if product else "")

            # Chuyển sang Decimal
            quantity = Decimal(item.so_luong or 0)
            unit_price = Decimal(item.don_gia or 0)
            total_price = (quantity * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Chuẩn hóa thuế suất
            tax_rate = normalize_tax(item.thue_suat)
            tien_thue = (total_price * tax_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Đảm bảo Supplier tồn tại
            supplier, _ = Supplier.objects.get_or_create(
                ma_so_thue=invoice.ma_so_thue,
                defaults={
                    "ten_dv_ban": invoice.ten_dv_ban,
                    "dia_chi": invoice.dia_chi
                }
            )

            items_to_create.append(
                PurchaseOrderItem(
                    purchase_order=po,
                    product_name=item.ten_hang,
                    quantity=quantity,
                    unit=item.dvt or "",
                    unit_price=unit_price,
                    total_price=total_price,
                    thue_suat_field=tax_rate,
                    tien_thue_field=tien_thue,
                    sku=sku,
                    ten_goi_chung=ten_goi_chung,
                   
                )
            )

        # Bulk create tất cả item
        PurchaseOrderItem.objects.bulk_create(items_to_create)

        # Cập nhật tổng cộng
        po.total_amount = sum(i.total_price for i in po.items.all()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        po.total_tax = sum(i.tien_thue_field for i in po.items.all()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        po.save()

    return True



# 🧩 Mở hoặc đồng bộ PO từ hóa đơn
def open_or_sync_po_from_invoice(request, invoice):
    po = PurchaseOrder.objects.filter(invoice=invoice).first()
    if not po:
        po_number = f"PO{invoice.id:05d}"
        po = PurchaseOrder.objects.create(
            invoice=invoice,
            po_number=po_number,
            supplier=invoice.ten_dv_ban,
            total_amount=Decimal(invoice.tong_tien or 0),
            total_tax=Decimal('0'),
        )

    if not sync_po_items_from_invoice(po, invoice):
        messages.warning(request, "Hóa đơn chưa có chi tiết hàng hóa. PO hiện tại sẽ rỗng.")
        return po

    messages.success(request, f"PO #{po.po_number} đã đồng bộ với hóa đơn #{invoice.so_hoa_don}.")
    return po



def generate_po_number(invoice):
    ngay_hd_str = invoice.ngay_hd.strftime('%Y%m%d')
    last_po = PurchaseOrder.objects.filter(
        po_number__startswith=f"PN{ngay_hd_str}-"
    ).aggregate(Max('po_number'))['po_number__max']

    if last_po:
        last_number = int(last_po.split('-')[-1])
        next_number = last_number + 1
    else:
        next_number = 1

    return f"PN{ngay_hd_str}-{next_number:03d}"


def generate_pn(invoice: Invoice) -> str:
    ngay_str = (invoice.ngay_hd or timezone.now()).strftime('%Y%m%d')

    last_po = PurchaseOrder.objects.filter(
        po_number__startswith=f"PN{ngay_str}-"
    ).aggregate(Max('po_number'))['po_number__max']

    if last_po:
        last_index = int(last_po.split('-')[-1])
    else:
        last_index = 0

    return f"PN{ngay_str}-{last_index + 1:03d}"





def open_or_create_po(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    # --- 1. Tìm PO đã tồn tại ---
    po = PurchaseOrder.objects.filter(invoice=invoice).first()

    # --- 2. Lấy hoặc tạo Supplier ---
    supplier_instance, _ = Supplier.objects.get_or_create(
        ten_dv_ban = invoice.ten_dv_ban,
        defaults={
            "ma_so_thue": invoice.ma_so_thue or "",
            "dia_chi": invoice.dia_chi or ""
        }
    )

    # --- 3. Nếu chưa có PO thì tạo mới ---
    if not po:
        po_number = generate_pn(invoice)   # lấy số phiếu mới

        po = PurchaseOrder.objects.create(
            invoice=invoice,
            po_number=po_number,
            supplier=supplier_instance,                     # <-- FIX QUAN TRỌNG
            total_amount=Decimal(invoice.tong_tien or 0),
            total_tax=Decimal('0'),
            phan_loai_phieu='HH'
        )

        sync_po_items_from_invoice(po, invoice)
        messages.success(request, f"Đã tạo mới PO #{po.po_number} từ hóa đơn #{invoice.so_hoa_don}.")

    # --- 4. Nếu có rồi → chỉ sync lại items ---
    else:
        sync_po_items_from_invoice(po, invoice)
        messages.info(request, f"Đã đồng bộ lại PO #{po.po_number} theo hóa đơn #{invoice.so_hoa_don}.")

    # --- 5. Điều hướng ---
    return redirect('edit_purchase_order', po_id=po.id)

def to_decimal_safe(val, default=0):
    try:
        return Decimal(str(val).replace(',', ''))
    except (InvalidOperation, TypeError):
        return Decimal(default)






def edit_purchase_order(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    items = po.items.all()

    if request.method == 'POST':
        for item in items:
            # Lấy dữ liệu từ form
            sku = request.POST.get(f'sku_{item.id}', '').strip()
            ten_goi_chung = request.POST.get(f'ten_goi_chung_{item.id}', '').strip()
            
            # Decimal an toàn
            quantity = to_decimal_safe(request.POST.get(f'so_luong_{item.id}', item.quantity))
            so_luong_quy_doi = to_decimal_safe(request.POST.get(f'so_luong_quy_doi_{item.id}', getattr(item, 'so_luong_quy_doi', 0)))
            unit_price = to_decimal_safe(request.POST.get(f'don_gia_{item.id}', item.unit_price))
            tax_rate = to_decimal_safe(request.POST.get(f'thue_suat_field_{item.id}', item.thue_suat_field))
            chiet_khau = to_decimal_safe(request.POST.get(f'chiet_khau_{item.id}', getattr(item, 'chiet_khau', 0)))

            # ❗ LẤY TRỰC TIẾP từ object nếu đã có, không tính lại
            thanh_tien_truoc_ck = getattr(item, 'thanh_tien', quantity * unit_price)
            thanh_tien_sau_ck = getattr(item, 'thanh_tien_sau_ck', thanh_tien_truoc_ck - chiet_khau)
            tien_thue = getattr(item, 'tien_thue_field', (thanh_tien_sau_ck * tax_rate / Decimal(100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            thanh_toan = getattr(item, 'thanh_toan_field', (thanh_tien_sau_ck + tien_thue).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

            # Gán lại vào object
            item.sku = sku
            item.ten_goi_chung = ten_goi_chung
            item.quantity = quantity
            item.so_luong_quy_doi = so_luong_quy_doi
            item.unit_price = unit_price
            item.thue_suat_field = tax_rate
            item.chiet_khau = chiet_khau
            item.thanh_tien = thanh_tien_truoc_ck
            item.thanh_tien_sau_ck = thanh_tien_sau_ck
            item.tien_thue_field = tien_thue
            item.thanh_toan_field = thanh_toan

            item.save()

        # Cập nhật tổng PO
        po.total_amount = sum(i.thanh_tien for i in po.items.all())
        po.total_discount = sum(i.chiet_khau for i in po.items.all())
        po.total_tax = sum(i.tien_thue_field for i in po.items.all())
        po.total_final_amount = sum(i.thanh_toan_field for i in po.items.all())
        po.save()

        messages.success(request, "Đã lưu thay đổi phiếu nhập thành công.")
        return redirect("invoice_list")

    return render(request, "edit_po.html", {"po": po, "items": items})





# 🧩 Xem chi tiết PO
def purchase_order_detail(request, invoice_id):
    po = get_object_or_404(PurchaseOrder, invoice_id=invoice_id)
    items = po.items.all()
    return render(request, 'purchase_order_detail.html', {'po': po, 'items': items})


# 🧩 Tạo nhiều PO từ danh sách hóa đơn được chọn
def create_selected_invoices(request):
    """
    Tạo nhiều phiếu nhập từ danh sách các hóa đơn được chọn.
    """
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})

    invoice_ids = data.get('ids', [])
    created_count = 0
    updated_count = 0

    for inv_id in invoice_ids:
        invoice = Invoice.objects.filter(id=inv_id).first()
        if not invoice:
            continue

        # --- Lấy hoặc tạo Supplier ---
        supplier_instance, _ = Supplier.objects.get_or_create(
            ten_dv_ban=invoice.ten_dv_ban,
            defaults={
                'ma_so_thue': invoice.ma_so_thue or '',
                'dia_chi': invoice.dia_chi or ''
            }
        )

        # --- Tìm PO đã tồn tại ---
        po = PurchaseOrder.objects.filter(invoice=invoice).first()
        if not po:
            po_number = generate_pn(invoice)  # tạo số phiếu mới
            po = PurchaseOrder.objects.create(
                invoice=invoice,
                po_number=po_number,
                supplier=supplier_instance,
                total_amount=Decimal(invoice.tong_tien or 0),
                total_tax=Decimal('0'),
                phan_loai_phieu='HH'
            )
            created_count += 1
        else:
            updated_count += 1

        # --- Đồng bộ items ---
        sync_po_items_from_invoice(po, invoice)

    return JsonResponse({
        'success': True,
        'created_count': created_count,
        'updated_count': updated_count,
    })




from .utils import sync_fiscal_year
def purchase_order_list(request):
    # ---- AUTO SYNC NĂM ----
    current_year = sync_fiscal_year(request, PurchaseOrder)

    # ---- YEAR LIST (nguồn sự thật từ DB) ----
    year_range = PurchaseOrder.objects.aggregate(
        min_year=Min("fiscal_year"),
        max_year=Max("fiscal_year")
    )

    min_year = year_range["min_year"] or current_year
    max_year = year_range["max_year"] or current_year

    year_list = list(range(min_year, max_year + 1))

    # ---- DANH SÁCH PO ----
    po_list = (
        PurchaseOrder.objects
        .select_related("invoice")
        .filter(
            phan_loai_phieu__in=["HH", "PN"],
            fiscal_year=current_year
        )
        .order_by("-po_number")
    )

    # --- Tìm kiếm ---
    search_invoice = request.GET.get('invoice', '').strip()
    search_supplier = request.GET.get('supplier', '').strip()
    search_po_number = request.GET.get('po_number', '').strip()

    if search_invoice:
        po_list = po_list.filter(invoice__so_hoa_don__icontains=search_invoice)
    if search_supplier:
        po_list = po_list.filter(supplier__icontains=search_supplier)
    if search_po_number:
        po_list = po_list.filter(po_number__icontains=search_po_number)

    # --- Phân trang ---
    per_page = request.GET.get('per_page', 10)
    page_number = request.GET.get('page', 1)

    if per_page != 'all':
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10

    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1

    if per_page == 'all':
        paginator = None
        pos = po_list
        page_obj = None  # không có phân trang
    else:
        paginator = Paginator(po_list, per_page)
        page_obj = paginator.get_page(page_number)
        pos = page_obj

    # --- Tính tổng thanh toán ---
    for po in pos:
        bank_total = po.bankpayment_set.aggregate(total=Sum('amount'))['total'] or 0
        po.actual_payment = bank_total

    # --- Query params cho pagination ---
    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'pos': pos,                        # dùng cho table
        
        'label': 'phiếu nhập',
        'search_invoice': search_invoice,
        'search_supplier': search_supplier,
        'search_po_number': search_po_number,
        'page_obj': page_obj,              # dùng cho pagination
        'paginator': paginator,
        'per_page': per_page,
        'query_params': query_params.urlencode(),
        'current_year': current_year,
        'year_list': year_list,
    }

    return render(request, 'purchase_order_list.html', context)
