from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum, FloatField, ExpressionWrapper, Q
from invoice_reader_app.model_invoice import Customer, InvoiceItem
from django.views.decorators.csrf import csrf_protect

# views.py


def customer_products(request):
    search_product = request.GET.get('search_product', '')
    search_customer = request.GET.get('search_customer', '')

    customers = Customer.objects.all()
    if search_customer:
        customers = customers.filter(
            Q(ten_khach_hang__icontains=search_customer) |
            Q(ma_so_thue__icontains=search_customer)
        )

    customer_tax_ids = customers.values_list('ma_so_thue', flat=True)

    products = InvoiceItem.objects.filter(
        invoice__ma_so_thue_mua__in=customer_tax_ids,
        invoice__loai_hd='XUAT',
        so_luong__gt=0,
        ten_goi_chung__isnull=False,
    ).exclude(ten_goi_chung='')

    products = products.values(
        'id',
        'invoice__ten_nguoi_mua',
        'invoice__ma_so_thue_mua',
        'ten_hang',
        'ten_goi_chung',
        'ten_goi_xuat',
        'sku',  # ✅ thêm SKU
        'invoice__loai_hd',
        'invoice__supplier__phan_loai'
    ).annotate(
        total_so_luong=Sum('so_luong'),
        total_thanh_tien=Sum('thanh_tien'),
        total_tien_thue=Sum('tien_thue'),
        avg_don_gia=ExpressionWrapper(
            (Sum('thanh_tien') + Sum('tien_thue')) / Sum('so_luong'),
            output_field=FloatField()
        )
    ).order_by('invoice__ten_nguoi_mua', 'ten_hang')

    # --- Phân trang ---
    page_size = 10
    page_number = request.GET.get('product_page', 1)
    paginator = Paginator(products, page_size)
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'search_product': search_product,
        'search_customer': search_customer,
    }
    return render(request, 'customer_products.html', context)



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from invoice_reader_app.model_invoice import InvoiceItem

def customer_products_edit(request, pk):
    """
    View chỉnh sửa một hàng hóa (InvoiceItem)
    """
    item = get_object_or_404(InvoiceItem, pk=pk)

    # 🟢 Lấy danh sách hàng hóa nhập (loại VAO)
    import_items = (
        InvoiceItem.objects
        .filter(invoice__loai_hd='VAO')
        .values_list('ten_hang', flat=True)
        .distinct()
        .order_by('ten_hang')
    )

    if request.method == 'POST':
        item.ten_hang = request.POST.get('ten_hang', item.ten_hang)
        item.dvt = request.POST.get('dvt', item.dvt)
        item.so_luong = float(request.POST.get('so_luong', item.so_luong or 0))
        item.don_gia = float(request.POST.get('don_gia', item.don_gia or 0))
        item.thanh_tien = float(request.POST.get('thanh_tien', item.thanh_tien or 0))
        item.thue_suat = request.POST.get('thue_suat', item.thue_suat)
        item.tien_thue = float(request.POST.get('tien_thue', item.tien_thue or 0))
        item.thanh_toan = float(request.POST.get('thanh_toan', item.thanh_toan or 0))
        item.ten_goi_xuat = request.POST.get('ten_goi_xuat', item.ten_goi_xuat)
        item.ten_goi_chung = request.POST.get('ten_goi_chung', item.ten_goi_chung)

        item.save()
        messages.success(request, "✅ Cập nhật hàng hóa thành công!")
        return redirect('customer_products')

    return render(request, 'customer_products_edit.html', {
        'item': item,
        'import_items': import_items,
    })


import pandas as pd
from django.http import HttpResponse
from invoice_reader_app.model_invoice import InvoiceItem
from django.db.models import Sum, FloatField, ExpressionWrapper

def export_customer_products_excel(request):
    search_product = request.GET.get('search_product', '')
    search_customer = request.GET.get('search_customer', '')

    customers = Customer.objects.all()
    if search_customer:
        customers = customers.filter(
            Q(ten_khach_hang__icontains=search_customer) |
            Q(ma_so_thue__icontains=search_customer)
        )
    customer_tax_ids = customers.values_list('ma_so_thue', flat=True)

    products = InvoiceItem.objects.filter(
        invoice__ma_so_thue_mua__in=customer_tax_ids,
        invoice__loai_hd='XUAT',
        so_luong__gt=0
    )

    if search_product:
        products = products.filter(ten_hang__icontains=search_product)

    products = products.values(
        'invoice__ten_nguoi_mua',
        'invoice__ma_so_thue_mua',
        'ten_hang',
        'ten_goi_chung',
        'ten_goi_xuat'
    ).annotate(
        total_so_luong=Sum('so_luong'),
        total_thanh_tien=Sum('thanh_tien'),
        total_tien_thue=Sum('tien_thue'),
        avg_don_gia=ExpressionWrapper(
            (Sum('thanh_tien') + Sum('tien_thue')) / Sum('so_luong'),
            output_field=FloatField()
        )
    ).order_by('invoice__ten_nguoi_mua', 'ten_hang')

    data = []
    for p in products:
        data.append({
            "Khách hàng": p['invoice__ten_nguoi_mua'],
            "MST khách": p['invoice__ma_so_thue_mua'],
            "Tên hàng": p['ten_hang'],
            "Tên gọi chung": p['ten_goi_chung'],
            "Tên gọi xuất": p['ten_goi_xuat'],
             "SKU": p['sku'],  # ✅ thêm SKU
            "Tổng số lượng": p['total_so_luong'],
            "Đơn giá TB": p['avg_don_gia'],
            "Tổng tiền": p['total_thanh_tien'],
            "Tổng tiền thuế": p['total_tien_thue'],
            "Thanh toán": p['total_thanh_tien'] + p['total_tien_thue']
        })

    df = pd.DataFrame(data)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="customer_products.xlsx"'
    df.to_excel(response, index=False)
    return response
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib import messages
import pandas as pd
from invoice_reader_app.model_invoice import ProductName



