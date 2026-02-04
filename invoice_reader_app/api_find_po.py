from django.http import JsonResponse
from .models_purcharoder import PurchaseOrder, PurchaseOrderItem
from invoice_reader_app.model_invoice import ProductName, Invoice, Supplier, Customer
from decimal import Decimal
from django.http import JsonResponse
from django.db.models import Sum


def api_find_po(request):
    mst = request.GET.get('mst', '').strip()
    sohd = request.GET.get('sohd', '').strip()

    if not mst or not sohd:
        return JsonResponse({'found': False, 'pos': []})

    # Chuẩn hóa số hóa đơn thành list
    sohd_list = []
    for s in sohd.split(','):
        s_clean = s.strip()
        if s_clean:
            try:
                s_clean_int = str(int(s_clean))
                sohd_list.append(s_clean_int)
            except ValueError:
                continue

    # Lọc PO theo MST từ invoice
    pos_qs = PurchaseOrder.objects.filter(
        invoice__isnull=False,
        invoice__ma_so_thue=mst
    ).order_by('po_number')

    pos_list = []
    for po in pos_qs:
        inv_no = getattr(po.invoice, 'so_hoa_don', None)
        if not inv_no:
            continue
        try:
            inv_no_clean = str(int(inv_no))
        except (ValueError, TypeError):
            continue
        if inv_no_clean in sohd_list:
            # Tính tổng tiền hàng + thuế từ các item
            total_amount = sum(
                getattr(item, 'total_price', 0) for item in po.items.all()
            )
            total_tax = sum(
                getattr(item, 'tien_thue', 0) for item in po.items.all()
            )

            pos_list.append({
                'id': po.id,
                'po_number': po.po_number,
                'invoice': inv_no,
                'supplier': str(po.supplier) if po.supplier else '',
                'amount': float(total_amount),
                'tax': float(total_tax),
                'total_payment': float(total_amount + total_tax),
            })

    return JsonResponse({
        'found': bool(pos_list),
        'pos': pos_list
    })



from django.http import JsonResponse

from .services.tax_api import lookup_tax_code


def get_or_create_customer_by_mst(request):
    mst = request.GET.get("mst", "").strip()

    if not mst:
        return JsonResponse({"error": "missing_mst"}, status=400)

    # 1️⃣ Có trong DB
    customer = Customer.objects.filter(ma_so_thue=mst).first()
    if customer:
        return JsonResponse({
            "id": customer.id,
            "ten_khach_hang": customer.ten_khach_hang,
            "dia_chi": customer.dia_chi,
            "source": "db",
        })

    # 2️⃣ Gọi Tổng cục Thuế
    tax_data = lookup_tax_code(mst)
    if not tax_data:
        return JsonResponse({"not_found": True})

    # 3️⃣ Tạo khách hàng mới
    customer = Customer.objects.create(
        ma_so_thue=mst,
        ten_khach_hang=tax_data["ten_khach_hang"],
        dia_chi=tax_data["dia_chi"],
        phan_loai="KHÁCH HÀNG",   # 👈 gán mặc định rất hợp lý
    )

    return JsonResponse({
        "id": customer.id,
        "ten_khach_hang": customer.ten_khach_hang,
        "dia_chi": customer.dia_chi,
        "source": "tax",
    })



def api_inventory_by_sku(request):
    sku = request.GET.get("sku", "").strip().upper()

    if not sku:
        return JsonResponse({"found": False})

    qs = PurchaseOrderItem.objects.filter(
        sku__iexact=sku,
        purchase_order__phan_loai_phieu="HH"
    )

    if not qs.exists():
        return JsonResponse({"found": False})

    total_qty = 0
    total_money = 0
    ten_goi_chung = ""
    unit = ""

    for i in qs:
        qty = float(i.so_luong_quy_doi or i.quantity or 0)
        total_qty += qty
        total_money += float(i.total_price or 0)
        ten_goi_chung = i.ten_goi_chung
        unit = i.unit

    gia_tb = total_money / total_qty if total_qty else 0

    return JsonResponse({
        "found": True,
        "sku": sku,
        "ten_goi_chung": ten_goi_chung,
        "dvt": unit,
        "don_gia": round(gia_tb, 2),
        "ton": round(total_qty, 2)
    })

def get_avg_export_price(sku):
    qs = (
        PurchaseOrderItem.objects
        .filter(
            purchase_order__phan_loai_phieu='PX',
            sku=sku
        )
        .aggregate(
            tong_qty=Sum('quantity'),
            tong_tien=Sum('total_price')
        )
    )

    qty = qs['tong_qty'] or 0
    tien = qs['tong_tien'] or 0

    return round(tien / qty, 0) if qty else 0



from invoice_reader_app.inventory_summary import get_inventory_data_fast

def api_products_search(request):
    search = request.GET.get("q", "").strip()
    data = get_inventory_data_fast(search=search)

    return JsonResponse({
        "count": len(data),
        "results": data
    })