import openpyxl
from io import BytesIO
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import HttpResponse
from invoice_reader_app.model_invoice import ProductName, Brand, ProductLevel, ProductType
from django.db import models
from .forms import ProductForm

from django.core.paginator import Paginator
from django.shortcuts import render
from django.db import models

from invoice_reader_app.model_invoice import (
    ProductName,
    ProductGroup,
)
from django.db import models
from django.core.paginator import Paginator
from django.shortcuts import render




# --- Import Excel ---
import openpyxl
from django.contrib import messages
from django.shortcuts import redirect
import openpyxl
from django.shortcuts import redirect
from django.contrib import messages
from invoice_reader_app.model_invoice import ProductName

def products_import_excel(request):
    """
    Import danh mục hàng hóa từ Excel (.xlsx, .xls)
    - File chỉ có 3 cột: SKU | Tên hàng | Tên gọi chung
    - Nhóm hàng sẽ được gán mặc định nếu file không có cột nhóm
    """
    DEFAULT_NHOM_HANG = 'HH'  # Giá trị mặc định, thay theo NHOM_HANG_CHOICES

    if request.method == 'POST' and request.FILES.get('excel_file'):
        print("Request method:", request.method)
        print("FILES:", request.FILES)

        file = request.FILES['excel_file']
        wb = openpyxl.load_workbook(file)
        ws = wb.active  # Lấy sheet đầu tiên

        try:
            wb = openpyxl.load_workbook(file)
            ws = wb.active

            total_rows = 0
            created_count = 0
            skipped_count = 0

            for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):

                print(row)

                sku, ten_hang, ten_goi_chung = row[:3]

                # Bỏ qua dòng nếu thiếu tên hàng
                if not ten_hang or not str(ten_hang).strip():
                    continue

                total_rows += 1

                sku_val = str(sku).strip() if sku else ''
                ten_hang_val = str(ten_hang).strip()
                ten_goi_chung_val = str(ten_goi_chung).strip() if ten_goi_chung else ''

                # Kiểm tra trùng lặp
                if ProductName.objects.filter(
                    sku__iexact=sku_val,
                    ten_hang__iexact=ten_hang_val,
                    ten_goi_chung__iexact=ten_goi_chung_val
                ).exists():
                    skipped_count += 1
                    continue

                # Tạo sản phẩm mới với nhóm hàng mặc định
                ProductName.objects.create(
                    sku=sku_val,
                    ten_hang=ten_hang_val,
                    ten_goi_chung=ten_goi_chung_val,
                    nhom_hang=DEFAULT_NHOM_HANG
                )
                created_count += 1

            messages.success(
                request,
                f"Đã xử lý {total_rows} dòng, tạo mới {created_count}, bỏ qua {skipped_count} trùng."
            )

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messages.error(request, f"Lỗi khi import Excel: {str(e)}")

    else:
        messages.error(request, "Vui lòng chọn file Excel trước khi nhập.")

    return redirect('product_dmhh')




# --- Export Excel (tên hàng duy nhất) ---
def products_export_excel(request):
    search_product = request.GET.get('search_product', '').strip()
    products_qs = ProductName.objects.all()
    if search_product:
        products_qs = products_qs.filter(
            models.Q(ten_hang__icontains=search_product) |
            models.Q(ten_goi_chung__icontains=search_product) |
            models.Q(sku__icontains=search_product)
        )

    # Lọc tên hàng duy nhất
    unique_names = {}
    for product in products_qs:
        if product.ten_hang not in unique_names:
            unique_names[product.ten_hang] = product

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh mục hàng hóa"

    # Header
    ws.append(["TT", "SKU", "Tên hàng hóa", "Tên gọi chung"])

    # Dữ liệu
    for idx, product in enumerate(unique_names.values(), start=1):
        ws.append([idx, product.sku, product.ten_hang, product.ten_goi_chung or ''])

    # Lưu file
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=product_dmhh.xlsx'
    return response


def delete_all_products(request):
    if request.method == 'POST':
        count = ProductName.objects.count()
        ProductName.objects.all().delete()
        messages.success(request, f"Đã xóa toàn bộ {count} sản phẩm trong danh mục.")
    else:
        messages.error(request, "Phải gửi POST mới được phép xóa.")
    return redirect('product_dmhh')

