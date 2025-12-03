from django.http import JsonResponse
from .models_purcharoder import PurchaseOrder

def api_find_po(request):
    """
    API tìm PO theo MST (tax code) và nhiều số hóa đơn.
    Sửa MST lấy từ invoice.ma_so_thue, số hóa đơn bỏ số 0 đầu.
    """
    mst = request.GET.get('mst', '').strip()
    sohd = request.GET.get('sohd', '').strip()

    if not mst or not sohd:
        return JsonResponse({'found': False, 'pos': []})

    # Chuẩn hóa số hóa đơn
    sohd_list = []
    for s in sohd.split(','):
        s_clean = s.strip()
        if s_clean:
            try:
                s_clean_int = str(int(s_clean))
                sohd_list.append(s_clean_int)
            except ValueError:
                continue

    # Lọc PO theo MST từ invoice và số hóa đơn
    pos_qs = PurchaseOrder.objects.filter(
        invoice__ma_so_thue=mst
    ).order_by('po_number')

    filtered_pos = []
    for po in pos_qs:
        inv_no = getattr(po.invoice, 'so_hoa_don', None)
        if not inv_no:
            continue
        try:
            inv_no_clean = str(int(inv_no))
        except (ValueError, TypeError):
            continue
        if inv_no_clean in sohd_list:
            filtered_pos.append(po)

    pos_list = []
    for po in filtered_pos:
        pos_list.append({
            'id': po.id,
            'po_number': po.po_number,
            'invoice': getattr(po.invoice, 'so_hoa_don', ''),
            'supplier': po.supplier,
            'amount': float(po.total_amount) if po.total_amount else 0,
            'tax': float(po.total_tax) if po.total_tax else 0,
        })

    return JsonResponse({
        'found': bool(pos_list),
        'pos': pos_list
    })
