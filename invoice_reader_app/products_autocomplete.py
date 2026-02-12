from django.http import JsonResponse
from django.db.models import Q
from .models_purcharoder import ProductName  # ✅ model chứa dữ liệu hàng hóa
from django.db import models

def products_autocomplete(request):
    """
    API autocomplete cho SKU và Tên gọi chung
    Trả về JSON dạng:
    [
      {"sku": "SP001", "ten_hang": "Bút bi Thiên Long", "ten_goi_chung": "Bút viết"},
      ...
    ]
    """
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse([], safe=False)

    products = ProductName.objects.filter(
        Q(sku__icontains=q) |
        Q(ten_hang__icontains=q) |
        Q(ten_goi_chung__icontains=q)
    ).annotate(
        label=models.functions.Concat(
            models.F("sku"),
            models.Value(" — "),
            models.F("ten_hang"),
            output_field=models.CharField(),
        )
    ).values("sku", "ten_hang", "ten_goi_chung", "label")[:15]

    

    return JsonResponse(list(products), safe=False)


# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .model_invoice import Customer

@require_GET
def customers_autocomplete(request):
    """
    Trả về danh sách khách hàng dựa trên MST (ma_so_thue) query param 'q'
    """
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse([], safe=False)  # Trả về mảng rỗng nếu không có query

    # Lọc khách hàng có MST chứa q (có thể dùng __istartswith để tìm từ đầu)
    customers = Customer.objects.filter(ma_so_thue__icontains=q)[:10]  # Giới hạn 10 kết quả

    # Trả về JSON
    data = [
        {
            "ma_so_thue": c.ma_so_thue,
            "ten_khach_hang": c.ten_khach_hang,
            "dia_chi": c.dia_chi,
        } 
        for c in customers
    ]
    return JsonResponse(data, safe=False)