def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            sku = form.cleaned_data.get('sku', '').strip()
            ten_hang = form.cleaned_data.get('ten_hang', '').strip()
            ten_goi_chung = form.cleaned_data.get('ten_goi_chung', '').strip()

            # Kiểm tra trùng
            if ProductName.objects.filter(
                sku__iexact=sku,
                ten_hang__iexact=ten_hang,
                ten_goi_chung__iexact=ten_goi_chung
            ).exists():
                messages.warning(request, f"Sản phẩm {ten_hang} đã tồn tại, không thêm được.")
            else:
                ProductName.objects.create(
                    sku=sku,
                    ten_hang=ten_hang,
                    ten_goi_chung=ten_goi_chung
                )
                messages.success(request, f"Đã thêm sản phẩm {ten_hang} thành công.")
            return redirect('product_dmhh')
    else:
        form = ProductForm()

    return render(request, 'product_add_hh.html', {'form': form})


from django.shortcuts import render, get_object_or_404, redirect



# 11/08/2026

def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)

        if form.is_valid():
            sku = form.cleaned_data.get('sku', '').strip()
            ten_hang = form.cleaned_data.get('ten_hang', '').strip()
            ten_goi_chung = form.cleaned_data.get(
                'ten_goi_chung', ''
            ).strip()

            # Kiểm tra trùng
            if ProductName.objects.filter(
                sku__iexact=sku,
                ten_hang__iexact=ten_hang,
                ten_goi_chung__iexact=ten_goi_chung
            ).exists():

                messages.warning(
                    request,
                    f"Sản phẩm {ten_hang} đã tồn tại, không thêm được."
                )

            else:
                product = form.save(commit=False)

                product.sku = sku
                product.ten_hang = ten_hang
                product.ten_goi_chung = ten_goi_chung

                product.save()

                messages.success(
                    request,
                    f"Đã thêm sản phẩm {ten_hang} thành công."
                )

            return redirect('product_dmhh')

    else:
        form = ProductForm()

    return render(
        request,
        'product_add_hh.html',
        {'form': form}
    )

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from invoice_reader_app.model_invoice import (
    ProductName,
    ProductGroup,
)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from invoice_reader_app.model_invoice import ProductName, ProductGroup
from invoice_reader_app.models_activitytype import ActivityType


def edit_product_dmhh(request, product_id):
    product = get_object_or_404(
        ProductName,
        id=product_id
    )

    nhom_hang_list = ProductGroup.objects.filter(
        is_active=True
    ).order_by("name")

    activity_type_list = ActivityType.objects.filter(
        is_active=True
    ).order_by("code")

    if request.method == "POST":

        product.sku = request.POST.get(
            "sku",
            product.sku or ""
        ).strip()

        product.ten_hang = request.POST.get(
            "ten_hang",
            product.ten_hang or ""
        ).strip()

        product.ten_goi_chung = request.POST.get(
            "ten_goi_chung",
            product.ten_goi_chung or ""
        ).strip()

        # =========================
        # NHÓM HÀNG
        # =========================

        nhom_hang_id = request.POST.get("nhom_hang")

        if nhom_hang_id:
            try:
                group = ProductGroup.objects.get(
                    id=nhom_hang_id,
                    is_active=True
                )

                product.nhom_hang = group

            except ProductGroup.DoesNotExist:
                messages.error(
                    request,
                    "Nhóm hàng không hợp lệ."
                )

                return render(
                    request,
                    "edit_product_dmhh.html",
                    {
                        "product": product,
                        "nhom_hang_list": nhom_hang_list,
                        "activity_type_list": activity_type_list,
                    }
                )
        else:
            product.nhom_hang = None

        # =========================
        # LOẠI HÌNH HOẠT ĐỘNG
        # =========================

        activity_type_id = request.POST.get(
            "activity_type"
        )

        if activity_type_id:
            try:
                activity = ActivityType.objects.get(
                    id=activity_type_id,
                    is_active=True
                )

                product.activity_type = activity

            except ActivityType.DoesNotExist:
                messages.error(
                    request,
                    "Loại hình hoạt động không hợp lệ."
                )

                return render(
                    request,
                    "edit_product_dmhh.html",
                    {
                        "product": product,
                        "nhom_hang_list": nhom_hang_list,
                        "activity_type_list": activity_type_list,
                    }
                )
        else:
            product.activity_type = None

        product.save()

        messages.success(
            request,
            "Cập nhật sản phẩm thành công."
        )

        return redirect("product_dmhh")

    return render(
        request,
        "edit_product_dmhh.html",
        {
            "product": product,
            "nhom_hang_list": nhom_hang_list,
            "activity_type_list": activity_type_list,
        }
    )

