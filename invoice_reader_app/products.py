from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum, FloatField, Value, Q
from django.db.models.functions import Coalesce
from invoice_reader_app.model_invoice import Supplier, InvoiceItem
from django.http import HttpResponse
import pandas as pd

# ===============================
# Hàm chung để lọc & tổng hợp sản phẩm
# ===============================
def get_filtered_products(search_product="", search_supplier=""):
    # Lọc nhà cung cấp
    suppliers = Supplier.objects.filter(phan_loai="Cung cấp hàng hoá")
    if search_supplier:
        for word in search_supplier.split():
            suppliers = suppliers.filter(
                Q(ten_dv_ban__icontains=word) | Q(ma_so_thue__icontains=word)
            )
    supplier_tax_ids = suppliers.values_list("ma_so_thue", flat=True)

    # Lọc sản phẩm
    products = InvoiceItem.objects.filter(
        invoice__ma_so_thue__in=supplier_tax_ids, so_luong__gt=0
    )
    if search_product:
        for word in search_product.split():
            products = products.filter(
                Q(ten_hang__icontains=word) | Q(ten_goi_chung__icontains=word)
            )

    # Gộp nhóm và tính toán
    products = (
        products
        .values("ten_hang", "ten_goi_chung")
        .annotate(
            total_so_luong=Sum("so_luong"),
            total_thanh_tien=Sum("thanh_tien"),
            total_tien_thue=Sum("tien_thue"),
            avg_don_gia=Coalesce(
                Sum("thanh_tien") / Sum("so_luong"),
                Value(0),
                output_field=FloatField()
            )
        )
        .order_by("ten_hang")
    )
    return products

# ===============================
# View hiển thị sản phẩm + phân trang
# ===============================
def products_view(request):
    search_product = request.GET.get("search_product", "").strip()
    search_supplier = request.GET.get("search_supplier", "").strip()

    products = get_filtered_products(search_product, search_supplier)

    paginator = Paginator(products, 10)
    page_number = request.GET.get("product_page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "products": page_obj,
        "search_product": search_product,
        "search_supplier": search_supplier,
        "query_params": request.GET.urlencode(),
    }
    return render(request, "products.html", context)

# ===============================
# View xuất Excel
# ===============================
def export_products_excel(request):
    search_product = request.GET.get("search_product", "").strip()
    search_supplier = request.GET.get("search_supplier", "").strip()

    products = get_filtered_products(search_product, search_supplier)

    # Chuyển sang list để tạo DataFrame
    data = []
    for item in products:
        data.append({
            "Tên hàng hóa": item['ten_hang'],
            "Tên gọi chung": item['ten_goi_chung'],
            "Tổng số lượng": item['total_so_luong'],
            "Đơn giá TB": item['avg_don_gia'],
            "Tổng tiền": item['total_thanh_tien'],
            "Tổng tiền thuế": item['total_tien_thue'],
            "Thanh toán": item['total_thanh_tien'] + item['total_tien_thue']
        })

    df = pd.DataFrame(data)

    # Tạo file Excel
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="danh_muc_hang_hoa.xlsx"'
    df.to_excel(response, index=False)
    return response

import pandas as pd
from django.contrib import messages
from django.shortcuts import redirect
from invoice_reader_app.model_invoice import InvoiceItem

def import_products_excel(request):
    if request.method == "POST" and request.FILES.get("excel_file"):
        excel_file = request.FILES["excel_file"]
        try:
            df = pd.read_excel(excel_file)

            # Kiểm tra cột bắt buộc có trong file Excel
            if not {"Tên hàng hóa", "Tên gọi chung"}.issubset(df.columns):
                messages.error(request, "❌ File Excel phải có cột 'Tên hàng hóa' và 'Tên gọi chung'.")
                return redirect("products")

            updated_count = 0
            not_found = []

            for _, row in df.iterrows():
                ten_hang = str(row.get("Tên hàng hóa", "")).strip()
                ten_goi_chung = str(row.get("Tên gọi chung", "")).strip()

                if not ten_hang:
                    continue

                # Cập nhật tất cả InvoiceItem có tên hàng trùng
                items = InvoiceItem.objects.filter(ten_hang__iexact=ten_hang)
                if items.exists():
                    items.update(ten_goi_chung=ten_goi_chung)
                    updated_count += items.count()
                else:
                    not_found.append(ten_hang)

            msg = f"✅ Cập nhật thành công {updated_count} dòng."
            if not_found:
                msg += f" ⚠️ Không tìm thấy {len(not_found)} hàng: {', '.join(not_found[:5])}"  # chỉ hiển thị 5 cái đầu
            messages.success(request, msg)

        except Exception as e:
            messages.error(request, f"❌ Lỗi khi nhập file: {str(e)}")

    return redirect("products")
