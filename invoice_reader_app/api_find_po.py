from django.http import JsonResponse
from .models_purcharoder import PurchaseOrder

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