from django.contrib import messages
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)




def edit_product_dmhh(request, product_id):

    product = get_object_or_404(
        ProductName,
        id=product_id
    )

    # ==================================================
    # DANH MỤC
    # ==================================================

    nhom_hang_list = (
        ProductGroup.objects
        .filter(is_active=True)
        .order_by("name")
    )

    activity_type_list = (
        ActivityType.objects
        .filter(is_active=True)
        .order_by("code")
    )

    brand_list = (
        Brand.objects
        .filter(is_active=True)
        .order_by("name")
    )

    product_type_list = (
        ProductType.objects
        .filter(is_active=True)
        .order_by("name")
    )

    product_level_list = (
        ProductLevel.objects
        .filter(is_active=True)
        .order_by("name")
    )

    # ==================================================
    # POST
    # ==================================================

    if request.method == "POST":

        # ==================================================
        # THÔNG TIN CƠ BẢN
        # ==================================================

        product.sku = request.POST.get(
            "sku",
            product.sku or ""
        ).strip()

        product.ten_hang = request.POST.get(
            "ten_hang",
            product.ten_hang or ""
        ).strip()

        product.ten_goi_chung = request.POST.get(
            "ten_goi_chung",
            product.ten_goi_chung or ""
        ).strip()

        product.ten_goi_xuat = request.POST.get(
            "ten_goi_xuat",
            product.ten_goi_xuat or ""
        ).strip()

        product.dvt = request.POST.get(
            "dvt",
            product.dvt or ""
        ).strip()

        # ==================================================
        # NHÓM HÀNG
        # ==================================================

        nhom_hang_id = request.POST.get(
            "nhom_hang"
        )

        if nhom_hang_id:

            try:

                group = ProductGroup.objects.get(
                    id=nhom_hang_id,
                    is_active=True
                )

                product.nhom_hang = group

            except ProductGroup.DoesNotExist:

                messages.error(
                    request,
                    "Nhóm hàng không hợp lệ."
                )

                return render(
                    request,
                    "edit_product_dmhh.html",
                    {
                        "product": product,
                        "nhom_hang_list": nhom_hang_list,
                        "activity_type_list": activity_type_list,
                        "brand_list": brand_list,
                        "product_type_list": product_type_list,
                        "product_level_list": product_level_list,
                    }
                )

        else:

            product.nhom_hang = None

        # ==================================================
        # LOẠI HÌNH HOẠT ĐỘNG
        # ==================================================

        activity_type_id = request.POST.get(
            "activity_type"
        )

        if activity_type_id:

            try:

                activity = ActivityType.objects.get(
                    id=activity_type_id,
                    is_active=True
                )

                product.activity_type = activity

            except ActivityType.DoesNotExist:

                messages.error(
                    request,
                    "Loại hình hoạt động không hợp lệ."
                )

                return render(
                    request,
                    "edit_product_dmhh.html",
                    {
                        "product": product,
                        "nhom_hang_list": nhom_hang_list,
                        "activity_type_list": activity_type_list,
                        "brand_list": brand_list,
                        "product_type_list": product_type_list,
                        "product_level_list": product_level_list,
                    }
                )

        else:

            product.activity_type = None

        # ==================================================
        # HÃNG
        # ==================================================

        brand_id = request.POST.get(
            "brand"
        )

        if brand_id:

            try:

                brand = Brand.objects.get(
                    id=brand_id,
                    is_active=True
                )

                product.brand = brand

            except Brand.DoesNotExist:

                messages.error(
                    request,
                    "Hãng không hợp lệ."
                )

                return render(
                    request,
                    "edit_product_dmhh.html",
                    {
                        "product": product,
                        "nhom_hang_list": nhom_hang_list,
                        "activity_type_list": activity_type_list,
                        "brand_list": brand_list,
                        "product_type_list": product_type_list,
                        "product_level_list": product_level_list,
                    }
                )

        else:

            product.brand = None

        # ==================================================
        # PHÂN LOẠI
        # ==================================================

        product_type_id = request.POST.get(
            "product_type"
        )

        if product_type_id:

            try:

                product_type = ProductType.objects.get(
                    id=product_type_id,
                    is_active=True
                )

                product.product_type = product_type

            except ProductType.DoesNotExist:

                messages.error(
                    request,
                    "Phân loại không hợp lệ."
                )

                return render(
                    request,
                    "edit_product_dmhh.html",
                    {
                        "product": product,
                        "nhom_hang_list": nhom_hang_list,
                        "activity_type_list": activity_type_list,
                        "brand_list": brand_list,
                        "product_type_list": product_type_list,
                        "product_level_list": product_level_list,
                    }
                )

        else:

            product.product_type = None

        # ==================================================
        # LOẠI HÀNG
        # ==================================================

        product_level_id = request.POST.get(
            "product_level"
        )

        if product_level_id:

            try:

                product_level = ProductLevel.objects.get(
                    id=product_level_id,
                    is_active=True
                )

                product.product_level = product_level

            except ProductLevel.DoesNotExist:

                messages.error(
                    request,
                    "Loại hàng không hợp lệ."
                )

                return render(
                    request,
                    "edit_product_dmhh.html",
                    {
                        "product": product,
                        "nhom_hang_list": nhom_hang_list,
                        "activity_type_list": activity_type_list,
                        "brand_list": brand_list,
                        "product_type_list": product_type_list,
                        "product_level_list": product_level_list,
                    }
                )

        else:

            product.product_level = None

        # ==================================================
        # LƯU
        # ==================================================

        product.save()

        messages.success(
            request,
            "Cập nhật sản phẩm thành công."
        )

        return redirect(
            "product_dmhh"
        )

    # ==================================================
    # GET
    # ==================================================

    return render(
        request,
        "edit_product_dmhh.html",
        {
            "product": product,

            "nhom_hang_list":
                nhom_hang_list,

            "activity_type_list":
                activity_type_list,

            "brand_list":
                brand_list,

            "product_type_list":
                product_type_list,

            "product_level_list":
                product_level_list,
        }
    )


