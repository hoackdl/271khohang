from django.http import JsonResponse
from django.db.models import Q
from invoice_reader_app.model_invoice import ProductName
from django.contrib.auth.decorators import login_required


@login_required
def api_products_search_v2(request):

    search = request.GET.get("q", "").strip()

    if not search:
        return JsonResponse({
            "count": 0,
            "results": []
        })

    products = (
        ProductName.objects
        .filter(
            Q(sku__icontains=search) |
            Q(ten_hang__icontains=search) |
            Q(ten_goi_chung__icontains=search)
        )
        .values(
            "sku",
            "ten_hang",
            "ten_goi_chung",
            "dvt",
        )[:20]
    )

    results = []

    for p in products:

        results.append({
            "sku": p["sku"] or "",
            "ten_hang": p["ten_hang"] or "",
            "ten_goi_chung": p["ten_goi_chung"] or "",
            "dvt": p["dvt"] or "",
        })

    return JsonResponse({
        "count": len(results),
        "results": results
    })


@login_required
def api_products_search_v2(request):

    search = request.GET.get("q", "").strip()

    if not search:
        return JsonResponse({
            "count": 0,
            "results": []
        })

    products = (
        ProductName.objects
        .filter(
            Q(sku__icontains=search) |
            Q(ten_hang__icontains=search) |
            Q(ten_goi_chung__icontains=search)
        )
        .values(
            "sku",
            "ten_hang",
            "ten_goi_chung",
            "dvt",
        )
        .order_by("sku")[:20]
    )

    results = []

    for p in products:

        results.append({
            "sku": p["sku"] or "",
            "ten_hang": p["ten_hang"] or "",
            "ten_goi_chung": p["ten_goi_chung"] or "",
            "dvt": p["dvt"] or "",
        })

    return JsonResponse({
        "count": len(results),
        "results": results
    })
