import pandas as pd
from django.shortcuts import render, redirect
from django.http import HttpResponse
from invoice_reader_app.model_invoice import Supplier, InvoiceItem, ProductName
from django.core.paginator import Paginator

def product_names_list(request):
    search_name = request.GET.get("search_name", "")
    product_names = ProductName.objects.all().order_by("ten_hang")
    if search_name:
        product_names = product_names.filter(ten_hang__icontains=search_name).order_by("ten_hang")

    from django.core.paginator import Paginator
    paginator = Paginator(product_names, 15)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)  # ✅ sửa tên biến

    # Xử lý query string để giữ filter khi đổi page
    query_params = request.GET.copy()
    query_params.pop('page', None)  # Xóa page cũ
    query_string = query_params.urlencode()

    return render(request, "product_names.html", {
        "product_names": page_obj,        # ✅ dùng page_obj
        "search_name": search_name,
        "query_params": query_string,
    })

import pandas as pd
from django.shortcuts import redirect
from django.contrib import messages
from invoice_reader_app.model_invoice import ProductName

def product_names_import_excel(request):
    if request.method != "POST" or "excel_file" not in request.FILES:
        messages.error(request, "❌ Không có file Excel nào được chọn!")
        return redirect("product_names_list")

    excel_file = request.FILES["excel_file"]

    try:
        # Đọc file Excel
        df = pd.read_excel(excel_file)

        # Chuẩn hóa tên cột, loại bỏ dòng trống
        df = df.rename(columns=lambda x: x.strip())
        df = df.dropna(subset=['Tên hàng hóa', 'Tên gọi chung'])

        imported_count = 0
        for _, row in df.iterrows():
            ten_hang = str(row['Tên hàng hóa']).strip()
            ten_goi_chung = str(row['Tên gọi chung']).strip()

            if not ten_hang or not ten_goi_chung:
                continue

            # Update nếu tồn tại, tạo mới nếu chưa có
            ProductName.objects.update_or_create(
                ten_hang=ten_hang,
                defaults={'ten_goi_chung': ten_goi_chung}
            )
            imported_count += 1

        messages.success(request, f"✅ Đã nhập dữ liệu thành công {imported_count} dòng!")

    except Exception as e:
        messages.error(request, f"❌ Lỗi khi import: {e}")

    return redirect("product_names_list")



# 📥 Export Excel
def product_names_export_excel(request):
    qs = ProductName.objects.all().values("ten_hang", "ten_goi_chung")
    df = pd.DataFrame(list(qs))

    response = HttpResponse(content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = 'attachment; filename="product_names.xlsx"'
    df.to_excel(response, index=False)
    return response



def product_names_edit(request, pk):  # phải có 'pk' hoặc tên giống URL
    product = ProductName.objects.get(pk=pk)

    if request.method == "POST":
        product.ten_hang = request.POST.get("ten_hang")
        product.ten_goi_chung = request.POST.get("ten_goi_chung")
        product.save()
        return redirect('product_names_list')

    return render(request, "product_names_edit.html", {"product": product})