from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import render


def product_dmhh(request):

    search_product = request.GET.get("search_product", "").strip()
    nhom_hang = request.GET.get("nhom_hang", "").strip()
    activity_type = request.GET.get("activity_type", "").strip()

    # ==================================================
    # DANH SÁCH SẢN PHẨM
    # ==================================================

    products_qs = ProductName.objects.select_related(
        "nhom_hang",
        "activity_type",
    )

    # ==================================================
    # TÌM KIẾM
    # ==================================================

    if search_product:
        products_qs = products_qs.filter(
            models.Q(ten_hang__icontains=search_product)
            |
            models.Q(ten_goi_chung__icontains=search_product)
            |
            models.Q(sku__icontains=search_product)
        )

    # ==================================================
    # LỌC NHÓM HÀNG
    # ==================================================

    if nhom_hang:
        products_qs = products_qs.filter(
            nhom_hang_id=nhom_hang
        )

    # ==================================================
    # LỌC LOẠI HÌNH HOẠT ĐỘNG
    # ==================================================

    if activity_type:
        products_qs = products_qs.filter(
            activity_type_id=activity_type
        )

    # ==================================================
    # SẮP XẾP
    # ==================================================

    products_qs = products_qs.order_by("id")

    # ==================================================
    # DANH SÁCH NHÓM HÀNG
    # ==================================================

    nhom_hang_list = ProductGroup.objects.filter(
        is_active=True
    ).select_related(
        "activity_type"
    ).order_by("name")

    # ==================================================
    # DANH SÁCH LOẠI HÌNH HOẠT ĐỘNG
    # ==================================================

    activity_type_list = ActivityType.objects.filter(
        is_active=True
    ).order_by("code")

    # ==================================================
    # PHÂN TRANG
    # ==================================================

    per_page = request.GET.get("per_page", "10")

    if per_page == "all":
        per_page_value = products_qs.count() or 1
    else:
        try:
            per_page_value = int(per_page)
        except (ValueError, TypeError):
            per_page_value = 10

        # Chống nhập số quá lớn / không hợp lệ
        if per_page_value not in [10, 20, 50, 100]:
            per_page_value = 10

    paginator = Paginator(
        products_qs,
        per_page_value
    )

    page_number = request.GET.get("page", 1)

    page_obj = paginator.get_page(page_number)
    # ==================================================
    # DANH SÁCH SỐ TRANG HIỂN THỊ
    # ==================================================

    current_page = page_obj.number
    total_pages = paginator.num_pages

    page_numbers = []

    for num in range(1, total_pages + 1):

        if (
            num == 1
            or num == total_pages
            or current_page - 2 <= num <= current_page + 2
        ):
            page_numbers.append(num)

    # ==================================================
    # GIỮ QUERY SEARCH + FILTER KHI CHUYỂN TRANG
    # ==================================================

    query_params = request.GET.copy()

    if "page" in query_params:
        query_params.pop("page")

    # ==================================================
    # CONTEXT
    # ==================================================

    context = {
        "products": page_obj,
        "data": page_obj,

        "search_product": search_product,

        "nhom_hang": nhom_hang,
        "nhom_hang_list": nhom_hang_list,

        "activity_type": activity_type,
        "activity_type_list": activity_type_list,

        "per_page": per_page,

        "query_params": query_params.urlencode(),

        "label": "hàng hoá",

        # Thông tin phân trang
        "page_obj": page_obj,
        "paginator": paginator,
        "page_numbers": page_numbers,
    }

    return render(
        request,
        "product_dmhh.html",
        context
    )



