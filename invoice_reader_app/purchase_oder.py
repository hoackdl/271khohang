from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
import json
from django.db.models import Max
from .models_purcharoder import PurchaseOrder, PurchaseOrderItem
from invoice_reader_app.model_invoice import Invoice, ProductName
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from decimal import Decimal, ROUND_HALF_UP
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from .models_purcharoder import PurchaseOrderItem
from invoice_reader_app.model_invoice import ProductName
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def normalize_tax(raw_tax):
    """
    Chuẩn hóa thuế suất.
    Hỗ trợ các dạng: 8, "8", "8%", 0.08, "0.08", None
    Trả về Decimal(8)
    """
    if raw_tax is None:
        return Decimal("0")

    # Chuyển về chuỗi
    raw = str(raw_tax).strip()

    # Nếu có ký tự % -> loại bỏ
    raw = raw.replace("%", "")

    # Nếu dạng thập phân (0.08) → chuyển thành 8
    try:
        value = Decimal(raw)
        if value < 1:
            value = value * 100
        return value.quantize(Decimal("0.01"))
    except:
        return Decimal("0")


def sync_po_items_from_invoice(po, invoice):
    items = invoice.items.all()
    if not items.exists():
        return False

    with transaction.atomic():
        po.items.all().delete()

        for item in items:
            product = ProductName.objects.filter(ten_hang__iexact=item.ten_hang).first()
            sku = item.sku or (product.sku if product else "")
            ten_goi_chung = item.ten_goi_chung or (product.ten_goi_chung if product else "")

            quantity = Decimal(item.so_luong or 0)
            unit_price = Decimal(item.don_gia or 0)
            total_price = quantity * unit_price

            # Chuẩn hóa thuế suất
            raw_tax = item.thue_suat
            tax_rate = normalize_tax(raw_tax)

            tien_thue = (total_price * tax_rate / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            PurchaseOrderItem.objects.create(
                purchase_order=po,
                product_name=item.ten_hang,
                quantity=quantity,
                unit=item.dvt,
                unit_price=unit_price,
                total_price=total_price,
                thue_suat_field=tax_rate,  # Lưu lại dạng %
                tien_thue_field=tien_thue,
                sku=sku,
                ten_goi_chung=ten_goi_chung
            )

    # Cập nhật tổng cộng
    po.total_amount = sum(i.total_price for i in po.items.all())
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



def generate_pn(invoice):
    # Lấy ngày hóa đơn dạng YYYYMMDD
    ngay_hd_str = invoice.ngay_hd.strftime('%Y%m%d')

    # Tìm số thứ tự lớn nhất trong cùng ngày
    last_pn = PurchaseOrder.objects.filter(
        invoice__ngay_hd=invoice.ngay_hd,
        po_number__startswith=f"PN{ngay_hd_str}-"
    ).aggregate(Max('po_number'))['po_number__max']

    if last_pn:
        last_number = int(last_pn.split('-')[-1])
        next_number = last_number + 1
    else:
        next_number = 1

    # Tạo PO mới
    po_number = f"PN{ngay_hd_str}-{next_number:03d}"
    return po_number


def open_or_create_po(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    po = PurchaseOrder.objects.filter(invoice=invoice).first()

    if not po:
        po_number = generate_pn(invoice)  # <-- Lấy số PO mới

        po = PurchaseOrder.objects.create(
            invoice=invoice,
            po_number=po_number,
            supplier=invoice.ten_dv_ban,
            total_amount=Decimal(invoice.tong_tien or 0),
            total_tax=Decimal('0'),
            phan_loai_phieu='HH'
        )
        sync_po_items_from_invoice(po, invoice)
        messages.success(request, f"Đã tạo mới PO #{po.po_number} từ hóa đơn #{invoice.so_hoa_don}.")
    else:
        sync_po_items_from_invoice(po, invoice)
        messages.info(request, f"Đã đồng bộ lại PO #{po.po_number} theo hóa đơn #{invoice.so_hoa_don}.")

    return redirect('edit_purchase_order', po_id=po.id)




# 🧩 Chỉnh sửa PO (form giao diện)
from decimal import Decimal, InvalidOperation
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from .models_purcharoder import PurchaseOrder, PurchaseOrderItem

from decimal import Decimal, InvalidOperation
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from .models_purcharoder import PurchaseOrder, PurchaseOrderItem

from decimal import Decimal, InvalidOperation
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from .models_purcharoder import PurchaseOrder, PurchaseOrderItem

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
    Tạo nhiều phiếu nhập từ danh sách các hóa đơn được chọn (gửi bằng JSON).
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

        po = PurchaseOrder.objects.filter(invoice=invoice).first()
        if not po:
            po_number = f"PO{timezone.now().strftime('%y%m%d')}{invoice.id:05d}"
            po = PurchaseOrder.objects.create(
                invoice=invoice,
                po_number=po_number,
                supplier=invoice.ten_dv_ban,
                total_amount=Decimal(invoice.tong_tien or 0),
                total_tax=Decimal('0'),
            )
            created_count += 1
        else:
            updated_count += 1

        sync_po_items_from_invoice(po, invoice)

    return JsonResponse({
        'success': True,
        'created_count': created_count,
        'updated_count': updated_count,
    })



from django.db.models import Sum


def purchase_order_list(request):
    """
    Hiển thị danh sách phiếu nhập loại 'HH' với tìm kiếm, phân trang
    và tổng thanh toán thực tế từ BankPayment
    """
    po_list = PurchaseOrder.objects.select_related('invoice') \
        .filter(phan_loai_phieu='HH') \
        .order_by('-po_number')

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

    if per_page == 'all':
        paginator = None
        pos = po_list  # không phân trang
    else:
        paginator = Paginator(po_list, per_page)
        pos = paginator.get_page(page_number)

    # --- Tính tổng thanh toán ---
    for po in pos:
        po.total_payment = po.total_amount + po.total_tax
        bank_total = po.bankpayment_set.aggregate(total=Sum('amount'))['total'] or 0
        po.actual_payment = bank_total

    # --- Query params cho pagination ---
    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'pos': pos,
        'data': pos,                      # để dùng chung component pagination.html
        'paginator': paginator,
        'per_page': per_page,

        # Label cho pagination (hiển thị "Tổng X phiếu nhập")
        'label': 'phiếu nhập',

        # input search
        'search_invoice': search_invoice,
        'search_supplier': search_supplier,
        'search_po_number': search_po_number,

        'query_params': query_params.urlencode(),
    }

    return render(request, 'purchase_order_list.html', context)
