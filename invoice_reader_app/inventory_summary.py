from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import HttpResponse
import openpyxl
from invoice_reader_app.model_invoice import InvoiceItem, ProductName
from django.contrib.auth.decorators import login_required



# --------------------------
# Hàm lấy dữ liệu chung
# --------------------------


from .models_purcharoder import PurchaseOrder, PurchaseOrderItem  # đổi theo tên app của bạn


from invoice_reader_app.model_invoice import ProductName


def get_inventory_data(search=None):
    """
    Lấy dữ liệu xuất–nhập–tồn từ phiếu nhập và phiếu xuất hàng hóa.
    Luôn lấy tên gọi chung mới từ DMHH (ProductName) dựa trên SKU.
    Chỉ lấy các dòng có SKU hợp lệ (dùng sku_auto).
    """

    # --- Lấy tất cả item phiếu nhập và xuất ---
    po_items_in_qs = PurchaseOrderItem.objects.filter(purchase_order__phan_loai_phieu='HH')
    po_items_out_qs = PurchaseOrderItem.objects.filter(purchase_order__phan_loai_phieu='PX')

    # --- Map nhập theo SKU ---
    grouped = {}
    for item in po_items_in_qs:
        sku = item.sku_auto
        if not sku:
            continue

        # Lấy tên gọi chung mới từ DMHH nếu có
        product_obj = ProductName.objects.filter(sku=sku).first()
        ten_goi_chung = product_obj.ten_goi_chung if product_obj else item.ten_goi_chung_auto
        dvt = item.unit

        if sku not in grouped:
            grouped[sku] = {
                'sku': sku,
                'ten_goi_chung': ten_goi_chung,
                'dvt': dvt,
                'tong_nhap': 0,
                'tong_xuat': 0,
                'gia_tb_nhap': 0,
                'gia_tb_xuat': 0,
                'chi_tiet_nhap': [],
                'chi_tiet_xuat': []
            }

        qty_raw = float(item.quantity or 0)
        qty_qd = float(item.so_luong_quy_doi or 0)
        qty_used = qty_qd if qty_qd > 0 else qty_raw

        grouped[sku]['tong_nhap'] += qty_used
        grouped[sku]['chi_tiet_nhap'].append({
            'ma_po': item.purchase_order.po_number,
            'so_luong': qty_used,
            'thanh_tien': float(item.total_price or 0),
            'ngay_nhap': item.purchase_order.created_at,
        })

    # --- Map xuất theo SKU ---
    for item in po_items_out_qs:
        sku = item.sku_auto
        if not sku:
            continue

        # Lấy tên gọi chung mới từ DMHH nếu có
        product_obj = ProductName.objects.filter(sku=sku).first()
        ten_goi_chung = product_obj.ten_goi_chung if product_obj else item.ten_goi_chung_auto

        if sku not in grouped:
            grouped[sku] = {
                'sku': sku,
                'ten_goi_chung': ten_goi_chung,
                'dvt': item.unit,
                'tong_nhap': 0,
                'tong_xuat': 0,
                'gia_tb_nhap': 0,
                'gia_tb_xuat': 0,
                'chi_tiet_nhap': [],
                'chi_tiet_xuat': []
            }

        grouped[sku]['tong_xuat'] += float(item.quantity or 0)
        grouped[sku]['chi_tiet_xuat'].append({
            'ma_po': item.purchase_order.po_number,
            'so_luong': float(item.quantity or 0),
            'thanh_tien': float(item.total_price or 0),
            'ngay_xuat': item.purchase_order.created_at,
        })

    # --- Tính giá trung bình nhập/xuất và tồn cuối ---
    for sku, data in grouped.items():
        tong_nhap = data['tong_nhap']
        tong_xuat = data['tong_xuat']

        tong_tien_nhap = sum(c['thanh_tien'] for c in data['chi_tiet_nhap'])
        tong_tien_xuat = sum(c['thanh_tien'] for c in data['chi_tiet_xuat'])

        data['ton_cuoi'] = tong_nhap - tong_xuat
        data['gia_tb_nhap'] = (tong_tien_nhap / tong_nhap) if tong_nhap else 0
        data['gia_tb_xuat'] = (tong_tien_xuat / tong_xuat) if tong_xuat else 0

    # --- Chuyển về list ---
    data_list = list(grouped.values())

    # --- Lọc theo search nếu có ---
    if search:
        search = search.lower()
        data_list = [
            d for d in data_list
            if search in d['sku'].lower() or search in d['ten_goi_chung'].lower()
        ]

    return data_list