from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import render


def product_dmhh(request):

    search_product = request.GET.get(
        "search_product", ""
    ).strip()

    nhom_hang = request.GET.get(
        "nhom_hang", ""
    ).strip()

    activity_type = request.GET.get(
        "activity_type", ""
    ).strip()

    brand = request.GET.get(
        "brand", ""
    ).strip()

    product_type = request.GET.get(
        "product_type", ""
    ).strip()

    product_level = request.GET.get(
        "product_level", ""
    ).strip()

    # ==================================================
    # DANH SÁCH SẢN PHẨM
    # ==================================================

    products_qs = ProductName.objects.select_related(
        "nhom_hang",
        "activity_type",
        "brand",
        "product_type",
        "product_level",
    )

    # ==================================================
    # TÌM KIẾM
    # ==================================================

    if search_product:
        products_qs = products_qs.filter(
            models.Q(
                ten_hang__icontains=search_product
            )
            |
            models.Q(
                ten_goi_chung__icontains=search_product
            )
            |
            models.Q(
                sku__icontains=search_product
            )
        )

    # ==================================================
    # LỌC NHÓM HÀNG
    # ==================================================

    if nhom_hang:
        products_qs = products_qs.filter(
            nhom_hang_id=nhom_hang
        )

    # ==================================================
    # LỌC LOẠI HÌNH HOẠT ĐỘNG
    # ==================================================

    if activity_type:
        products_qs = products_qs.filter(
            activity_type_id=activity_type
        )

    # ==================================================
    # LỌC HÃNG
    # ==================================================

    if brand:
        products_qs = products_qs.filter(
            brand_id=brand
        )

    # ==================================================
    # LỌC PHÂN LOẠI
    # ==================================================

    if product_type:
        products_qs = products_qs.filter(
            product_type_id=product_type
        )

    # ==================================================
    # LỌC LOẠI HÀNG
    # ==================================================

    if product_level:
        products_qs = products_qs.filter(
            product_level_id=product_level
        )

    # ==================================================
    # SẮP XẾP
    # ==================================================

    products_qs = products_qs.order_by("id")

    # ==================================================
    # DANH SÁCH NHÓM HÀNG
    # ==================================================

    nhom_hang_list = (
        ProductGroup.objects
        .filter(is_active=True)
        .select_related("activity_type")
        .order_by("name")
    )

    # ==================================================
    # DANH SÁCH LOẠI HÌNH HOẠT ĐỘNG
    # ==================================================

    activity_type_list = (
        ActivityType.objects
        .filter(is_active=True)
        .order_by("code")
    )

    # ==================================================
    # DANH SÁCH HÃNG
    # ==================================================

    brand_list = (
        Brand.objects
        .filter(is_active=True)
        .order_by("name")
    )

    # ==================================================
    # DANH SÁCH PHÂN LOẠI
    # ==================================================

    product_type_list = (
        ProductType.objects
        .filter(is_active=True)
        .order_by("name")
    )

    # ==================================================
    # DANH SÁCH LOẠI HÀNG
    # ==================================================

    product_level_list = (
        ProductLevel.objects
        .filter(is_active=True)
        .order_by("name")
    )

    # ==================================================
    # PHÂN TRANG
    # ==================================================

    per_page = request.GET.get(
        "per_page",
        "10"
    )

    if per_page == "all":

        per_page_value = (
            products_qs.count() or 1
        )

    else:

        try:
            per_page_value = int(per_page)

        except (ValueError, TypeError):
            per_page_value = 10

        if per_page_value not in [
            10,
            20,
            50,
            100
        ]:
            per_page_value = 10

    paginator = Paginator(
        products_qs,
        per_page_value
    )

    page_number = request.GET.get(
        "page",
        1
    )

    page_obj = paginator.get_page(
        page_number
    )

    # ==================================================
    # GIỮ SEARCH + FILTER KHI CHUYỂN TRANG
    # ==================================================

    query_params = request.GET.copy()

    if "page" in query_params:
        query_params.pop("page")
        
    current_page = page_obj.number
    total_pages = paginator.num_pages

    start_page = max(current_page - 2, 1)
    end_page = min(current_page + 2, total_pages)

    page_numbers = range(start_page, end_page + 1)

    # ==================================================
    # CONTEXT
    # ==================================================

    context = {
        "products": page_obj,
        "data": page_obj,

        "search_product": search_product,

        "nhom_hang": nhom_hang,
        "nhom_hang_list": nhom_hang_list,

        "activity_type": activity_type,
        "activity_type_list": activity_type_list,

        "brand": brand,
        "brand_list": brand_list,

        "product_type": product_type,
        "product_type_list": product_type_list,

        "product_level": product_level,
        "product_level_list": product_level_list,

        "per_page": per_page,

        "query_params": query_params.urlencode(),

        "label": "hàng hoá",

        "page_obj": page_obj,
        "paginator": paginator,

        "page_numbers": page_numbers,
    }


    return render(
        request,
        "product_dmhh.html",
        context
    )





