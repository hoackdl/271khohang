from django.shortcuts import render, redirect
from django.db.models import Q
from urllib.parse import unquote
from django.contrib import messages
from invoice_reader_app.model_invoice import InvoiceItem

def products_edit_view(request, ten_hang):
    # Giải mã tên hàng (vì trong URL nó bị encode)
    ten_hang = unquote(ten_hang).strip()

    # Lọc mềm, không phân biệt hoa thường, bỏ khoảng trắng đầu cuối
    products = InvoiceItem.objects.filter(ten_hang__iexact=ten_hang)

    # Nếu không tìm thấy, hiển thị gợi ý hàng gần giống
    if not products.exists():
        possible = InvoiceItem.objects.filter(ten_hang__icontains=ten_hang)[:10]
        return render(request, "products_edit.html", {
            "products": [],
            "ten_hang": ten_hang,
            "suggested": possible,
        })

    # Nếu POST → cập nhật thông tin
    if request.method == "POST":
        ten_goi_chung_moi = request.POST.get("ten_goi_chung", "").strip()

        for item in products:
            # Cập nhật số lượng
            qty_field = f"so_luong_{item.id}"
            if qty_field in request.POST:
                try:
                    item.so_luong = float(request.POST[qty_field])
                except ValueError:
                    pass

            # Cập nhật tên gọi chung nếu có
            if ten_goi_chung_moi:
                item.ten_goi_chung = ten_goi_chung_moi

            item.save()

        messages.success(request, f"✅ Đã cập nhật thông tin cho '{ten_hang}'")
        return redirect("products")

    # Lấy tên gọi chung (nếu có ít nhất 1 bản ghi)
    ten_goi_chung_hien_tai = products.first().ten_goi_chung or ""

    context = {
        "products": products,
        "ten_hang": ten_hang,
        "ten_goi_chung": ten_goi_chung_hien_tai,
    }
    return render(request, "products_edit.html", context)
