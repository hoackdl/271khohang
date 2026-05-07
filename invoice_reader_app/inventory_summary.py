from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import HttpResponse
import openpyxl
from invoice_reader_app.model_invoice import InvoiceItem, ProductName
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import (
    Sum, F, Case, When, FloatField, Value, Q
)
from django.db.models.functions import Coalesce, Cast
from .models_purchaseorder import PurchaseOrder, PurchaseOrderItem  # đổi theo tên app của bạn
from invoice_reader_app.model_invoice import ProductName


@login_required
def inventory_detail(request, sku):
    qs = (
        PurchaseOrderItem.objects
        .filter(sku_auto=sku)
        .select_related('purchase_order')
        .values(
            'purchase_order__po_number',
            'purchase_order__created_at',
            'purchase_order__phan_loai_phieu'
        )
        .annotate(
            so_luong=Sum(
                Coalesce(F('so_luong_quy_doi'), F('quantity'))
            ),
            thanh_tien=Sum('total_price')
        )
        .order_by('-purchase_order__created_at')
    )

    return JsonResponse(list(qs), safe=False)


def inventory_summary_export(request):
    qs = get_inventory_data_fast(request.GET.get('search'))

    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet("XNT")

    ws.append([
        "SKU", "Tổng nhập", "Tổng xuất",
        "Tồn cuối", "Giá TB nhập", "Giá TB xuất"
    ])

    for row in qs.iterator(chunk_size=2000):
        tong_nhap = row['tong_nhap']
        tong_xuat = row['tong_xuat']
        ws.append([
            row['sku'],
            tong_nhap,
            tong_xuat,
            tong_nhap - tong_xuat,
            (row['tong_tien_nhap'] / tong_nhap) if tong_nhap else 0,
            (row['tong_tien_xuat'] / tong_xuat) if tong_xuat else 0,
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=inventory.xlsx'
    wb.save(response)
    return response


from collections import defaultdict
from django.db.models import F

def get_inventory_data_fast(search=None):
    """
    Phiên bản tối ưu: xử lý nhanh hơn bằng cách:
    - Lấy ProductName một lần cho tất cả SKU.
    - Dùng dict để group SKU.
    """
    # 1. Lấy tất cả item nhập/xuất
    po_items_in = PurchaseOrderItem.objects.filter(
        purchase_order__phan_loai_phieu__in=['HH', 'PN']
    ).values(
        'sku', 'ten_goi_chung', 'unit', 'quantity', 'so_luong_quy_doi', 'total_price',
        'purchase_order__po_number', 'purchase_order__created_at'
    )

    po_items_out = PurchaseOrderItem.objects.filter(
        purchase_order__phan_loai_phieu='PX'
    ).values(
        'sku', 'ten_goi_chung', 'unit', 'quantity', 'total_price',
        'purchase_order__po_number', 'purchase_order__created_at'
    )

    # 2. Lấy tên gọi chung một lần cho tất cả SKU
    skus = set()
    for item in po_items_in:
        if item['sku']:
            skus.add(item['sku'])
    for item in po_items_out:
        if item['sku']:
            skus.add(item['sku'])

    product_map = dict(
        ProductName.objects.filter(sku__in=skus)
        .values_list('sku', 'ten_goi_chung')
    )

    # 3. Group dữ liệu
    grouped = defaultdict(lambda: {
        'sku': '',
        'ten_goi_chung': '',
        'dvt': '',
        'tong_nhap': 0,
        'tong_xuat': 0,
        'gia_tb_nhap': 0,
        'gia_tb_xuat': 0,
        'chi_tiet_nhap': [],
        'chi_tiet_xuat': [],
    })

    # --- nhập ---
    for item in po_items_in:
        sku = item['sku']
        if not sku:
            continue

        data = grouped[sku]
        data['sku'] = sku
        data['ten_goi_chung'] = product_map.get(sku, item['ten_goi_chung'])
        data['dvt'] = item['unit']

        qty = float(item['so_luong_quy_doi'] or item['quantity'] or 0)
        thanh_tien = float(item['total_price'] or 0)
        don_gia = thanh_tien / qty if qty else 0

        data['tong_nhap'] += qty
        data['chi_tiet_nhap'].append({
            'ma_po': item['purchase_order__po_number'],
            'so_luong': qty,
            'thanh_tien': float(item['total_price'] or 0),
            'don_gia': round(don_gia, 2),
            'ngay': item['purchase_order__created_at'],
        })

    # --- xuất ---
    for item in po_items_out:
        sku = item['sku']
        if not sku:
            continue

        data = grouped[sku]
        data['sku'] = sku
        data['ten_goi_chung'] = product_map.get(sku, item['ten_goi_chung'])
        data['dvt'] = item['unit']

        qty = float(item['quantity'] or 0)
        thanh_tien = float(item['total_price'] or 0)
        don_gia = thanh_tien / qty if qty else 0

        data['tong_xuat'] += qty
        data['chi_tiet_xuat'].append({
            'ma_po': item['purchase_order__po_number'],
            'so_luong': qty,
            'thanh_tien': float(item['total_price'] or 0),
            'don_gia': round(don_gia, 2),
            'ngay': item['purchase_order__created_at'],
        })

    # 4. Tính tồn cuối và giá TB
    data_list = []
    for sku, d in grouped.items():
        tong_tien_nhap = sum(c['thanh_tien'] for c in d['chi_tiet_nhap'])
        tong_tien_xuat = sum(c['thanh_tien'] for c in d['chi_tiet_xuat'])

        d['ton_cuoi'] = d['tong_nhap'] - d['tong_xuat']
        d['gia_tb_nhap'] = (tong_tien_nhap / d['tong_nhap']) if d['tong_nhap'] else 0
        d['gia_tb_xuat'] = (tong_tien_xuat / d['tong_xuat']) if d['tong_xuat'] else 0

        # gộp chi tiết
        d['chi_tiet'] = d['chi_tiet_nhap'] + d['chi_tiet_xuat']

        data_list.append(d)
    # 4.5. Sắp xếp theo SKU
    data_list = sorted(data_list, key=lambda x: x['sku'] or '')
    
    # 5. Lọc theo search nếu cần
    if search:
        search_lower = search.lower()
        data_list = [
            d for d in data_list
            if search_lower in (d['sku'] or '').lower() or search_lower in (d['ten_goi_chung'] or '').lower()
        ]

    return data_list


from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def inventory_summary(request):
    search = request.GET.get('search', '').strip()
    per_page = int(request.GET.get('per_page', 20))
    page_number = request.GET.get('page')  # ✅ KHÔNG ÉP INT

    data_all = get_inventory_data_fast(search=search)

    # 🔥 đưa tồn âm lên đầu
    data_all.sort(key=lambda x: x['ton_cuoi'] >= 0)

    
    paginator = Paginator(data_all, per_page)
    page_obj = paginator.get_page(page_number)

    totals = {
        'tong_nhap': sum(d['tong_nhap'] for d in data_all),
        'tong_xuat': sum(d['tong_xuat'] for d in data_all),
        'ton_cuoi': sum(d['ton_cuoi'] for d in data_all),
        'gia_tb_nhap': round(
            sum(d['tong_nhap'] * d['gia_tb_nhap'] for d in data_all) /
            sum(d['tong_nhap'] for d in data_all)
        ) if sum(d['tong_nhap'] for d in data_all) else 0,
        'gia_tb_xuat': round(
            sum(d['tong_xuat'] * d['gia_tb_xuat'] for d in data_all) /
            sum(d['tong_xuat'] for d in data_all)
        ) if sum(d['tong_xuat'] for d in data_all) else 0,
    }

    return render(request, "inventory_summary.html", {
        "data": page_obj.object_list,
        "page_obj": page_obj,
        "search": search,
        "per_page": per_page,
        "totals": totals,
    })