# ==================================================
# TẠO HÃNG
# ==================================================

def brand_create(request):

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        if not name:

            messages.error(
                request,
                "Vui lòng nhập tên hãng."
            )

            return render(
                request,
                "brand_create.html"
            )

        if Brand.objects.filter(
            name__iexact=name
        ).exists():

            messages.error(
                request,
                f"Hãng '{name}' đã tồn tại."
            )

            return render(
                request,
                "brand_create.html",
                {
                    "name": name
                }
            )

        Brand.objects.create(
            name=name,
            is_active=True
        )

        messages.success(
            request,
            f"Đã tạo hãng '{name}' thành công."
        )

        return redirect(
            "product_dmhh"
        )

    return render(
        request,
        "brand_create.html"
    )


# ==================================================
# TẠO PHÂN LOẠI
# ==================================================

def product_type_create(request):

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        if not name:

            messages.error(
                request,
                "Vui lòng nhập tên phân loại."
            )

            return render(
                request,
                "product_type_create.html"
            )

        if ProductType.objects.filter(
            name__iexact=name
        ).exists():

            messages.error(
                request,
                f"Phân loại '{name}' đã tồn tại."
            )

            return render(
                request,
                "product_type_create.html",
                {
                    "name": name
                }
            )

        ProductType.objects.create(
            name=name,
            is_active=True
        )

        messages.success(
            request,
            f"Đã tạo phân loại '{name}' thành công."
        )

        return redirect(
            "product_dmhh"
        )

    return render(
        request,
        "product_type_create.html"
    )


# ==================================================
# TẠO LOẠI HÀNG
# ==================================================

def product_level_create(request):

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        if not name:

            messages.error(
                request,
                "Vui lòng nhập tên loại hàng."
            )

            return render(
                request,
                "product_level_create.html"
            )

        if ProductLevel.objects.filter(
            name__iexact=name
        ).exists():

            messages.error(
                request,
                f"Loại hàng '{name}' đã tồn tại."
            )

            return render(
                request,
                "product_level_create.html",
                {
                    "name": name
                }
            )

        ProductLevel.objects.create(
            name=name,
            is_active=True
        )

        messages.success(
            request,
            f"Đã tạo loại hàng '{name}' thành công."
        )

        return redirect(
            "product_dmhh"
        )

    return render(
        request,
        "product_level_create.html"
    )
