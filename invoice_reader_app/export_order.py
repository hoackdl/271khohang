# invoice_reader_app/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json
from django.db.models import Q, IntegerField, Case, When, Value, Sum, Min
from .model_invoice import Invoice, Supplier, InvoiceItem, Customer, ProductName

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime
import re
import unicodedata

from invoice_reader_app.models_purchaseorder import PurchaseOrder, PurchaseOrderItem, ActivityType
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from django.views.decorators.http import require_POST
from django.http import JsonResponse



@require_POST
def delete_all_px(request):
    # Xoá tất cả PurchaseOrder là PX
    PurchaseOrder.objects.filter(is_export=True).delete()
    return JsonResponse({"status": "success"})



def export_order_list(request):
    from django.db.models import IntegerField, Case, When, Value
    from django.db.models.functions import Cast

    current_year = request.session.get("fiscal_year", datetime.now().year)

    year_param = request.GET.get("year")
    if year_param:
        try:
            current_year = int(year_param)
            request.session["fiscal_year"] = current_year
        except ValueError:
            pass

    current_year = request.session.get("fiscal_year", datetime.now().year)

    year_range = (
        Invoice.objects
        .aggregate(
            min_year=Min("fiscal_year"),
            max_year=Max("fiscal_year")
        )
    )

    min_year = year_range["min_year"] or current_year
    max_year = year_range["max_year"] or current_year

    years = set(range(min_year, max_year + 1))
    years.add(current_year)
    year_list = sorted(years)

    # Danh sách phiếu xuất
    # --- Lấy phiếu xuất ---
    pos = PurchaseOrder.objects.select_related(
        'invoice',
        'activity_type'
    ).filter(
        phan_loai_phieu='PX',
        invoice__fiscal_year=current_year
    ).annotate(
        invoice_num_int=Case(
            When(invoice__so_hoa_don__regex=r'^\d+$',
                then=Cast('invoice__so_hoa_don', IntegerField())),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('-invoice_num_int')

    # --- GET parameters ---
    year_param = request.GET.get("year")
    if year_param:
        try:
            current_year = int(year_param)
            request.session["fiscal_year"] = current_year
        except ValueError:
            pass

    search = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    per_page = request.GET.get('per_page', '15').strip()

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

    # --- Tính tổng tiền hóa đơn ---
    total_tien = pos.aggregate(total=Sum('invoice__tong_tien'))['total'] or 0

    # --- Phân trang ---
    page_number = request.GET.get('page', 1)
    paginator = None

    if str(per_page).lower() != 'all':
        try:
            per_page_int = int(per_page)
        except ValueError:
            per_page_int = 20

        paginator = Paginator(pos, per_page_int)
        try:
            page_obj = paginator.get_page(page_number)
        except (EmptyPage, PageNotAnInteger):
            page_obj = paginator.get_page(1)
    else:
        page_obj = pos  # Trường hợp 'all'

    # Xử lý query params giữ filter khi phân trang
    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'pos': page_obj,            # dùng luôn page_obj cho template
        'data': pos,                # danh sách gốc
        'paginator': paginator,
        'per_page': per_page,
        'label': 'phiếu xuất',
        'search': search,
        'start_date': start_date,
        'end_date': end_date,
        'query_params': query_params.urlencode(),
        'total_tien': total_tien,  # tổng tiền
        'page_obj': page_obj,       # dùng cho pagination.html
        'current_year': current_year,
        'year_list': year_list,   # 👈 thêm
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
    invoice_id = request.POST.get("invoice_id") if request.method == "POST" else request.GET.get("invoice_id")

    if not invoice_id:
        messages.error(request, "Không tìm thấy ID hóa đơn.")
        return redirect('invoice_export_list')

    invoice = get_object_or_404(Invoice, id=invoice_id)

    # Kiểm tra đã có PX chưa
    existing_po = PurchaseOrder.objects.filter(invoice=invoice).first()
    if existing_po:
        messages.info(request, f"Hóa đơn này đã có phiếu xuất {existing_po.po_number}.")
        return redirect('export_order_detail', po_id=existing_po.id)

    # Tạo PX mới
    try:
        po = create_purchase_order_from_invoice(invoice)
        messages.success(request, f"Tạo phiếu xuất {po.po_number} thành công!")
        return redirect('export_order_detail', po_id=po.id)

    except Exception as e:
        messages.error(request, f"Lỗi: {str(e)}")
        return redirect('invoice_export_list')




from django.db.models import Max, IntegerField
from django.db.models.functions import Cast, Substr
from django.db.models import Max, IntegerField
from django.db.models.functions import Right, Cast
from datetime import datetime

from datetime import datetime

def generate_px_number(invoice_date, so_hoa_don):
    """
    Tạo số phiếu xuất dựa trên ngày hóa đơn và số hóa đơn.
    Định dạng: PX-YYYYMMDD-SOHD
    """
    if not invoice_date:
        invoice_date = datetime.today().date()

    date_str = invoice_date.strftime("%Y%m%d")
    
    # Loại bỏ ký tự đặc biệt trong số hóa đơn
    safe_sohd = ''.join(e for e in so_hoa_don if e.isalnum())

    return f"PX-{date_str}-{safe_sohd}"

# Bổ sung ký hiệu vào hàm phiếu xuất
from datetime import datetime

def generate_px_number(invoice_date, so_hoa_don, ky_hieu):
    """
    Tạo số phiếu xuất dựa trên:
    PX-YYYYMMDD-KYHIEU-SOHD

    Ví dụ:
    PX-20260107-C26TTA-00000001
    """

    if not invoice_date:
        invoice_date = datetime.today().date()

    date_str = invoice_date.strftime("%Y%m%d")

    # Loại bỏ ký tự đặc biệt
    safe_sohd = ''.join(c for c in str(so_hoa_don) if c.isalnum())
    safe_ky_hieu = ''.join(c for c in str(ky_hieu) if c.isalnum())

    return f"PX-{date_str}-{safe_ky_hieu}-{safe_sohd}"




from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from invoice_reader_app.purchase_oder import PurchaseOrder
from invoice_reader_app.activity_type_create import ActivityType
from invoice_reader_app.model_invoice import ProductName


def export_order_detail(request, po_id):

    po = get_object_or_404(
        PurchaseOrder.objects.select_related(
            "invoice",
            "activity_type",
        ),
        id=po_id,
    )

    items = po.items.all()

    total_amount = sum(
        item.total_price + item.tien_thue
        for item in items
    )

    activity_types = ActivityType.objects.filter(
        is_active=True
    ).order_by("code")

    # =====================================================
    # TỰ ĐỘNG XÁC ĐỊNH ACTIVITY THEO SKU
    # CHỈ QUERY ProductName 1 LẦN
    # =====================================================

    # Lấy toàn bộ SKU trong phiếu
    skus = {
        (item.sku or "").strip()
        for item in items
        if (item.sku or "").strip()
    }

    # Lấy toàn bộ ProductName tương ứng
    products = (
        ProductName.objects
        .select_related("activity_type")
        .filter(
            sku__in=skus
        )
    )

    # Tạo dictionary:
    # {
    #     "sku001": ProductName,
    #     "sku002": ProductName,
    # }
    product_by_sku = {
        (product.sku or "").strip().lower(): product
        for product in products
    }

    activity_map = {}
    sku_not_found = []
    sku_no_activity = []

    # Duyệt các dòng hàng
    for item in items:

        sku = (item.sku or "").strip()

        if not sku:
            continue

        product = product_by_sku.get(
            sku.lower()
        )

        # SKU chưa có trong danh mục
        if not product:
            sku_not_found.append(sku)
            continue

        # SKU có nhưng chưa gán Activity
        if not product.activity_type:
            sku_no_activity.append(sku)
            continue

        # Gom Activity
        activity = product.activity_type

        activity_map[activity.id] = activity


    # Danh sách Activity duy nhất
    detected_activities = list(
        activity_map.values()
    )
    # =====================================================
    # TỰ ĐỘNG GÁN ACTIVITY CHO PO
    # =====================================================

    if len(detected_activities) == 1:

        detected_activity = detected_activities[0]

        if po.activity_type_id != detected_activity.id:

            po.activity_type = detected_activity

            po.save(
                update_fields=["activity_type"]
            )


    # =====================================================
    # CÓ NHIỀU ACTIVITY
    # =====================================================

    elif len(detected_activities) > 1:

        messages.warning(
            request,
            "Phiếu xuất có nhiều loại hình hoạt động "
            "theo SKU. Vui lòng kiểm tra lại."
        )


    # =====================================================
    # SKU CHƯA CÓ TRONG DANH MỤC
    # =====================================================

    if sku_not_found:

        messages.warning(
            request,
            "SKU chưa có trong danh mục hàng hóa: "
            + ", ".join(sorted(set(sku_not_found)))
        )


    # =====================================================
    # SKU CHƯA GÁN ACTIVITY
    # =====================================================

    if sku_no_activity:

        messages.warning(
            request,
            "SKU chưa được gán loại hình hoạt động: "
            + ", ".join(sorted(set(sku_no_activity)))
        )

    # =====================================================
    # POST - CHO PHÉP CHỌN LẠI THỦ CÔNG
    # =====================================================

    if request.method == "POST":

        activity_type_id = request.POST.get(
            "activity_type"
        )

        if not activity_type_id:

            messages.error(
                request,
                "Vui lòng chọn loại hình kinh doanh."
            )

        else:

            try:

                activity = ActivityType.objects.get(
                    id=activity_type_id,
                    is_active=True,
                )

                po.activity_type = activity

                po.save(
                    update_fields=["activity_type"]
                )

                messages.success(
                    request,
                    "Đã lưu loại hình kinh doanh."
                )

                return redirect(
                    "export_order_detail",
                    po_id=po.id,
                )

            except ActivityType.DoesNotExist:

                messages.error(
                    request,
                    "Loại hình hoạt động không hợp lệ."
                )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {
        "po": po,
        "invoice": po.invoice,
        "items": items,
        "total_amount": total_amount,

        "activity_types": activity_types,

        # Activity được tự động nhận diện
        "detected_activities": detected_activities,

        # SKU chưa được khai báo
        "sku_not_found": sku_not_found,

        "show_save_button": True,
    }

    return render(
        request,
        "export_order_detail.html",
        context,
    )




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





def sync_invoice_from_po(po, invoice):
    """
    Đồng bộ SKU từ PO sang InvoiceItem
    """
    for po_item in po.items.all():
        invoice_item = invoice.items.filter(ten_hang=po_item.product_name).first()
        if invoice_item:
            invoice_item.sku = po_item.sku
            invoice_item.save()




def create_export_order_view(request):
    if request.method == "POST":
        # 1. Lấy hoặc tạo Customer
        mst = request.POST.get("mst") or "UNKNOWN"
        khach_hang = request.POST.get("khach_hang") or "Khách hàng tạm"
        dia_chi = request.POST.get("dia_chi") or ""

        customer, _ = Customer.objects.get_or_create(
            ma_so_thue=mst,
            defaults={"ten_khach_hang": khach_hang, "dia_chi": dia_chi}
        )

        # 2. Lấy số hóa đơn để tạo PO number
        so_hoa_don = request.POST.get("so_hoa_don") or "NOHD"
        ngay_hd_str = request.POST.get("ngay_hd")  # định dạng YYYY-MM-DD
        if ngay_hd_str:
            ngay_hd = timezone.datetime.strptime(ngay_hd_str, "%Y-%m-%d").date()
        else:
            ngay_hd = timezone.localdate()

        po_number = generate_px_number(ngay_hd, so_hoa_don)

        # 3. Tạo PO PX
        po = PurchaseOrder.objects.create(
            po_number=po_number,
            phan_loai_phieu='PX',
            customer=customer,
            invoice=None,
        )

        # 4. Tạo PO Items
        ten_hang_list = request.POST.getlist("ten_goi_chung[]")
        so_luong_list = request.POST.getlist("so_luong[]")
        don_gia_list = request.POST.getlist("don_gia[]")
        thue_suat_list = request.POST.getlist("thue_suat[]")
        sku_list = request.POST.getlist("sku[]")

        for i in range(len(ten_hang_list)):
            PurchaseOrderItem.objects.create(
                purchase_order=po,
                product_name=ten_hang_list[i],
                quantity=float(so_luong_list[i] or 0),
                unit_price=float(don_gia_list[i] or 0),
                thue_suat_field=float(thue_suat_list[i] or 0),
                sku=sku_list[i] or None,
                is_export=True
            )

        return redirect("export_order_detail", po_id=po.id)

    return render(request, "export_order_create.html")





def normalize(text):
    """Chuẩn hóa text: bỏ dấu, lowercase, xóa ký tự thừa"""
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-zA-Z0-9 ]+', ' ', text)
    return text.lower().strip()

def auto_match_sku(invoice_item_name):
    """Tự động map SKU dựa trên tên sản phẩm hoặc tên gọi chung"""
    if not invoice_item_name:
        return None

    raw = invoice_item_name.strip()
    norm_raw = normalize(raw)

    # 1️⃣ MATCH exact tên sản phẩm
    product = ProductName.objects.filter(ten_hang__iexact=raw).first()
    if product:
        return product.sku

    # 2️⃣ MATCH exact tên chuẩn hóa
    normalized_exact_matches = [p for p in ProductName.objects.all() if normalize(p.ten_hang) == norm_raw]
    if normalized_exact_matches:
        return normalized_exact_matches[0].sku

    # 3️⃣ MATCH theo tên gọi chung
    product = ProductName.objects.filter(ten_goi_chung__icontains=raw).first()
    if product:
        return product.sku

    return None



def create_purchase_order_from_invoice(invoice):
    # Kiểm tra nếu PO đã tồn tại
    existing_po = PurchaseOrder.objects.filter(invoice=invoice).first()
    if existing_po:
        return existing_po  # trả về PO đã tồn tại

    # --- phần tạo supplier và customer như hiện tại ---
    supplier = invoice.supplier or Supplier.objects.get_or_create(
        ma_so_thue=invoice.ma_so_thue,
        defaults={
            'ten_dv_ban': invoice.ten_dv_ban or 'UNKNOWN',
            'dia_chi': invoice.dia_chi or ''
        }
    )[0]

    if invoice.ma_so_thue_mua:
        customer, created = Customer.objects.get_or_create(
            ma_so_thue=invoice.ma_so_thue_mua,
            defaults={
                'ten_khach_hang': invoice.ten_nguoi_mua or 'Khách hàng',
                'dia_chi': invoice.dia_chi_mua or ''
            }
        )
    else:
        placeholder_mst = f"TEMP-{invoice.id}"
        customer, created = Customer.objects.get_or_create(
            ma_so_thue=placeholder_mst,
            defaults={
                'ten_khach_hang': invoice.ten_nguoi_mua or 'Khách hàng',
                'dia_chi': invoice.dia_chi_mua or ''
            }
        )

    po_number = generate_px_number(invoice.ngay_hd, invoice.so_hoa_don,invoice.ky_hieu)


    po = PurchaseOrder.objects.create(
        po_number=po_number,
        invoice=invoice,
        customer=customer,
        supplier=supplier,
        phan_loai_phieu="PX",
        total_amount=invoice.tong_tien_hang or 0,
        total_tax=invoice.tong_tien_thue or 0,
    )

    # Tạo PO Items
    po_items = []

    for item in invoice.items.all():
        total_price = Decimal(item.so_luong or 0) * Decimal(item.don_gia or 0)
        tien_thue = total_price * Decimal(item.thue_suat or 0) / Decimal(100)

        # 1. Dùng SKU có sẵn của invoice item nếu có
        sku = item.sku

        # 2. Nếu chưa có SKU, thử tự động map theo tên
        if not sku:
            sku = auto_match_sku(item.ten_hang)

        # 3. Nếu vẫn chưa có SKU, có thể tạo placeholder (tuỳ chọn)
        # sku = sku or f"TEMP-{item.id}"

        po_items.append(PurchaseOrderItem(
            purchase_order_id=po.id,
            product_name=item.ten_hang or 'UNKNOWN',
            quantity=item.so_luong or 0,
            so_luong_quy_doi=item.so_luong or 0,
            unit=item.dvt or '',
            unit_price=item.don_gia or 0,
            total_price=total_price,
            tien_thue_field=tien_thue,
            thue_suat_field=item.thue_suat or 0,
            thanh_tien=total_price,
            thanh_tien_sau_ck=item.thanh_toan or 0,
            chiet_khau=item.chiet_khau or 0,
            thanh_toan_field=item.thanh_toan or 0,
            ten_goi_chung=item.ten_goi_chung or '',
            sku=sku or '',  # hoặc sku=sku để giữ None nếu không muốn placeholder
            is_export=True
        ))


    PurchaseOrderItem.objects.bulk_create(po_items)

    return po


from django.db import transaction



def create_or_update_purchase_order_from_invoice(invoice):
    """
    Tạo hoặc cập nhật PurchaseOrder (PX) từ hóa đơn xuất.
    Quy tắc: 1 hóa đơn = 1 phiếu xuất, dùng so_hoa_don làm tham số chính.
    Luôn lấy tên khách hàng từ invoice.
    """
    with transaction.atomic():
        # --- Supplier ---
        supplier = invoice.supplier
        if not supplier:
            supplier, _ = Supplier.objects.get_or_create(
                ma_so_thue=invoice.ma_so_thue,
                defaults={
                    'ten_dv_ban': invoice.ten_dv_ban or 'UNKNOWN',
                    'dia_chi': invoice.dia_chi or ''
                }
            )

        # --- Customer ---
        if invoice.ma_so_thue_mua:
            customer, _ = Customer.objects.get_or_create(
                ma_so_thue=invoice.ma_so_thue_mua
            )
            # Luôn cập nhật tên từ invoice
            customer.ten_khach_hang = invoice.ten_nguoi_mua or 'Khách hàng'
            customer.dia_chi = invoice.dia_chi_mua or ''
            customer.save()
        else:
            placeholder_mst = f"TEMP-{invoice.id}"
            customer, _ = Customer.objects.get_or_create(
                ma_so_thue=placeholder_mst
            )
            customer.ten_khach_hang = invoice.ten_nguoi_mua or 'Khách lẻ'
            customer.dia_chi = invoice.dia_chi_mua or ''
            customer.save()

        # --- PO: dùng so_hoa_don làm chuẩn để tránh trùng ---
        po_number = generate_px_number(invoice.ngay_hd, invoice.so_hoa_don)

        po, created = PurchaseOrder.objects.get_or_create(
            po_number=po_number,  # lấy số hóa đơn làm key chính
            defaults={
                'invoice': invoice,
                'customer': customer,
                'supplier': supplier,
                'phan_loai_phieu': 'PX',
                'total_amount': invoice.tong_tien_hang or 0,
                'total_tax': invoice.tong_tien_thue or 0,
            }
        )

        if not created:
            # Cập nhật PO nếu đã tồn tại
            po.customer = customer
            po.supplier = supplier
            po.total_amount = invoice.tong_tien_hang or 0
            po.total_tax = invoice.tong_tien_thue or 0
            po.invoice = invoice
            po.save()
            po.items.all().delete()  # Xóa item cũ để tạo lại

        # --- Tạo POItem từ invoice.items ---
        po_items = []
        for item in invoice.items.all():
            total_price = Decimal(item.so_luong or 0) * Decimal(item.don_gia or 0)
            tien_thue = total_price * Decimal(item.thue_suat or 0) / Decimal(100)
            sku = item.sku or auto_match_sku(item.ten_hang)

            po_items.append(PurchaseOrderItem(
                purchase_order=po,
                product_name=item.ten_hang or 'UNKNOWN',
                quantity=item.so_luong or 0,
                so_luong_quy_doi=item.so_luong or 0,
                unit=item.dvt or '',
                unit_price=item.don_gia or 0,
                total_price=total_price,
                tien_thue_field=tien_thue,
                thue_suat_field=item.thue_suat or 0,
                thanh_tien=total_price,
                thanh_tien_sau_ck=item.thanh_toan or 0,
                chiet_khau=item.chiet_khau or 0,
                thanh_toan_field=item.thanh_toan or 0,
                ten_goi_chung=item.ten_goi_chung or '',
                sku=sku or '',
                is_export=True
            ))

        if po_items:
            PurchaseOrderItem.objects.bulk_create(po_items)

        return po

def save_po_sku(request, po_id):
    po = get_object_or_404(
    PurchaseOrder.objects.select_related(
    "invoice",
    "activity_type"
    ),
    id=po_id
    )

   
    invoice = po.invoice

    if not invoice:
        messages.error(
            request,
            "PO chưa có hóa đơn, không thể lưu!"
        )
        return redirect(
            "export_order_detail",
            po_id=po.id
        )

    if request.method == "POST":

        # ==========================================
        # 1. LƯU LOẠI HÌNH KINH DOANH
        # ==========================================
        activity_type_id = request.POST.get("activity_type")

        if not activity_type_id:
            messages.error(
                request,
                "Vui lòng chọn loại hình kinh doanh!"
            )
            return redirect(
                "export_order_detail",
                po_id=po.id
            )

        try:
            activity_type = ActivityType.objects.get(
                id=activity_type_id,
                is_active=True
            )
        except ActivityType.DoesNotExist:
            messages.error(
                request,
                "Loại hình kinh doanh không hợp lệ!"
            )
            return redirect(
                "export_order_detail",
                po_id=po.id
            )

        po.activity_type = activity_type
        po.save(update_fields=["activity_type"])


        # ==========================================
        # 2. LƯU SKU
        # ==========================================
        for invoice_item in invoice.items.all():

            field = f"sku_{invoice_item.id}"

            if field in request.POST:

                new_sku = request.POST[field].strip()

                # Cập nhật InvoiceItem
                invoice_item.sku = new_sku
                invoice_item.save(
                    update_fields=["sku"]
                )

                # Cập nhật PurchaseOrderItem tương ứng
                po_item = (
                    po.items
                    .filter(
                        product_name=invoice_item.ten_hang
                    )
                    .first()
                )

                if po_item:
                    po_item.sku = new_sku
                    po_item.save(
                        update_fields=["sku"]
                    )


        # ==========================================
        # 3. THÔNG BÁO
        # ==========================================
        messages.success(
            request,
            "Đã lưu phiếu xuất và loại hình kinh doanh thành công!"
        )

        
        return redirect("export_order_list")
        

    return redirect(
        "export_order_detail",
        po_id=po.id
    )


def create_purchase_order_from_invoice(invoice):
    # Kiểm tra nếu PO đã tồn tại
    existing_po = PurchaseOrder.objects.filter(invoice=invoice).first()
    if existing_po:
        return existing_po  # trả về PO đã tồn tại

    # --- Tạo supplier ---
    supplier = invoice.supplier or Supplier.objects.get_or_create(
        ma_so_thue=invoice.ma_so_thue,
        defaults={
            'ten_dv_ban': invoice.ten_dv_ban or 'UNKNOWN',
            'dia_chi': invoice.dia_chi or ''
        }
    )[0]

    # --- Tạo customer ---
    if invoice.ma_so_thue_mua:
        customer, created = Customer.objects.get_or_create(
            ma_so_thue=invoice.ma_so_thue_mua,
            defaults={
                'ten_khach_hang': invoice.ten_nguoi_mua or 'Khách hàng',
                'dia_chi': invoice.dia_chi_mua or ''
            }
        )
    else:
        placeholder_mst = f"TEMP-{invoice.id}"

        customer, created = Customer.objects.get_or_create(
            ma_so_thue=placeholder_mst,
            defaults={
                'ten_khach_hang': invoice.ten_nguoi_mua or 'Khách hàng',
                'dia_chi': invoice.dia_chi_mua or ''
            }
        )

    # --- Sinh số phiếu xuất ---
    po_number = generate_px_number(
        invoice.ngay_hd,
        invoice.so_hoa_don,
        invoice.ky_hieu
    )

    # ==========================================
    # TẠO PHIẾU XUẤT
    # ==========================================
    po = PurchaseOrder.objects.create(
        po_number=po_number,
        invoice=invoice,
        customer=customer,
        supplier=supplier,

        # QUAN TRỌNG
        is_export=True,
        phan_loai_phieu="PX",

        total_amount=invoice.tong_tien_hang or 0,
        total_tax=invoice.tong_tien_thue or 0,
    )

    # ==========================================
    # TẠO PO ITEMS
    # ==========================================
    po_items = []

    for item in invoice.items.all():

        total_price = (
            Decimal(item.so_luong or 0)
            * Decimal(item.don_gia or 0)
        )

        tien_thue = (
            total_price
            * Decimal(item.thue_suat or 0)
            / Decimal(100)
        )

        # 1. Dùng SKU có sẵn
        sku = item.sku

        # 2. Nếu chưa có SKU thì tự động map
        if not sku:
            sku = auto_match_sku(item.ten_hang)

        po_items.append(
            PurchaseOrderItem(
                purchase_order_id=po.id,
                product_name=item.ten_hang or 'UNKNOWN',
                quantity=item.so_luong or 0,
                so_luong_quy_doi=item.so_luong or 0,
                unit=item.dvt or '',
                unit_price=item.don_gia or 0,
                total_price=total_price,
                tien_thue_field=tien_thue,
                thue_suat_field=item.thue_suat or 0,
                thanh_tien=total_price,
                thanh_tien_sau_ck=item.thanh_toan or 0,
                chiet_khau=item.chiet_khau or 0,
                thanh_toan_field=item.thanh_toan or 0,
                ten_goi_chung=item.ten_goi_chung or '',
                sku=sku or '',
                is_export=True,
            )
        )

    PurchaseOrderItem.objects.bulk_create(po_items)

    return po



def create_purchase_order_from_invoice(invoice):
    # ==========================================
    # KIỂM TRA PO ĐÃ TỒN TẠI
    # ==========================================
    existing_po = PurchaseOrder.objects.filter(
        invoice=invoice,
        is_export=True,
        phan_loai_phieu="PX"
    ).first()

    if existing_po:
        # Đồng bộ trạng thái Invoice
        if not invoice.da_tao_px:
            invoice.da_tao_px = True
            invoice.save(update_fields=["da_tao_px"])

        return existing_po

    # ==========================================
    # TẠO SUPPLIER
    # ==========================================
    supplier = invoice.supplier or Supplier.objects.get_or_create(
        ma_so_thue=invoice.ma_so_thue,
        defaults={
            'ten_dv_ban': invoice.ten_dv_ban or 'UNKNOWN',
            'dia_chi': invoice.dia_chi or ''
        }
    )[0]

    # ==========================================
    # TẠO CUSTOMER
    # ==========================================
    if invoice.ma_so_thue_mua:
        customer, created = Customer.objects.get_or_create(
            ma_so_thue=invoice.ma_so_thue_mua,
            defaults={
                'ten_khach_hang': invoice.ten_nguoi_mua or 'Khách hàng',
                'dia_chi': invoice.dia_chi_mua or ''
            }
        )
    else:
        placeholder_mst = f"TEMP-{invoice.id}"

        customer, created = Customer.objects.get_or_create(
            ma_so_thue=placeholder_mst,
            defaults={
                'ten_khach_hang': invoice.ten_nguoi_mua or 'Khách hàng',
                'dia_chi': invoice.dia_chi_mua or ''
            }
        )

    # ==========================================
    # SINH SỐ PHIẾU XUẤT
    # ==========================================
    po_number = generate_px_number(
        invoice.ngay_hd,
        invoice.so_hoa_don,
        invoice.ky_hieu
    )

    # ==========================================
    # TẠO PHIẾU XUẤT
    # ==========================================
    po = PurchaseOrder.objects.create(
        po_number=po_number,
        invoice=invoice,
        customer=customer,
        supplier=supplier,

        is_export=True,
        phan_loai_phieu="PX",

        total_amount=invoice.tong_tien_hang or 0,
        total_tax=invoice.tong_tien_thue or 0,
    )

    # ==========================================
    # TẠO PO ITEMS
    # ==========================================
    po_items = []

    for item in invoice.items.all():

        total_price = (
            Decimal(item.so_luong or 0)
            * Decimal(item.don_gia or 0)
        )

        tien_thue = (
            total_price
            * Decimal(item.thue_suat or 0)
            / Decimal(100)
        )

        sku = item.sku

        if not sku:
            sku = auto_match_sku(item.ten_hang)

        po_items.append(
            PurchaseOrderItem(
                purchase_order_id=po.id,
                product_name=item.ten_hang or 'UNKNOWN',
                quantity=item.so_luong or 0,
                so_luong_quy_doi=item.so_luong or 0,
                unit=item.dvt or '',
                unit_price=item.don_gia or 0,
                total_price=total_price,
                tien_thue_field=tien_thue,
                thue_suat_field=item.thue_suat or 0,
                thanh_tien=total_price,
                thanh_tien_sau_ck=item.thanh_toan or 0,
                chiet_khau=item.chiet_khau or 0,
                thanh_toan_field=item.thanh_toan or 0,
                ten_goi_chung=item.ten_goi_chung or '',
                sku=sku or '',
                is_export=True,
            )
        )

    PurchaseOrderItem.objects.bulk_create(po_items)

    # ==========================================
    # ĐÁNH DẤU INVOICE ĐÃ TẠO PX
    # ==========================================
    invoice.da_tao_px = True
    invoice.save(update_fields=["da_tao_px"])

    return po

def generate_po_from_invoice(request):
    invoice_id = (
        request.POST.get("invoice_id")
        if request.method == "POST"
        else request.GET.get("invoice_id")
    )

    if not invoice_id:
        messages.error(request, "Không tìm thấy ID hóa đơn.")
        return redirect('invoice_export_list')

    invoice = get_object_or_404(Invoice, id=invoice_id)

    # ==========================================
    # ĐÃ TẠO PX
    # ==========================================
    if invoice.da_tao_px:
        existing_po = PurchaseOrder.objects.filter(
            invoice=invoice,
            is_export=True,
            phan_loai_phieu="PX"
        ).first()

        if existing_po:
            messages.info(
                request,
                f"Hóa đơn này đã có phiếu xuất {existing_po.po_number}."
            )
            return redirect(
                'export_order_detail',
                po_id=existing_po.id
            )

        messages.warning(
            request,
            "Hóa đơn này đã từng tạo phiếu xuất nhưng hiện không còn liên kết với phiếu xuất."
        )
        return redirect('invoice_export_list')

    # ==========================================
    # TẠO PX
    # ==========================================
    try:
        po = create_purchase_order_from_invoice(invoice)

        messages.success(
            request,
            f"Tạo phiếu xuất {po.po_number} thành công!"
        )

        return redirect(
            'export_order_detail',
            po_id=po.id
        )

    except Exception as e:
        messages.error(
            request,
            f"Lỗi: {str(e)}"
        )
        return redirect('invoice_export_list')


from django.db import transaction
from decimal import Decimal


@transaction.atomic
def create_purchase_order_from_invoice(invoice):

    # ==========================================
    # KIỂM TRA PO ĐÃ TỒN TẠI
    # ==========================================
    existing_po = PurchaseOrder.objects.filter(
        invoice=invoice,
        is_export=True,
        phan_loai_phieu="PX"
    ).first()

    if existing_po:
        if not invoice.da_tao_px:
            invoice.da_tao_px = True
            invoice.save(update_fields=["da_tao_px"])

        return existing_po

    # ==========================================
    # TẠO SUPPLIER
    # ==========================================
    supplier = invoice.supplier or Supplier.objects.get_or_create(
        ma_so_thue=invoice.ma_so_thue,
        defaults={
            'ten_dv_ban': invoice.ten_dv_ban or 'UNKNOWN',
            'dia_chi': invoice.dia_chi or ''
        }
    )[0]

    # ==========================================
    # TẠO CUSTOMER
    # ==========================================
    if invoice.ma_so_thue_mua:
        customer, created = Customer.objects.get_or_create(
            ma_so_thue=invoice.ma_so_thue_mua,
            defaults={
                'ten_khach_hang': invoice.ten_nguoi_mua or 'Khách hàng',
                'dia_chi': invoice.dia_chi_mua or ''
            }
        )
    else:
        placeholder_mst = f"TEMP-{invoice.id}"

        customer, created = Customer.objects.get_or_create(
            ma_so_thue=placeholder_mst,
            defaults={
                'ten_khach_hang': invoice.ten_nguoi_mua or 'Khách hàng',
                'dia_chi': invoice.dia_chi_mua or ''
            }
        )

    # ==========================================
    # SINH SỐ PHIẾU XUẤT
    # ==========================================
    po_number = generate_px_number(
        invoice.ngay_hd,
        invoice.so_hoa_don,
        invoice.ky_hieu
    )

    # ==========================================
    # TẠO PHIẾU XUẤT
    # ==========================================
    po = PurchaseOrder.objects.create(
        po_number=po_number,
        invoice=invoice,
        customer=customer,
        supplier=supplier,
        is_export=True,
        phan_loai_phieu="PX",
        total_amount=invoice.tong_tien_hang or 0,
        total_tax=invoice.tong_tien_thue or 0,
    )

    # ==========================================
    # TẠO PO ITEMS
    # ==========================================
    po_items = []

    for item in invoice.items.all():

        total_price = (
            Decimal(item.so_luong or 0)
            * Decimal(item.don_gia or 0)
        )

        tien_thue = (
            total_price
            * Decimal(item.thue_suat or 0)
            / Decimal(100)
        )

        sku = item.sku

        if not sku:
            sku = auto_match_sku(item.ten_hang)

        po_items.append(
            PurchaseOrderItem(
                purchase_order_id=po.id,
                product_name=item.ten_hang or 'UNKNOWN',
                quantity=item.so_luong or 0,
                so_luong_quy_doi=item.so_luong or 0,
                unit=item.dvt or '',
                unit_price=item.don_gia or 0,
                total_price=total_price,
                tien_thue_field=tien_thue,
                thue_suat_field=item.thue_suat or 0,
                thanh_tien=total_price,
                thanh_tien_sau_ck=item.thanh_toan or 0,
                chiet_khau=item.chiet_khau or 0,
                thanh_toan_field=item.thanh_toan or 0,
                ten_goi_chung=item.ten_goi_chung or '',
                sku=sku or '',
                is_export=True,
            )
        )

    PurchaseOrderItem.objects.bulk_create(po_items)

    # ==========================================
    # ĐÁNH DẤU ĐÃ TẠO PX
    # ==========================================
    invoice.da_tao_px = True
    invoice.save(update_fields=["da_tao_px"])

    return po
