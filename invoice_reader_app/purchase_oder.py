from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.utils.dateparse import parse_date

import json
from django.db.models import Max
from invoice_reader_app.models_purchaseorder import PurchaseOrder, PurchaseOrderItem, ActivityType
from invoice_reader_app.model_invoice import Invoice, ProductName, Supplier
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
from django.db.models import Sum, F, FloatField
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.db.models import Sum
from django.core.paginator import Paginator
from datetime import datetime
from django.db.models import Min, Max
from invoice_reader_app.utils.sync_fiscal_year import sync_fiscal_year
from django.contrib.auth.decorators import login_required


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

@login_required
def open_or_create_po(request, invoice_id):

    invoice = get_object_or_404(
        Invoice,
        id=invoice_id
    )

    # =========================================================
    # 1. XÁC ĐỊNH NĂM TÀI CHÍNH
    # =========================================================

    fiscal_year = invoice.fiscal_year

    # Nếu Invoice chưa có fiscal_year
    # thì lấy theo ngày hóa đơn
    if not fiscal_year and invoice.ngay_hd:

        fiscal_year = invoice.ngay_hd.year

        invoice.fiscal_year = fiscal_year

        invoice.save(
            update_fields=["fiscal_year"]
        )

    # Không xác định được năm
    if not fiscal_year:

        messages.error(
            request,
            f"Hóa đơn #{invoice.so_hoa_don} "
            "không có ngày hóa đơn để xác định năm tài chính."
        )

        return redirect("invoice_list")

    # =========================================================
    # 2. LẤY / TẠO SUPPLIER
    # =========================================================

    supplier_instance = invoice.supplier

    if not supplier_instance:

        supplier_instance, _ = (
            Supplier.objects.update_or_create(
                ma_so_thue=invoice.ma_so_thue,
                defaults={
                    "ten_dv_ban":
                        invoice.ten_dv_ban or "",

                    "dia_chi":
                        invoice.dia_chi or "",
                }
            )
        )

        invoice.supplier = supplier_instance

        invoice.save(
            update_fields=["supplier"]
        )

    # =========================================================
    # 3. TÌM PN ĐÃ TỒN TẠI
    # =========================================================

    po = (
        PurchaseOrder.objects
        .filter(
            invoice=invoice,
            phan_loai_phieu="PN"
        )
        .first()
    )

    # =========================================================
    # 4. TẠO PN MỚI
    # =========================================================

    if not po:

        po_number = generate_pn(invoice)

        po = PurchaseOrder.objects.create(

            invoice=invoice,

            po_number=po_number,

            supplier=supplier_instance,

            total_amount=Decimal(
                invoice.tong_tien or 0
            ),

            total_tax=Decimal(
                invoice.tong_tien_thue or 0
            ),

            # QUAN TRỌNG
            phan_loai_phieu="PN",

            # QUAN TRỌNG
            fiscal_year=fiscal_year,
        )

        sync_po_items_from_invoice(
            po,
            invoice
        )

        messages.success(
            request,
            f"Đã tạo PN #{po.po_number} "
            f"năm {fiscal_year} "
            f"từ hóa đơn #{invoice.so_hoa_don}."
        )

    # =========================================================
    # 5. PN ĐÃ TỒN TẠI
    # =========================================================

    else:

        update_fields = []

        # Đồng bộ năm
        if po.fiscal_year != fiscal_year:

            po.fiscal_year = fiscal_year

            update_fields.append(
                "fiscal_year"
            )

        # Đảm bảo đúng loại PN
        if po.phan_loai_phieu != "PN":

            po.phan_loai_phieu = "PN"

            update_fields.append(
                "phan_loai_phieu"
            )

        # Đồng bộ supplier
        if (
            supplier_instance
            and po.supplier_id != supplier_instance.id
        ):

            po.supplier = supplier_instance

            update_fields.append(
                "supplier"
            )

        if update_fields:

            po.save(
                update_fields=update_fields
            )

        # Sync items
        sync_po_items_from_invoice(
            po,
            invoice
        )

        messages.info(
            request,
            f"Đã mở và đồng bộ PN #{po.po_number} "
            f"năm {fiscal_year} "
            f"theo hóa đơn #{invoice.so_hoa_don}."
        )

    # =========================================================
    # 6. ĐIỀU HƯỚNG
    # =========================================================

    return redirect(
        "edit_purchase_order",
        po_id=po.id
    )



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
        .select_related("invoice", "activity_type")
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
        bank_total = po.bank_payments.aggregate(total=Sum('amount'))['total'] or 0
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



def edit_purchase_order(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    items = po.items.all()

    activity_types = ActivityType.objects.filter(
        is_active=True
    ).order_by("code")

    if request.method == 'POST':

        # Lấy loại hình hoạt động
        activity_type_id = request.POST.get("activity_type")

        if not activity_type_id:
            messages.error(
                request,
                "Vui lòng chọn loại hình hoạt động."
            )
            return render(
                request,
                "edit_po.html",
                {
                    "po": po,
                    "items": items,
                    "activity_types": activity_types,
                }
            )

        try:
            po.activity_type = ActivityType.objects.get(
                id=activity_type_id,
                is_active=True
            )
        except ActivityType.DoesNotExist:
            messages.error(
                request,
                "Loại hình hoạt động không hợp lệ."
            )
            return render(
                request,
                "edit_po.html",
                {
                    "po": po,
                    "items": items,
                    "activity_types": activity_types,
                }
            )

        for item in items:
            sku = request.POST.get(
                f'sku_{item.id}', ''
            ).strip()

            ten_goi_chung = request.POST.get(
                f'ten_goi_chung_{item.id}', ''
            ).strip()

            quantity = to_decimal_safe(
                request.POST.get(
                    f'so_luong_{item.id}',
                    item.quantity
                )
            )

            so_luong_quy_doi = to_decimal_safe(
                request.POST.get(
                    f'so_luong_quy_doi_{item.id}',
                    getattr(item, 'so_luong_quy_doi', 0)
                )
            )

            unit_price = to_decimal_safe(
                request.POST.get(
                    f'don_gia_{item.id}',
                    item.unit_price
                )
            )

            tax_rate = to_decimal_safe(
                request.POST.get(
                    f'thue_suat_field_{item.id}',
                    item.thue_suat_field
                )
            )

            chiet_khau = to_decimal_safe(
                request.POST.get(
                    f'chiet_khau_{item.id}',
                    getattr(item, 'chiet_khau', 0)
                )
            )

            thanh_tien_truoc_ck = getattr(
                item,
                'thanh_tien',
                quantity * unit_price
            )

            thanh_tien_sau_ck = getattr(
                item,
                'thanh_tien_sau_ck',
                thanh_tien_truoc_ck - chiet_khau
            )

            tien_thue = getattr(
                item,
                'tien_thue_field',
                (
                    thanh_tien_sau_ck
                    * tax_rate
                    / Decimal(100)
                ).quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP
                )
            )

            thanh_toan = getattr(
                item,
                'thanh_toan_field',
                (
                    thanh_tien_sau_ck + tien_thue
                ).quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP
                )
            )

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

        po.total_amount = sum(
            i.thanh_tien for i in po.items.all()
        )
        po.total_discount = sum(
            i.chiet_khau for i in po.items.all()
        )
        po.total_tax = sum(
            i.tien_thue_field for i in po.items.all()
        )
        po.total_final_amount = sum(
            i.thanh_toan_field for i in po.items.all()
        )

        po.save()

        messages.success(
            request,
            "Đã lưu thay đổi phiếu nhập thành công."
        )

        return redirect("invoice_list")

    return render(
        request,
        "edit_po.html",
        {
            "po": po,
            "items": items,
            "activity_types": activity_types,
        }
    )