# --- Danh sách tên gọi xuất ---
def customer_products_name(request):
    search_name = request.GET.get("search_name", "").strip()
    product_names = ProductName.objects.all().order_by("ten_goi_xuat")

    if search_name:
        # Tìm kiếm theo tên gọi xuất hoặc tên gọi chung
        product_names = product_names.filter(
            Q(ten_goi_xuat__icontains=search_name) |
            Q(ten_goi_chung__icontains=search_name)
        )

    # --- Phân trang ---
    paginator = Paginator(product_names, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "customer_products_name.html", {
        "product_names": page_obj,
        "search_name": search_name,
    })


# --- Import Excel ---
def customer_products_name_import_excel(request):
    if request.method == "POST" and request.FILES.get("excel_file"):
        excel_file = request.FILES["excel_file"]
        try:
            df = pd.read_excel(excel_file)

            required_columns = {"Tên gọi xuất", "Tên gọi chung", "SKU"}  # ✅ thêm SKU
            if not required_columns.issubset(df.columns):
                messages.error(request, "❌ File Excel phải có cột 'Tên gọi xuất', 'Tên gọi chung', và 'SKU'.")
                return redirect("customer_products_name")

            updated_products = 0
            for _, row in df.iterrows():
                ten_goi_xuat = str(row.get("Tên gọi xuất", "")).strip()
                ten_goi_chung = str(row.get("Tên gọi chung", "")).strip()
                sku = str(row.get("SKU", "")).strip() or None
                if not ten_goi_xuat:
                    continue

                ProductName.objects.update_or_create(
                    ten_goi_xuat=ten_goi_xuat,
                    defaults={
                        "ten_goi_chung": ten_goi_chung,
                        "sku": sku,  # ✅ lưu SKU
                    }
                )
                updated_products += 1

            messages.success(request, f"✅ Cập nhật/Thêm thành công {updated_products} dòng.")

        except Exception as e:
            messages.error(request, f"❌ Lỗi khi nhập file: {str(e)}")

    return redirect("customer_products_name")


# --- Xuất Excel ---
from django.http import HttpResponse

def customer_product_names_export_excel(request):
    search_name = request.GET.get("search_name", "")
    qs = ProductName.objects.all().order_by("ten_goi_xuat")

    if search_name:
        qs = qs.filter(ten_goi_xuat__icontains=search_name)

    data = [
        {
            "Tên gọi xuất": p.ten_goi_xuat,
            "Tên gọi chung": p.ten_goi_chung,
            "SKU": p.sku,  # ✅ thêm SKU
        }
        for p in qs
    ]
    df = pd.DataFrame(data)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=ten_goi_xuat.xlsx"
    df.to_excel(response, index=False)
    return response


# --- Sửa ---
def customer_products_name_edit(request, pk):
    product = get_object_or_404(ProductName, pk=pk)

    if request.method == "POST":
        product.ten_goi_xuat = request.POST.get("ten_goi_xuat", product.ten_goi_xuat)
        product.ten_goi_chung = request.POST.get("ten_goi_chung", product.ten_goi_chung)
        product.sku = request.POST.get("sku", product.sku)  # ✅ cập nhật SKU
        product.save()
        messages.success(request, "✅ Cập nhật thành công!")
        return redirect("customer_products_name")

    return render(request, "customer_products_name_edit.html", {"product": product})




# --- Xoá ---
def customer_product_name_delete(request, pk):
    product = get_object_or_404(ProductName, pk=pk)
    product.delete()
    messages.success(request, f"🗑️ Đã xóa '{product.ten_goi_xuat}' thành công!")
    return redirect("customer_products_name")

def customer_product_name_delete_all(request):
    ProductName.objects.all().delete()
    messages.success(request, "🗑️ Đã xóa toàn bộ danh mục tên gọi xuất!")
    return redirect("customer_products_name")