# --------------------------
# View hiển thị
# --------------------------
from django.core.paginator import Paginator
from django.shortcuts import render
@login_required
def inventory_summary(request):
    search = request.GET.get('search', '').strip()
    data = get_inventory_data(search=search)  # data là list dict

    # --- Sắp xếp theo SKU ---
    data = sorted(data, key=lambda x: x.get('sku', ''))

    for row in data:
        chi_tiet_nhap = row.get('chi_tiet_nhap', [])
        chi_tiet_xuat = row.get('chi_tiet_xuat', [])

        ct_dict = {}

        for item in chi_tiet_nhap:
            key = item['ma_po']
            ngay = item.get('ngay_hd') or item.get('ngay_nhap')  # fallback nếu 'ngay_hd' không có
            if key not in ct_dict:
                ct_dict[key] = {
                    'ma_po': item['ma_po'],
                    'ngay': ngay,
                    'so_luong_nhap': item['so_luong'],
                    'so_luong_xuat': 0,
                    'thanh_tien_nhap': item['thanh_tien'],
                    'thanh_tien_xuat': 0,
                }
            else:
                ct_dict[key]['so_luong_nhap'] += item['so_luong']
                ct_dict[key]['thanh_tien_nhap'] += item['thanh_tien']

        for item in chi_tiet_xuat:
            key = item['ma_po']
            ngay = item.get('ngay_hd') or item.get('ngay_xuat')  # fallback nếu 'ngay_hd' không có
            if key not in ct_dict:
                ct_dict[key] = {
                    'ma_po': item['ma_po'],
                    'ngay': ngay,
                    'so_luong_nhap': 0,
                    'so_luong_xuat': item['so_luong'],
                    'thanh_tien_nhap': 0,
                    'thanh_tien_xuat': item['thanh_tien'],
                }
            else:
                ct_dict[key]['so_luong_xuat'] += item['so_luong']
                ct_dict[key]['thanh_tien_xuat'] += item['thanh_tien']

        # Sắp xếp chi_tiet theo ngày giảm dần
        row['chi_tiet'] = sorted(
            ct_dict.values(),
            key=lambda x: x['ngay'],
            reverse=True
        )



    # Tính tổng trước phân trang
    totals = {
        'tong_nhap': sum(d.get('tong_nhap', 0) for d in data),
        'tong_xuat': sum(d.get('tong_xuat', 0) for d in data),
        'ton_cuoi': sum(d.get('ton_cuoi', 0) for d in data),
        'gia_tb_nhap': sum(d.get('gia_tb_nhap', 0) for d in data),
        'gia_tb_xuat': sum(d.get('gia_tb_xuat', 0) for d in data),
    }

    # Phân trang
    per_page = request.GET.get('per_page', 20)
    if per_page == 'all':
        per_page = len(data) or 1
    else:
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 20

    paginator = Paginator(data, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_number = int(page_number)
    except (ValueError, TypeError):
        page_number = 1
    page_obj = paginator.get_page(page_number)

    # Query string giữ filter khi đổi page
    query_params = request.GET.copy()
    query_params.pop('page', None)

    return render(request, "inventory_summary.html", {
        "data": page_obj,
        "search": search,
        "per_page": per_page,
        "query_params": query_params.urlencode(),
        "totals": totals
    })



# --------------------------
# View xuất Excel
# --------------------------
from io import BytesIO
@login_required
def inventory_summary_export(request):
    search = request.GET.get('search', '').strip()
    data = get_inventory_data(search=search)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Báo cáo Xuất-Nhập-Tồn"

    # Header
    headers = ["TT", "SKU", "Tên gọi chung", "ĐVT", "Tổng nhập", "Tổng xuất", "Tồn cuối", "Giá TB nhập", "Giá TB xuất"]
    ws.append(headers)

    # Dữ liệu
    for idx, row in enumerate(data, start=1):
        ws.append([
            idx,
            row['sku'],              # ✅ thêm dòng này
            row['ten_goi_chung'],
            row['dvt'],
            row['tong_nhap'],
            row['tong_xuat'],
            row['ton_cuoi'],
            row['gia_tb_nhap'],
            row['gia_tb_xuat'],
        ])

    # Tổng cuối
    total_nhap = sum(d['tong_nhap'] for d in data)
    total_xuat = sum(d['tong_xuat'] for d in data)
    total_ton_cuoi = sum(d['ton_cuoi'] for d in data)
    ws.append(["", "", "Tổng", "", total_nhap, total_xuat, total_ton_cuoi, "", ""])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=inventory_summary.xlsx'
    return response