def edit_purchase_order(request, po_id):
    po = get_object_or_404(
        PurchaseOrder,
        id=po_id
    )

    items = po.items.all()

    activity_types = ActivityType.objects.filter(
        is_active=True
    ).order_by("code")

    if request.method == "POST":

        # ==================================================
        # 1. TÌM LOẠI HÌNH HOẠT ĐỘNG THEO TẤT CẢ SKU
        # ==================================================

        activity_type_ids = set()

        for item in items:
            sku = request.POST.get(
                f"sku_{item.id}",
                ""
            ).strip()

            if not sku:
                continue

            products = ProductName.objects.filter(
                sku=sku
            ).select_related(
                "activity_type"
            )

            for product in products:
                if product.activity_type_id:
                    activity_type_ids.add(
                        product.activity_type_id
                    )

        # ==================================================
        # 2. XỬ LÝ LOẠI HÌNH HOẠT ĐỘNG CHO PHIẾU
        # ==================================================

        if len(activity_type_ids) == 1:
            # ----------------------------------------------
            # Chỉ có 1 loại hình
            # → TỰ ĐỘNG GÁN
            # ----------------------------------------------

            po.activity_type_id = next(
                iter(activity_type_ids)
            )

        elif len(activity_type_ids) > 1:
            # ----------------------------------------------
            # Có nhiều loại hình
            # → NGƯỜI DÙNG PHẢI CHỌN
            # ----------------------------------------------

            selected_activity_type_id = request.POST.get(
                "activity_type"
            )

            if not selected_activity_type_id:
                messages.error(
                    request,
                    "Các SKU trong phiếu có nhiều "
                    "loại hình hoạt động. "
                    "Vui lòng chọn loại hình cho phiếu."
                )

                return render(
                    request,
                    "edit_po.html",
                    {
                        "po": po,
                        "items": items,
                        "activity_types": activity_types,
                    }
                )

            # Chỉ cho phép chọn ActivityType
            # thực sự tồn tại từ SKU
            allowed_activity_type_ids = {
                str(activity_id)
                for activity_id in activity_type_ids
            }

            if selected_activity_type_id not in (
                allowed_activity_type_ids
            ):
                messages.error(
                    request,
                    "Loại hình hoạt động được chọn "
                    "không phù hợp với SKU trong phiếu."
                )

                return render(
                    request,
                    "edit_po.html",
                    {
                        "po": po,
                        "items": items,
                        "activity_types": activity_types,
                    }
                )

            po.activity_type_id = (
                selected_activity_type_id
            )

        else:
            # ----------------------------------------------
            # Không có SKU hoặc SKU chưa có loại hình
            # ----------------------------------------------

            po.activity_type = None

        # ==================================================
        # 3. CẬP NHẬT CÁC ITEM
        # ==================================================

        for item in items:

            sku = request.POST.get(
                f"sku_{item.id}",
                ""
            ).strip()

            ten_goi_chung = request.POST.get(
                f"ten_goi_chung_{item.id}",
                ""
            ).strip()

            quantity = to_decimal_safe(
                request.POST.get(
                    f"so_luong_{item.id}",
                    item.quantity
                )
            )

            so_luong_quy_doi = to_decimal_safe(
                request.POST.get(
                    f"so_luong_quy_doi_{item.id}",
                    getattr(
                        item,
                        "so_luong_quy_doi",
                        0
                    )
                )
            )

            unit_price = to_decimal_safe(
                request.POST.get(
                    f"don_gia_{item.id}",
                    item.unit_price
                )
            )

            tax_rate = to_decimal_safe(
                request.POST.get(
                    f"thue_suat_field_{item.id}",
                    item.thue_suat_field
                )
            )

            chiet_khau = to_decimal_safe(
                request.POST.get(
                    f"chiet_khau_{item.id}",
                    getattr(
                        item,
                        "chiet_khau",
                        0
                    )
                )
            )

            # ==================================================
            # TÍNH TIỀN
            # ==================================================

            thanh_tien_truoc_ck = (
                quantity * unit_price
            )

            thanh_tien_sau_ck = (
                thanh_tien_truoc_ck
                - chiet_khau
            )

            tien_thue = (
                thanh_tien_sau_ck
                * tax_rate
                / Decimal("100")
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            thanh_toan = (
                thanh_tien_sau_ck
                + tien_thue
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            # ==================================================
            # GÁN DỮ LIỆU ITEM
            # ==================================================

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

        # ==================================================
        # 4. TÍNH TỔNG PHIẾU
        # ==================================================

        po.total_amount = sum(
            i.thanh_tien
            for i in po.items.all()
        )

        po.total_discount = sum(
            i.chiet_khau
            for i in po.items.all()
        )

        po.total_tax = sum(
            i.tien_thue_field
            for i in po.items.all()
        )

        po.total_final_amount = sum(
            i.thanh_toan_field
            for i in po.items.all()
        )

        # ==================================================
        # 5. LƯU PHIẾU
        # ==================================================

        po.save()

        messages.success(
            request,
            "Đã lưu thay đổi phiếu nhập thành công."
        )

        return redirect("invoice_list")

    return render(
        request,
        "edit_po.html",
        {
            "po": po,
            "items": items,
            "activity_types": activity_types,
        }
    )



def edit_purchase_order(request, po_id):
    po = get_object_or_404(
        PurchaseOrder,
        id=po_id
    )

    items = po.items.all()

    activity_types = ActivityType.objects.filter(
        is_active=True
    ).order_by("code")

    # ==================================================
    # HÀM LẤY CÁC LOẠI HÌNH THEO SKU CỦA PO
    # ==================================================

    def get_activity_type_ids():
        activity_type_ids = set()

        for item in items:

            # POST: lấy SKU người dùng vừa nhập
            if request.method == "POST":
                sku = request.POST.get(
                    f"sku_{item.id}",
                    ""
                ).strip()

            # GET: lấy SKU đang có trong database
            else:
                sku = (
                    getattr(item, "sku_auto", None)
                    or getattr(item, "sku", None)
                    or ""
                ).strip()

            if not sku:
                continue

            # ==================================================
            # 1 SKU chỉ có 1 loại hình
            #
            # Không dùng .get()
            # vì ProductName có thể có nhiều dòng cùng SKU
            # ==================================================

            product_activity_ids = (
                ProductName.objects
                .filter(
                    sku=sku,
                    activity_type__isnull=False,
                    activity_type__is_active=True,
                )
                .values_list(
                    "activity_type_id",
                    flat=True
                )
                .distinct()
            )

            for activity_type_id in product_activity_ids:
                activity_type_ids.add(
                    activity_type_id
                )

        return activity_type_ids

    # ==================================================
    # XÁC ĐỊNH LOẠI HÌNH
    # ==================================================

    activity_type_ids = get_activity_type_ids()

    # Các loại hình thực tế xuất hiện trong SKU
    allowed_activity_types = activity_types.filter(
        id__in=activity_type_ids
    )

    # ==================================================
    # TRƯỜNG HỢP 1:
    # Tất cả SKU cùng 1 loại hình
    # ==================================================

    if len(activity_type_ids) == 1:

        auto_activity_type_id = next(
            iter(activity_type_ids)
        )

    else:

        auto_activity_type_id = None

    # ==================================================
    # GET
    # ==================================================

    if request.method == "GET":

        # Có đúng 1 loại hình từ SKU
        # → tự động chọn cho PO
        if auto_activity_type_id:

            po.activity_type_id = (
                auto_activity_type_id
            )

        return render(
            request,
            "edit_po.html",
            {
                "po": po,
                "items": items,
                "activity_types": activity_types,

                # Chỉ những loại hình xuất hiện
                # từ SKU mới được phép chọn
                "allowed_activity_types": (
                    allowed_activity_types
                ),

                "activity_type_ids": (
                    activity_type_ids
                ),
            }
        )

    # ==================================================
    # POST
    # ==================================================

    if request.method == "POST":

        # ==================================================
        # XÁC ĐỊNH LẠI ACTIVITY TYPE THEO SKU
        # ==================================================

        activity_type_ids = get_activity_type_ids()

        allowed_activity_types = activity_types.filter(
            id__in=activity_type_ids
        )

        # --------------------------------------------------
        # 1 loại hình
        # → tự động gán
        # --------------------------------------------------

        if len(activity_type_ids) == 1:

            po.activity_type_id = next(
                iter(activity_type_ids)
            )

        # --------------------------------------------------
        # Nhiều loại hình
        # → người dùng phải chọn
        # --------------------------------------------------

        elif len(activity_type_ids) > 1:

            selected_activity_type_id = (
                request.POST.get(
                    "activity_type"
                )
            )

            if not selected_activity_type_id:

                messages.error(
                    request,
                    "Các SKU trong phiếu có nhiều "
                    "loại hình hoạt động. "
                    "Vui lòng chọn loại hình cho phiếu."
                )

                return render(
                    request,
                    "edit_po.html",
                    {
                        "po": po,
                        "items": items,
                        "activity_types": activity_types,
                        "allowed_activity_types": (
                            allowed_activity_types
                        ),
                        "activity_type_ids": (
                            activity_type_ids
                        ),
                    }
                )

            # Chỉ được chọn loại hình
            # thực sự có trong SKU
            if int(selected_activity_type_id) not in (
                activity_type_ids
            ):

                messages.error(
                    request,
                    "Loại hình hoạt động được chọn "
                    "không phù hợp với SKU trong phiếu."
                )

                return render(
                    request,
                    "edit_po.html",
                    {
                        "po": po,
                        "items": items,
                        "activity_types": activity_types,
                        "allowed_activity_types": (
                            allowed_activity_types
                        ),
                        "activity_type_ids": (
                            activity_type_ids
                        ),
                    }
                )

            po.activity_type_id = (
                selected_activity_type_id
            )

        # --------------------------------------------------
        # Không có loại hình
        # --------------------------------------------------

        else:

            po.activity_type = None

        # ==================================================
        # CẬP NHẬT ITEM
        # ==================================================

        for item in items:

            sku = request.POST.get(
                f"sku_{item.id}",
                ""
            ).strip()

            ten_goi_chung = request.POST.get(
                f"ten_goi_chung_{item.id}",
                ""
            ).strip()

            quantity = to_decimal_safe(
                request.POST.get(
                    f"so_luong_{item.id}",
                    item.quantity
                )
            )

            so_luong_quy_doi = to_decimal_safe(
                request.POST.get(
                    f"so_luong_quy_doi_{item.id}",
                    getattr(
                        item,
                        "so_luong_quy_doi",
                        0
                    )
                )
            )

            unit_price = to_decimal_safe(
                request.POST.get(
                    f"don_gia_{item.id}",
                    item.unit_price
                )
            )

            tax_rate = to_decimal_safe(
                request.POST.get(
                    f"thue_suat_field_{item.id}",
                    item.thue_suat_field
                )
            )

            chiet_khau = to_decimal_safe(
                request.POST.get(
                    f"chiet_khau_{item.id}",
                    getattr(
                        item,
                        "chiet_khau",
                        0
                    )
                )
            )

            # ==================================================
            # TÍNH TIỀN
            # ==================================================

            thanh_tien_truoc_ck = (
                quantity * unit_price
            )

            thanh_tien_sau_ck = (
                thanh_tien_truoc_ck
                - chiet_khau
            )

            tien_thue = (
                thanh_tien_sau_ck
                * tax_rate
                / Decimal("100")
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            thanh_toan = (
                thanh_tien_sau_ck
                + tien_thue
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            # ==================================================
            # LƯU ITEM
            # ==================================================

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

        # ==================================================
        # TÍNH TỔNG PO
        # ==================================================

        po.total_amount = sum(
            i.thanh_tien
            for i in po.items.all()
        )

        po.total_discount = sum(
            i.chiet_khau
            for i in po.items.all()
        )

        po.total_tax = sum(
            i.tien_thue_field
            for i in po.items.all()
        )

        po.total_final_amount = sum(
            i.thanh_toan_field
            for i in po.items.all()
        )

        # ==================================================
        # LƯU PO
        # ==================================================

        po.save()

        messages.success(
            request,
            "Đã lưu thay đổi phiếu nhập thành công."
        )

        return redirect(
            "invoice_list"
        )



def edit_purchase_order(request, po_id):
    po = get_object_or_404(
        PurchaseOrder,
        id=po_id
    )

    items = po.items.all()

    activity_types = ActivityType.objects.filter(
        is_active=True
    ).order_by("code")

    # ==================================================
    # HÀM LẤY CÁC LOẠI HÌNH THEO SKU CỦA PO
    # ==================================================

    def get_activity_type_ids():
        activity_type_ids = set()

        for item in items:

            # POST: lấy SKU người dùng vừa nhập
            if request.method == "POST":
                sku = request.POST.get(
                    f"sku_{item.id}",
                    ""
                ).strip()

            # GET: lấy SKU đang có trong database
            else:
                sku = (
                    getattr(item, "sku_auto", None)
                    or getattr(item, "sku", None)
                    or ""
                ).strip()

            if not sku:
                continue

            # ==================================================
            # 1 SKU chỉ có 1 loại hình
            #
            # Không dùng .get()
            # vì ProductName có thể có nhiều dòng cùng SKU
            # ==================================================

            product_activity_ids = (
                ProductName.objects
                .filter(
                    sku=sku,
                    activity_type__isnull=False,
                    activity_type__is_active=True,
                )
                .values_list(
                    "activity_type_id",
                    flat=True
                )
                .distinct()
            )

            for activity_type_id in product_activity_ids:
                activity_type_ids.add(
                    activity_type_id
                )

        return activity_type_ids

    # ==================================================
    # XÁC ĐỊNH LOẠI HÌNH
    # ==================================================

    activity_type_ids = get_activity_type_ids()

    # Các loại hình thực tế xuất hiện trong SKU
    allowed_activity_types = activity_types.filter(
        id__in=activity_type_ids
    )

    # ==================================================
    # TRƯỜNG HỢP 1:
    # Tất cả SKU cùng 1 loại hình
    # ==================================================

    if len(activity_type_ids) == 1:

        auto_activity_type_id = next(
            iter(activity_type_ids)
        )

    else:

        auto_activity_type_id = None

    # ==================================================
    # GET
    # ==================================================

    if request.method == "GET":

        # Có đúng 1 loại hình từ SKU
        # → tự động chọn cho PO
        if auto_activity_type_id:

            po.activity_type_id = (
                auto_activity_type_id
            )

        return render(
            request,
            "edit_po.html",
            {
                "po": po,
                "items": items,
                "activity_types": activity_types,

                # Chỉ những loại hình xuất hiện
                # từ SKU mới được phép chọn
                "allowed_activity_types": (
                    allowed_activity_types
                ),

                "activity_type_ids": (
                    activity_type_ids
                ),
            }
        )

    # ==================================================
    # POST
    # ==================================================

    if request.method == "POST":

        # ==================================================
        # XÁC ĐỊNH LẠI ACTIVITY TYPE THEO SKU
        # ==================================================

        activity_type_ids = get_activity_type_ids()

        allowed_activity_types = activity_types.filter(
            id__in=activity_type_ids
        )

        # --------------------------------------------------
        # 1 loại hình
        # → tự động gán
        # --------------------------------------------------

        if len(activity_type_ids) == 1:

            po.activity_type_id = next(
                iter(activity_type_ids)
            )

        # --------------------------------------------------
        # Nhiều loại hình
        # → người dùng phải chọn
        # --------------------------------------------------

        elif len(activity_type_ids) > 1:

            selected_activity_type_id = (
                request.POST.get(
                    "activity_type"
                )
            )

            if not selected_activity_type_id:

                messages.error(
                    request,
                    "Các SKU trong phiếu có nhiều "
                    "loại hình hoạt động. "
                    "Vui lòng chọn loại hình cho phiếu."
                )

                return render(
                    request,
                    "edit_po.html",
                    {
                        "po": po,
                        "items": items,
                        "activity_types": activity_types,
                        "allowed_activity_types": (
                            allowed_activity_types
                        ),
                        "activity_type_ids": (
                            activity_type_ids
                        ),
                    }
                )

            # Chỉ được chọn loại hình
            # thực sự có trong SKU
            if int(selected_activity_type_id) not in (
                activity_type_ids
            ):

                messages.error(
                    request,
                    "Loại hình hoạt động được chọn "
                    "không phù hợp với SKU trong phiếu."
                )

                return render(
                    request,
                    "edit_po.html",
                    {
                        "po": po,
                        "items": items,
                        "activity_types": activity_types,
                        "allowed_activity_types": (
                            allowed_activity_types
                        ),
                        "activity_type_ids": (
                            activity_type_ids
                        ),
                    }
                )

            po.activity_type_id = (
                selected_activity_type_id
            )

        # --------------------------------------------------
        # Không có loại hình
        # --------------------------------------------------

        else:

            po.activity_type = None

        # ==================================================
        # CẬP NHẬT ITEM
        # ==================================================

        for item in items:

            sku = request.POST.get(
                f"sku_{item.id}",
                ""
            ).strip()

            ten_goi_chung = request.POST.get(
                f"ten_goi_chung_{item.id}",
                ""
            ).strip()

            quantity = to_decimal_safe(
                request.POST.get(
                    f"so_luong_{item.id}",
                    item.quantity
                )
            )

            so_luong_quy_doi = to_decimal_safe(
                request.POST.get(
                    f"so_luong_quy_doi_{item.id}",
                    getattr(
                        item,
                        "so_luong_quy_doi",
                        0
                    )
                )
            )

            unit_price = to_decimal_safe(
                request.POST.get(
                    f"don_gia_{item.id}",
                    item.unit_price
                )
            )

            tax_rate = to_decimal_safe(
                request.POST.get(
                    f"thue_suat_field_{item.id}",
                    item.thue_suat_field
                )
            )

            chiet_khau = to_decimal_safe(
                request.POST.get(
                    f"chiet_khau_{item.id}",
                    getattr(
                        item,
                        "chiet_khau",
                        0
                    )
                )
            )

            # ==================================================
            # TÍNH TIỀN
            # ==================================================

            thanh_tien_truoc_ck = (
                quantity * unit_price
            )

            thanh_tien_sau_ck = (
                thanh_tien_truoc_ck
                - chiet_khau
            )

            tien_thue = (
                thanh_tien_sau_ck
                * tax_rate
                / Decimal("100")
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            thanh_toan = (
                thanh_tien_sau_ck
                + tien_thue
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            # ==================================================
            # LƯU ITEM
            # ==================================================

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

        # ==================================================
        # TÍNH TỔNG PO
        # ==================================================

        po.total_amount = sum(
            i.thanh_tien
            for i in po.items.all()
        )

        po.total_discount = sum(
            i.chiet_khau
            for i in po.items.all()
        )

        po.total_tax = sum(
            i.tien_thue_field
            for i in po.items.all()
        )

        po.total_final_amount = sum(
            i.thanh_toan_field
            for i in po.items.all()
        )

        # ==================================================
        # LƯU PO
        # ==================================================

        po.save()

        messages.success(
            request,
            "Đã lưu thay đổi phiếu nhập thành công."
        )

        return redirect(
            "invoice_list"
        )




def edit_purchase_order(request, po_id):

    po = get_object_or_404(
        PurchaseOrder.objects.select_related(
            "invoice",
            "supplier",
            "activity_type",
        ),
        id=po_id,
    )

    # ==================================================
    # LẤY ITEMS 1 LẦN
    # ==================================================

    items = list(
        po.items.all()
    )

    # ==================================================
    # TOÀN BỘ LOẠI HÌNH ACTIVE
    #
    # Khi SKU không xác định được duy nhất
    # → người dùng được chọn từ TOÀN BỘ danh sách này
    # ==================================================

    activity_types = (
        ActivityType.objects
        .filter(is_active=True)
        .order_by("code")
    )

    # ==================================================
    # PHÂN TÍCH SKU
    # ==================================================

    def analyze_skus():

        sku_list = []

        for item in items:

            if request.method == "POST":

                sku = request.POST.get(
                    f"sku_{item.id}",
                    ""
                ).strip()

            else:

                sku = (
                    getattr(
                        item,
                        "sku_auto",
                        None,
                    )
                    or getattr(
                        item,
                        "sku",
                        None,
                    )
                    or ""
                ).strip()

            if sku:
                sku_list.append(sku)

        # ----------------------------------------------
        # Không có SKU
        # ----------------------------------------------

        if not sku_list:

            return {
                "has_sku": False,
                "all_sku_have_activity_type": False,
                "activity_type_ids": set(),
            }

        # ----------------------------------------------
        # Lấy ProductName của tất cả SKU
        # ----------------------------------------------

        products = (
            ProductName.objects
            .filter(
                sku__in=set(sku_list)
            )
            .values(
                "sku",
                "activity_type_id",
                "activity_type__is_active",
            )
        )

        # ----------------------------------------------
        # SKU -> các loại hình
        # ----------------------------------------------

        sku_activity_map = {
            sku: set()
            for sku in set(sku_list)
        }

        for product in products:

            sku = product["sku"]

            activity_type_id = (
                product["activity_type_id"]
            )

            is_active = (
                product[
                    "activity_type__is_active"
                ]
            )

            # Chỉ lấy loại hình active
            if (
                activity_type_id
                and is_active
            ):

                sku_activity_map[
                    sku
                ].add(
                    activity_type_id
                )

        # ----------------------------------------------
        # Kiểm tra từng SKU
        # ----------------------------------------------

        all_sku_have_activity_type = True

        activity_type_ids = set()

        for sku in set(sku_list):

            sku_types = sku_activity_map.get(
                sku,
                set()
            )

            # Có SKU chưa có loại hình
            if not sku_types:

                all_sku_have_activity_type = False

                continue

            activity_type_ids.update(
                sku_types
            )

        return {
            "has_sku": True,
            "all_sku_have_activity_type": (
                all_sku_have_activity_type
            ),
            "activity_type_ids": (
                activity_type_ids
            ),
        }

    # ==================================================
    # PHÂN TÍCH
    # ==================================================

    sku_info = analyze_skus()

    has_sku = sku_info[
        "has_sku"
    ]

    all_sku_have_activity_type = (
        sku_info[
            "all_sku_have_activity_type"
        ]
    )

    activity_type_ids = sku_info[
        "activity_type_ids"
    ]

    # ==================================================
    # CHỈ ĐƯỢC TỰ ĐỘNG KHI:
    #
    # 1. Có SKU
    # 2. Tất cả SKU đều có loại hình
    # 3. Chỉ có đúng 1 loại hình
    # ==================================================

    can_auto_assign = (
        has_sku
        and all_sku_have_activity_type
        and len(activity_type_ids) == 1
    )

    # ==================================================
    # GET
    # ==================================================

    if request.method == "GET":

        if can_auto_assign:

            # ------------------------------------------
            # Ví dụ:
            #
            # SKU A → loại 1
            # SKU B → loại 1
            #
            # → tự động chọn loại 1
            # ------------------------------------------

            po.activity_type_id = next(
                iter(activity_type_ids)
            )

        # ----------------------------------------------
        # Nếu:
        #
        # - nhiều loại hình
        # - SKU chưa có loại hình
        # - không có SKU
        #
        # thì KHÔNG tự gán.
        #
        # Template sẽ hiển thị TOÀN BỘ active.
        # ----------------------------------------------

        return render(
            request,
            "edit_po.html",
            {
                "po": po,
                "items": items,
                "activity_types": activity_types,

                "can_auto_assign": (
                    can_auto_assign
                ),
            }
        )

    # ==================================================
    # POST
    # ==================================================

    if request.method == "POST":

        # ==================================================
        # TRƯỜNG HỢP TỰ ĐỘNG
        # ==================================================

        if can_auto_assign:

            po.activity_type_id = next(
                iter(activity_type_ids)
            )

        # ==================================================
        # TRƯỜNG HỢP PHẢI CHỌN
        #
        # - Nhiều loại hình
        # - Có SKU chưa có loại hình
        # - Không có SKU
        # ==================================================

        else:

            selected_activity_type_id = (
                request.POST.get(
                    "activity_type",
                    ""
                ).strip()
            )

            # ----------------------------------------------
            # Chưa chọn
            # ----------------------------------------------

            if not selected_activity_type_id:

                messages.error(
                    request,
                    "Vui lòng chọn loại hình hoạt động."
                )

                return render(
                    request,
                    "edit_po.html",
                    {
                        "po": po,
                        "items": items,
                        "activity_types": activity_types,
                        "can_auto_assign": False,
                    }
                )

            # ----------------------------------------------
            # Kiểm tra ID
            # ----------------------------------------------

            try:

                selected_id = int(
                    selected_activity_type_id
                )

            except (
                ValueError,
                TypeError,
            ):

                messages.error(
                    request,
                    "Loại hình hoạt động không hợp lệ."
                )

                return render(
                    request,
                    "edit_po.html",
                    {
                        "po": po,
                        "items": items,
                        "activity_types": activity_types,
                        "can_auto_assign": False,
                    }
                )

            # ----------------------------------------------
            # CHỈ KIỂM TRA ACTIVE
            #
            # KHÔNG giới hạn theo SKU.
            #
            # Đây chính là yêu cầu:
            #
            # SKU chưa có loại hình
            # → chọn toàn bộ danh sách active.
            # ----------------------------------------------

            selected_activity_type = (
                ActivityType.objects.filter(
                    id=selected_id,
                    is_active=True,
                ).first()
            )

            if not selected_activity_type:

                messages.error(
                    request,
                    "Loại hình hoạt động được chọn "
                    "không tồn tại hoặc đã bị khóa."
                )

                return render(
                    request,
                    "edit_po.html",
                    {
                        "po": po,
                        "items": items,
                        "activity_types": activity_types,
                        "can_auto_assign": False,
                    }
                )

            # ----------------------------------------------
            # GÁN LOẠI HÌNH NGƯỜI DÙNG CHỌN
            # ----------------------------------------------

            po.activity_type_id = (
                selected_activity_type.id
            )

        # ==================================================
        # CẬP NHẬT ITEM
        # ==================================================

        with transaction.atomic():

            for item in items:

                sku = request.POST.get(
                    f"sku_{item.id}",
                    ""
                ).strip()

                ten_goi_chung = request.POST.get(
                    f"ten_goi_chung_{item.id}",
                    ""
                ).strip()

                quantity = to_decimal_safe(
                    request.POST.get(
                        f"so_luong_{item.id}",
                        item.quantity
                    )
                )

                so_luong_quy_doi = to_decimal_safe(
                    request.POST.get(
                        f"so_luong_quy_doi_{item.id}",
                        getattr(
                            item,
                            "so_luong_quy_doi",
                            0
                        )
                    )
                )

                unit_price = to_decimal_safe(
                    request.POST.get(
                        f"don_gia_{item.id}",
                        item.unit_price
                    )
                )

                tax_rate = to_decimal_safe(
                    request.POST.get(
                        f"thue_suat_field_{item.id}",
                        item.thue_suat_field
                    )
                )

                chiet_khau = to_decimal_safe(
                    request.POST.get(
                        f"chiet_khau_{item.id}",
                        getattr(
                            item,
                            "chiet_khau",
                            0
                        )
                    )
                )

                # ------------------------------------------
                # TÍNH TIỀN
                # ------------------------------------------

                thanh_tien_truoc_ck = (
                    quantity * unit_price
                )

                thanh_tien_sau_ck = (
                    thanh_tien_truoc_ck
                    - chiet_khau
                )

                tien_thue = (
                    thanh_tien_sau_ck
                    * tax_rate
                    / Decimal("100")
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP
                )

                thanh_toan = (
                    thanh_tien_sau_ck
                    + tien_thue
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP
                )

                # ------------------------------------------
                # GÁN ITEM
                # ------------------------------------------

                item.sku = sku
                item.ten_goi_chung = ten_goi_chung
                item.quantity = quantity
                item.so_luong_quy_doi = (
                    so_luong_quy_doi
                )
                item.unit_price = unit_price
                item.thue_suat_field = tax_rate
                item.chiet_khau = chiet_khau
                item.thanh_tien = (
                    thanh_tien_truoc_ck
                )
                item.thanh_tien_sau_ck = (
                    thanh_tien_sau_ck
                )
                item.tien_thue_field = tien_thue
                item.thanh_toan_field = thanh_toan

                item.save(
                    update_fields=[
                        "sku",
                        "ten_goi_chung",
                        "quantity",
                        "so_luong_quy_doi",
                        "unit_price",
                        "thue_suat_field",
                        "chiet_khau",
                        "thanh_tien",
                        "thanh_tien_sau_ck",
                        "tien_thue_field",
                        "thanh_toan_field",
                    ]
                )

            # ==================================================
            # TÍNH TỔNG
            # ==================================================

            po.total_amount = sum(
                (
                    item.thanh_tien
                    or Decimal("0")
                )
                for item in items
            )

            po.total_tax = sum(
                (
                    item.tien_thue_field
                    or Decimal("0")
                )
                for item in items
            )

            # ==================================================
            # LƯU PO
            #
            # Không dùng update_fields cho các field
            # không phải field DB thực tế.
            # ==================================================

            po.save()

        messages.success(
            request,
            "Đã lưu thay đổi phiếu nhập thành công."
        )

        return redirect(
            "purchase_order_list"
        )


from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Min, Max, Sum
from django.shortcuts import render
from django.contrib import messages
from invoice_reader_app.models_fiscalyear import FiscalYear
from django.db.models import Q

@login_required
def purchase_order_list(request):

    # =========================================================
    # 1. DANH SÁCH NĂM TÀI CHÍNH
    #    FiscalYear là nguồn dữ liệu chính
    # =========================================================

    year_list = list(
        FiscalYear.objects
        .order_by("-year")
        .values_list("year", flat=True)
    )

    # Nếu chưa có FiscalYear nào
    if not year_list:
        from datetime import datetime

        default_year = datetime.now().year

        FiscalYear.objects.create(
            year=default_year
        )

        year_list = [default_year]

    # =========================================================
    # 2. NĂM ĐANG CHỌN
    # =========================================================

    year_param = request.GET.get("year")

    if year_param:

        try:
            selected_year = int(year_param)
        except (ValueError, TypeError):
            selected_year = None

        if selected_year in year_list:
            current_year = selected_year
        else:
            current_year = year_list[0]

    else:

        session_year = request.session.get(
            "fiscal_year"
        )

        try:
            session_year = int(session_year)
        except (ValueError, TypeError):
            session_year = None

        if session_year in year_list:
            current_year = session_year
        else:
            current_year = year_list[0]

    # Lưu lại session
    request.session["fiscal_year"] = current_year

    # =========================================================
    # 3. PO THEO NĂM TÀI CHÍNH
    # =========================================================

    po_list = (
        PurchaseOrder.objects
        .select_related(
            "invoice",
            "activity_type"
        )
        .filter(
            phan_loai_phieu__in=["HH", "PN"],
            fiscal_year=current_year
        )
        .order_by("-po_number")
    )

    # =========================================================
    # 4. TÌM KIẾM
    # =========================================================

    search_invoice = request.GET.get(
        "invoice",
        ""
    ).strip()

    search_supplier = request.GET.get(
        "supplier",
        ""
    ).strip()

    search_po_number = request.GET.get(
        "po_number",
        ""
    ).strip()

    if search_invoice:
        po_list = po_list.filter(
            invoice__so_hoa_don__icontains=search_invoice
        )

    po_list = po_list.filter(
        Q(supplier__ten_dv_ban__icontains=search_supplier) |
        Q(supplier__ma_so_thue__icontains=search_supplier) |
        Q(supplier__dia_chi__icontains=search_supplier)
    )

    if search_po_number:
        po_list = po_list.filter(
            po_number__icontains=search_po_number
        )

    # =========================================================
    # 5. PHÂN TRANG
    # =========================================================

    per_page = request.GET.get(
        "per_page",
        "10"
    )

    page_number = request.GET.get(
        "page",
        "1"
    )

    if per_page != "all":

        try:
            per_page = int(per_page)

            if per_page <= 0:
                per_page = 10

        except (ValueError, TypeError):
            per_page = 10

    try:
        page_number = int(page_number)
    except (ValueError, TypeError):
        page_number = 1

    if per_page == "all":

        paginator = None
        pos = po_list
        page_obj = None

    else:

        paginator = Paginator(
            po_list,
            per_page
        )

        page_obj = paginator.get_page(
            page_number
        )

        pos = page_obj

    # =========================================================
    # 6. THANH TOÁN
    # =========================================================

    for po in pos:

        po.actual_payment = (
            po.bank_payments
            .aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

    # =========================================================
    # 7. QUERY PARAMS
    # =========================================================

    query_params = request.GET.copy()

    query_params.pop(
        "page",
        None
    )

    # =========================================================
    # 8. CONTEXT
    # =========================================================

    return render(
        request,
        "purchase_order_list.html",
        {
            "pos": pos,

            "label": "phiếu nhập",

            "search_invoice": search_invoice,

            "search_supplier": search_supplier,

            "search_po_number": search_po_number,

            "page_obj": page_obj,

            "paginator": paginator,

            "per_page": per_page,

            "query_params": query_params.urlencode(),

            "current_year": current_year,

            "year_list": year_list,
        }
    )



@login_required
def purchase_order_list(request):

    # =========================================================
    # 1. DANH SÁCH NĂM TÀI CHÍNH
    # =========================================================

    year_list = list(
        FiscalYear.objects
        .order_by("-year")
        .values_list("year", flat=True)
    )

    if not year_list:
        from datetime import datetime

        default_year = datetime.now().year

        FiscalYear.objects.create(
            year=default_year
        )

        year_list = [default_year]

    # =========================================================
    # 2. NĂM ĐANG CHỌN
    # =========================================================

    year_param = request.GET.get("year")

    if year_param:
        try:
            selected_year = int(year_param)
        except (ValueError, TypeError):
            selected_year = None

        if selected_year in year_list:
            current_year = selected_year
        else:
            current_year = year_list[0]

    else:
        session_year = request.session.get("fiscal_year")

        try:
            session_year = int(session_year)
        except (ValueError, TypeError):
            session_year = None

        if session_year in year_list:
            current_year = session_year
        else:
            current_year = year_list[0]

    request.session["fiscal_year"] = current_year

    # =========================================================
    # 3. PO THEO NĂM
    # =========================================================
    po_list = (
        PurchaseOrder.objects
        .select_related(
            "invoice",
            "activity_type",
            "supplier",
            "customer",
        )
        .filter(
            phan_loai_phieu="PN"
        )
    )

    if current_year:
        po_list = po_list.filter(
            Q(fiscal_year=current_year)
            |
            Q(
                fiscal_year__isnull=True,
                invoice__ngay_hd__year=current_year
            )
        )

    po_list = po_list.order_by("-po_number")

    # =========================================================
    # 4. TÌM KIẾM
    # =========================================================

    search_invoice = request.GET.get(
        "invoice",
        ""
    ).strip()

    search_supplier = request.GET.get(
        "supplier",
        ""
    ).strip()

    search_po_number = request.GET.get(
        "po_number",
        ""
    ).strip()

    search_activity_type = request.GET.get(
        "activity_type",
        ""
    ).strip()

    start_date_str = request.GET.get(
        "start_date",
        ""
    ).strip()

    end_date_str = request.GET.get(
        "end_date",
        ""
    ).strip()


    # =========================================================
    # SỐ HÓA ĐƠN
    # =========================================================

    if search_invoice:
        po_list = po_list.filter(
            invoice__so_hoa_don__icontains=search_invoice
        )


    # =========================================================
    # NHÀ CUNG CẤP
    # =========================================================

    if search_supplier:
        po_list = po_list.filter(
            Q(supplier__ten_dv_ban__icontains=search_supplier) |
            Q(supplier__ma_so_thue__icontains=search_supplier) |
            Q(supplier__dia_chi__icontains=search_supplier)
        )


    # =========================================================
    # SỐ PHIẾU PN
    # =========================================================

    if search_po_number:
        po_list = po_list.filter(
            po_number__icontains=search_po_number
        )


    # =========================================================
    # LOẠI HÌNH HOẠT ĐỘNG
    # =========================================================

    if search_activity_type:
        po_list = po_list.filter(
            activity_type_id=search_activity_type
        )


    # =========================================================
    # TỪ NGÀY
    # =========================================================

    if start_date_str:
        start_date = parse_date(start_date_str)

        if start_date:
            po_list = po_list.filter(
                invoice__ngay_hd__gte=start_date
            )


    # =========================================================
    # ĐẾN NGÀY
    # =========================================================

    if end_date_str:
        end_date = parse_date(end_date_str)

        if end_date:
            po_list = po_list.filter(
                invoice__ngay_hd__lte=end_date
            )


    # =========================================================
    # 5. PHÂN TRANG
    # =========================================================

    per_page_param = request.GET.get(
        "per_page",
        "10"
    ).strip()

    page_number = request.GET.get(
        "page",
        "1"
    ).strip()


    # ---------------------------------------------------------
    # Số dòng / trang
    # ---------------------------------------------------------

    if per_page_param == "all":

        per_page = "all"

    else:

        try:
            per_page = int(per_page_param)

            if per_page <= 0:
                per_page = 10

        except (ValueError, TypeError):

            per_page = 10


    # ---------------------------------------------------------
    # Số trang
    # ---------------------------------------------------------

    try:

        page_number = int(page_number)

        if page_number <= 0:
            page_number = 1

    except (ValueError, TypeError):

        page_number = 1


    # ---------------------------------------------------------
    # Tạo paginator
    # ---------------------------------------------------------

    if per_page == "all":

        paginator = None
        page_obj = None
        pos = po_list

    else:

        paginator = Paginator(
            po_list,
            per_page
        )

        page_obj = paginator.get_page(page_number)

        pos = page_obj

        # =========================================================
        # DANH SÁCH TRANG HIỂN THỊ
        # =========================================================

        current_page = page_obj.number
        num_pages = paginator.num_pages

        page_numbers = []

        # Luôn hiện trang 1
        page_numbers.append(1)

        # Các trang xung quanh trang hiện tại
        start_page = max(2, current_page - 2)
        end_page = min(num_pages - 1, current_page + 2)

        for num in range(start_page, end_page + 1):
            if num not in page_numbers:
                page_numbers.append(num)

        # Luôn hiện trang cuối
        if num_pages > 1 and num_pages not in page_numbers:
            page_numbers.append(num_pages)



    # =========================================================
    # 6. THANH TOÁN
    # =========================================================

    for po in pos:

        po.actual_payment = (
            po.bank_payments
            .aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )


    # =========================================================
    # 7. QUERY PARAMS
    # =========================================================
    #
    # Giữ toàn bộ điều kiện tìm kiếm khi chuyển trang
    #
    # =========================================================

    query_params = request.GET.copy()

    # Không để page cũ đi theo
    query_params.pop(
        "page",
        None
    )

    # Luôn giữ năm
    query_params["year"] = str(
        current_year
    )


    # ---------------------------------------------------------
    # Giữ số hóa đơn
    # ---------------------------------------------------------

    if search_invoice:

        query_params["invoice"] = (
            search_invoice
        )

    else:

        query_params.pop(
            "invoice",
            None
        )


    # ---------------------------------------------------------
    # Giữ nhà cung cấp
    # ---------------------------------------------------------

    if search_supplier:

        query_params["supplier"] = (
            search_supplier
        )

    else:

        query_params.pop(
            "supplier",
            None
        )


    # ---------------------------------------------------------
    # Giữ số phiếu
    # ---------------------------------------------------------

    if search_po_number:

        query_params["po_number"] = (
            search_po_number
        )

    else:

        query_params.pop(
            "po_number",
            None
        )


    # ---------------------------------------------------------
    # Giữ loại hình hoạt động
    # ---------------------------------------------------------

    if search_activity_type:

        query_params["activity_type"] = (
            search_activity_type
        )

    else:

        query_params.pop(
            "activity_type",
            None
        )


    # ---------------------------------------------------------
    # Giữ từ ngày
    # ---------------------------------------------------------

    if start_date_str:

        query_params["start_date"] = (
            start_date_str
        )

    else:

        query_params.pop(
            "start_date",
            None
        )


    # ---------------------------------------------------------
    # Giữ đến ngày
    # ---------------------------------------------------------

    if end_date_str:

        query_params["end_date"] = (
            end_date_str
        )

    else:

        query_params.pop(
            "end_date",
            None
        )


    # ---------------------------------------------------------
    # Giữ số dòng / trang
    # ---------------------------------------------------------

    query_params["per_page"] = str(
        per_page
    )


    # ---------------------------------------------------------
    # Chuyển thành query string
    # ---------------------------------------------------------

    query_params = query_params.urlencode()


    # =========================================================
    # 8. CONTEXT
    # =========================================================

    activity_types = (
        ActivityType.objects
        .all()
        .order_by("name")
    )


    return render(
        request,
        "purchase_order_list.html",
        {

            # -------------------------
            # DATA
            # -------------------------

            "pos": pos,

            "label": "phiếu nhập",


            # -------------------------
            # SEARCH
            # -------------------------

            "search_invoice":
                search_invoice,

            "search_supplier":
                search_supplier,

            "search_po_number":
                search_po_number,

            "search_activity_type":
                search_activity_type,


            # -------------------------
            # DATE
            # -------------------------

            "start_date":
                start_date_str,

            "end_date":
                end_date_str,


            # -------------------------
            # PAGINATION
            # -------------------------

            "page_obj":
                page_obj,

            "paginator":
                paginator,

            "per_page":
                per_page,


            # -------------------------
            # QUERY
            # -------------------------

            "query_params":
                query_params,


            # -------------------------
            # YEAR
            # -------------------------

            "current_year":
                current_year,

            "year_list":
                year_list,


            # -------------------------
            # ACTIVITY
            # -------------------------

            "activity_types":
                activity_types,
            "page_numbers": page_numbers,


        }
    )


def create_selected_invoices(request):
    """
    Tạo nhiều phiếu nhập từ danh sách hóa đơn được chọn.
    fiscal_year của PN lấy theo năm của ngày hóa đơn.
    """

    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "Invalid request method"
        })

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        })

    invoice_ids = data.get("ids", [])

    created_count = 0
    updated_count = 0

    for inv_id in invoice_ids:

        invoice = Invoice.objects.filter(
            id=inv_id
        ).first()

        if not invoice:
            continue

        # =====================================================
        # XÁC ĐỊNH NĂM TẠO PHIẾU
        # =====================================================

        fiscal_year = invoice.fiscal_year

        # Nếu Invoice chưa có fiscal_year
        # thì lấy theo ngày hóa đơn
        if not fiscal_year and invoice.ngay_hd:
            fiscal_year = invoice.ngay_hd.year

            # Đồng bộ lại vào Invoice
            invoice.fiscal_year = fiscal_year
            invoice.save(
                update_fields=["fiscal_year"]
            )

        # Không có cả fiscal_year và ngày hóa đơn
        if not fiscal_year:
            return JsonResponse({
                "success": False,
                "error": (
                    f"Hóa đơn {invoice.so_hoa_don} "
                    "chưa có năm tài chính và ngày hóa đơn."
                )
            })

        # =====================================================
        # SUPPLIER
        # =====================================================

        supplier_instance, _ = Supplier.objects.get_or_create(
            ten_dv_ban=invoice.ten_dv_ban,
            defaults={
                "ma_so_thue": invoice.ma_so_thue or "",
                "dia_chi": invoice.dia_chi or ""
            }
        )

        # =====================================================
        # TÌM PO ĐÃ TỒN TẠI
        # =====================================================

        po = PurchaseOrder.objects.filter(
            invoice=invoice
        ).first()

        if not po:

            # =================================================
            # TẠO SỐ PN
            # =================================================

            po_number = generate_pn(invoice)

            # =================================================
            # TẠO PN
            # =================================================

            po = PurchaseOrder.objects.create(
                invoice=invoice,

                po_number=po_number,

                supplier=supplier_instance,

                total_amount=Decimal(
                    invoice.tong_tien or 0
                ),

                total_tax=Decimal("0"),

                phan_loai_phieu="PN",

                # =============================================
                # NĂM TẠO PHIẾU
                # =============================================
                fiscal_year=fiscal_year,
            )

            created_count += 1

        else:

            updated_count += 1

            # =================================================
            # ĐỒNG BỘ NĂM CHO PO CŨ
            # =================================================

            if po.fiscal_year != fiscal_year:

                po.fiscal_year = fiscal_year

                po.save(
                    update_fields=["fiscal_year"]
                )

        # =====================================================
        # ĐỒNG BỘ ITEMS
        # =====================================================

        sync_po_items_from_invoice(
            po,
            invoice
        )

    return JsonResponse({
        "success": True,
        "created_count": created_count,
        "updated_count": updated_count,
    })




from django.views.decorators.http import require_POST
@require_POST
def create_selected_invoices(request):
    """
    Tạo nhiều phiếu nhập (PN) từ danh sách hóa đơn được chọn.

    Quy tắc:
    - fiscal_year của PN = năm ngày hóa đơn.
    - Nếu Invoice chưa có fiscal_year thì cập nhật luôn.
    - PN luôn có phan_loai_phieu = "PN".
    - Nếu PN đã tồn tại thì không tạo mới.
    - PN cũ chưa có năm thì bổ sung năm.
    """

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        })

    invoice_ids = data.get("ids", [])

    if not invoice_ids:
        return JsonResponse({
            "success": False,
            "error": "Chưa chọn hóa đơn."
        })

    created_count = 0
    updated_count = 0

    with transaction.atomic():

        for inv_id in invoice_ids:

            invoice = (
                Invoice.objects
                .select_related("supplier")
                .filter(id=inv_id)
                .first()
            )

            if not invoice:
                continue

            # =====================================================
            # 1. XÁC ĐỊNH NĂM
            # =====================================================

            fiscal_year = invoice.fiscal_year

            if not fiscal_year and invoice.ngay_hd:
                fiscal_year = invoice.ngay_hd.year

                invoice.fiscal_year = fiscal_year
                invoice.save(
                    update_fields=["fiscal_year"]
                )

            if not fiscal_year:
                raise ValueError(
                    f"Hóa đơn {invoice.so_hoa_don} "
                    f"không có năm tài chính."
                )

            # =====================================================
            # 2. SUPPLIER
            # =====================================================

            supplier_instance = invoice.supplier

            if not supplier_instance:

                supplier_instance, _ = (
                    Supplier.objects
                    .update_or_create(
                        ma_so_thue=invoice.ma_so_thue,
                        defaults={
                            "ten_dv_ban":
                                invoice.ten_dv_ban or "",

                            "dia_chi":
                                invoice.dia_chi or "",
                        }
                    )
                )

                invoice.supplier = supplier_instance
                invoice.save(
                    update_fields=["supplier"]
                )

            # =====================================================
            # 3. TÌM PN ĐÃ TỒN TẠI
            # =====================================================

            po = (
                PurchaseOrder.objects
                .filter(
                    invoice=invoice,
                    phan_loai_phieu="PN"
                )
                .first()
            )

            # =====================================================
            # 4. TẠO PN
            # =====================================================

            if not po:

                po_number = generate_pn(invoice)

                po = PurchaseOrder.objects.create(

                    invoice=invoice,

                    po_number=po_number,

                    supplier=supplier_instance,

                    total_amount=Decimal(
                        invoice.tong_tien or 0
                    ),

                    total_tax=Decimal("0"),

                    # QUAN TRỌNG
                    phan_loai_phieu="PN",

                    # QUAN TRỌNG
                    fiscal_year=fiscal_year,
                )

                created_count += 1

            else:

                updated_count += 1

                changed_fields = []

                # Đảm bảo là PN
                if po.phan_loai_phieu != "PN":
                    po.phan_loai_phieu = "PN"
                    changed_fields.append(
                        "phan_loai_phieu"
                    )

                # Đảm bảo có năm
                if po.fiscal_year != fiscal_year:
                    po.fiscal_year = fiscal_year
                    changed_fields.append(
                        "fiscal_year"
                    )

                # Đảm bảo supplier
                if po.supplier_id != supplier_instance.id:
                    po.supplier = supplier_instance
                    changed_fields.append(
                        "supplier"
                    )

                if changed_fields:
                    po.save(
                        update_fields=changed_fields
                    )

            # =====================================================
            # 5. ĐỒNG BỘ ITEMS
            # =====================================================

            sync_po_items_from_invoice(
                po,
                invoice
            )

    return JsonResponse({
        "success": True,
        "created_count": created_count,
        "updated_count": updated_count,
    })
