# invoice_reader_app/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json
from .model_invoice import Invoice
from .models_purcharoder import PurchaseOrder
from django.utils import timezone
from django.db.models import Q, Exists, OuterRef
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime

def export_order_list(request):
    from django.db.models import IntegerField, Case, When, Value
    from django.db.models.functions import Cast
    # Danh sách phiếu xuất
    # --- Lấy phiếu xuất ---
    pos = PurchaseOrder.objects.filter(
        phan_loai_phieu='PX'
    ).annotate(
        # Ép số phiếu (po_number) sang số nguyên an toàn
        po_num_int=Case(
            When(po_number__regex=r'^\d+$', then=Cast('po_number', IntegerField())),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('-created_at', '-po_num_int')   # Sắp xếp giảm dần

    # --- GET parameters ---
    search = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    per_page = request.GET.get('per_page', '10').strip()

    # Hàm parse ngày
    def parse_date(date_str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    # --- Lọc search ---
    if search:
        pos = pos.filter(
            Q(po_number__icontains=search) |
            Q(invoice__ten_nguoi_mua__icontains=search) |
            Q(invoice__ma_so_thue_mua__icontains=search)
        )

    # --- Lọc ngày ---
    if start_date:
        d = parse_date(start_date)
        if d:
            pos = pos.filter(created_at__date__gte=d)

    if end_date:
        d = parse_date(end_date)
        if d:
            pos = pos.filter(created_at__date__lte=d)

    # --- Phân trang ---
    page_number = request.GET.get('page', 1)
    if per_page.lower() == 'all':
        paginated_pos = pos
        page_number = None
    else:
        try:
            per_page_int = int(per_page)
        except ValueError:
            per_page_int = 10

        paginator = Paginator(pos, per_page_int)
        try:
            paginated_pos = paginator.get_page(page_number)
        except (EmptyPage, PageNotAnInteger):
            paginated_pos = paginator.get_page(1)

    context = {
        'pos': paginated_pos,
        'search': search,
        'start_date': start_date,
        'end_date': end_date,
        'per_page': per_page,
        'page_number': page_number,
    }

    return render(request, 'export_order_list.html', context)







@require_POST
def delete_selected_export_orders(request):
    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        PurchaseOrder.objects.filter(id__in=ids).delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def delete_export_order(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    po.delete()
    messages.success(request, f"Đã xoá phiếu xuất {po.po_number}")
    return redirect('export_order_list')

def generate_po_from_invoice(request):
    if request.method == "POST":
        invoice_id = request.POST.get("invoice_id")
    elif request.method == "GET":
        invoice_id = request.GET.get("invoice_id")
    else:
        return redirect('invoice_export_list')

    invoice = get_object_or_404(Invoice, id=invoice_id)

    existing_po = PurchaseOrder.objects.filter(invoice=invoice).first()
    if existing_po:
        messages.info(request, f"Hóa đơn này đã có phiếu xuất {existing_po.po_number}.")
        return redirect('export_order_detail', po_id=existing_po.id)

    try:
        po = create_purchase_order_from_invoice(invoice)
        messages.success(request, f"Tạo phiếu xuất {po.po_number} thành công!")
        return redirect('export_order_detail', po_id=po.id)
    except Exception as e:
        messages.error(request, f"Lỗi: {str(e)}")
        return redirect('invoice_export_list')

        
from .models_purcharoder import PurchaseOrderItem, ProductName
def auto_match_sku(invoice_item_name):
    if not invoice_item_name:
        return None

    raw = invoice_item_name.strip()

    # 1. match đúng 100%
    product = ProductName.objects.filter(
        ten_hang__iexact=raw
    ).first()
    if product:
        return product

    # 2. match gần đúng
    product = ProductName.objects.filter(
        Q(ten_hang__icontains=raw) |
        Q(ten_goi_chung__icontains=raw)
    ).first()
    if product:
        return product

    # 3. match từng từ
    tokens = raw.split()
    q = Q()
    for t in tokens:
        q &= Q(ten_hang__icontains=t)
    product = ProductName.objects.filter(q).first()
    if product:
        return product

    return None

from django.db import IntegrityError
from django.utils import timezone

def generate_unique_po_number():
    today = timezone.localdate()
    date_str = today.strftime("%Y%m%d")
    seq_number = 1

    while True:
        po_number = f"PX{date_str}-{str(seq_number).zfill(3)}"
        if not PurchaseOrder.objects.filter(po_number=po_number).exists():
            return po_number
        seq_number += 1
def create_purchase_order_from_invoice(invoice, created_at=None):
    """
    Tạo PO từ hóa đơn, có thể set ngày tạo theo invoice.ngay_hoa_don
    """
    if created_at is None:
        created_at = invoice.ngay_hd or timezone.now()  # fallback nếu invoice chưa có ngày

    # --- 1. Tạo PO_NUMBER duy nhất ---
    po_number = generate_unique_po_number()

    # --- 2. Tạo PO xuất kho ---
    po = PurchaseOrder.objects.create(
        invoice=invoice,
        po_number=po_number,
        phan_loai_phieu="PX",
        supplier=invoice.ten_dv_ban,
        created_at=created_at,
        
    )

    # --- 3. Tạo các dòng POItem ---
    for item in invoice.items.all():
        matched = auto_match_sku(item.ten_hang)

        if matched:
            sku = matched.sku
            ten_goi_chung = matched.ten_goi_chung
        else:
            sku = ""
            ten_goi_chung = item.ten_hang

        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product_name=item.ten_hang,
            quantity=item.so_luong,
            unit=item.dvt,
            unit_price=item.don_gia,
            thue_suat_field=item.thue_suat,
            sku=sku,
            ten_goi_chung=ten_goi_chung,
            is_export=True
        )

    return po



def export_order_detail(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    total_amount = sum(item.total_price + item.tien_thue for item in po.items.all())

    context = {
        'po': po,
        'invoice': po.invoice,
        'items': po.items.all(),
        'total_amount': total_amount,
        'show_save_button': True,  # <-- thêm cờ này
    }
    return render(request, 'export_order_detail.html', context)


def save_po_sku(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    invoice = po.invoice

    if not invoice:
        messages.error(request, "PO chưa có hóa đơn, không thể lưu SKU!")
        return redirect("export_order_detail", po_id=po.id)

    if request.method == "POST":
        for invoice_item in invoice.items.all():
            field = f"sku_{invoice_item.id}"
            if field in request.POST:
                new_sku = request.POST[field].strip()

                # Cập nhật InvoiceItem
                invoice_item.sku = new_sku
                invoice_item.save()

                # Cập nhật PurchaseOrderItem tương ứng
                po_item = po.items.filter(product_name=invoice_item.ten_hang).first()
                if po_item:
                    po_item.sku = new_sku
                    po_item.save()

        messages.success(request, "Đã lưu SKU thành công!")
        return redirect("export_order_list")


from django.utils import timezone
from .model_invoice import Customer, ProductName
from .models_purcharoder import PurchaseOrder, PurchaseOrderItem
from decimal import Decimal

def create_po_without_invoice(items_data, customer_mst=None, customer_name=None):
    """
    items_data: list dict chứa {ten_hang, so_luong, dvt, don_gia, thue_suat, sku (tuỳ chọn)}
    customer_mst: MST khách hàng, nếu có
    customer_name: tên khách hàng, nếu MST không tìm thấy
    """

    # --- 1. Lấy hoặc tạo Customer ---
    customer = None
    if customer_mst:
        customer = Customer.objects.filter(ma_so_thue=customer_mst).first()

    if not customer:
        mst = customer_mst or "UNKNOWN"
        name = customer_name or "Khách hàng tạm"
        customer = Customer.objects.create(
            ma_so_thue=mst,
            ten_khach_hang=name,
            dia_chi=""
        )

    # --- 2. Tạo PO ---
    today = timezone.localdate()
    date_str = today.strftime("%Y%m%d")
    today_pos = PurchaseOrder.objects.filter(created_at__date=today)
    seq_number = today_pos.count() + 1
    seq_str = str(seq_number).zfill(3)
    po_number = f"PX{date_str}-{seq_str}"

    po = PurchaseOrder.objects.create(
        po_number=po_number,
        phan_loai_phieu="PX",
        supplier=customer.ten_khach_hang,
        invoice=None  # cần model cho phép NULL
    )

    # --- 3. Tạo các PO Item ---
    for item in items_data or []:
        sku = item.get('sku')
        if not sku:
            p = ProductName.objects.filter(ten_hang__iexact=item['ten_hang']).first()
            if p:
                sku = p.sku

        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product_name=item['ten_hang'],
            quantity=item['so_luong'],
            unit=item['dvt'],
            unit_price=item['don_gia'],
            thue_suat_field=item.get('thue_suat', 0),
            sku=sku,
            is_export=True
        )

    return po


def sync_invoice_from_po(po, invoice):
    """
    Đồng bộ SKU từ PO sang InvoiceItem
    """
    for po_item in po.items.all():
        invoice_item = invoice.items.filter(ten_hang=po_item.product_name).first()
        if invoice_item:
            invoice_item.sku = po_item.sku
            invoice_item.save()
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

# invoice_reader_app/views.py
from django.shortcuts import render, redirect
from django.utils import timezone
from .models_purcharoder import PurchaseOrder, PurchaseOrderItem
from .model_invoice import Customer
from django.shortcuts import render, redirect
from django.utils import timezone
from .models_purcharoder import PurchaseOrder, PurchaseOrderItem
from .model_invoice import Customer

def create_export_order_view(request):
    if request.method == "POST":
        # --- 1. Thông tin khách hàng ---
        mst = request.POST.get("mst") or "UNKNOWN"
        khach_hang = request.POST.get("khach_hang") or "Khách hàng tạm"
        dia_chi = request.POST.get("dia_chi") or ""

        # Lấy hoặc tạo Customer
        customer = Customer.objects.filter(ma_so_thue=mst).first()
        if not customer:
            customer = Customer.objects.create(
                ma_so_thue=mst,
                ten_khach_hang=khach_hang,
                dia_chi=dia_chi
            )

        # --- 2. Tạo PO ---
        today = timezone.localdate()
        date_str = today.strftime("%Y%m%d")
        today_pos = PurchaseOrder.objects.filter(created_at__date=today)
        seq_number = today_pos.count() + 1
        po_number = f"PX{date_str}-{str(seq_number).zfill(3)}"

        po = PurchaseOrder.objects.create(
            po_number=po_number,
            phan_loai_phieu="PX",
            supplier=customer.ten_khach_hang,
            invoice=None  # PO chưa có hóa đơn
        )

        # --- 3. Lấy danh sách items ---
        ten_hang_list = request.POST.getlist("ten_goi_chung[]")
        so_luong_list = request.POST.getlist("so_luong[]")
        don_gia_list = request.POST.getlist("don_gia[]")
        thue_suat_list = request.POST.getlist("thue_suat[]")
        sku_list = request.POST.getlist("sku[]")

        # --- 4. Tạo PO Items với tính toán tiền ---
        for i in range(len(ten_hang_list)):
            ten_hang = ten_hang_list[i]
            so_luong = float(so_luong_list[i] or 0)
            don_gia = float(don_gia_list[i] or 0)
            thue_suat = float(thue_suat_list[i] or 0)
            sku = sku_list[i] or None

            thanh_tien = so_luong * don_gia
            tien_thue = thanh_tien * thue_suat / 100

            PurchaseOrderItem.objects.create(
                purchase_order=po,
                product_name=ten_hang,
                quantity=so_luong,
                unit_price=don_gia,
                thue_suat_field=thue_suat,
                sku=sku,
                is_export=True
            )

        # --- 5. Redirect sang chi tiết PO ---
        return redirect("export_order_detail", po_id=po.id)

    # GET request: hiển thị form
    return render(request, "export_order_create.html")
