# views.py

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from django.db.models import Min, Max, Count

from django.db.models import Min, Max
from django.shortcuts import render

from invoice_reader_app.model_invoice import (
    Invoice,
    InvoiceItem,
    Supplier,
    Brand,
    ProductType,
    ProductLevel,
    ProductName,
)


# ==========================================================
# CHUẨN HÓA TEXT
# ==========================================================

def normalize_text(text):
    if not text:
        return ""

    import unicodedata

    text = str(text).lower().strip()

    text = unicodedata.normalize("NFD", text)

    return "".join(
        c
        for c in text
        if unicodedata.category(c) != "Mn"
    )


# ==========================================================
# BÁO CÁO MUA HÀNG
# ==========================================================

def bao_cao_mua_hang(request):
    # ======================================================
    # NĂM
    # ======================================================

    current_year = request.session.get(
        "fiscal_year",
        datetime.now().year
    )


    # ======================================================
    # CHỈ LẤY NĂM CỦA HÓA ĐƠN MUA VÀO
    # ======================================================

    year_range = (
        Invoice.objects
        .filter(
            loai_hd="VAO"
        )
        .exclude(
            ma_so_thue="0314858906"
        )
        .aggregate(
            min_year=Min("fiscal_year"),
            max_year=Max("fiscal_year"),
        )
    )

    min_year = (
        year_range["min_year"]
        or current_year
    )

    max_year = (
        year_range["max_year"]
        or current_year
    )


    # ======================================================
    # DANH SÁCH NĂM
    # NĂM MỚI NHẤT ĐỨNG ĐẦU
    # ======================================================

    nam_list = sorted(
        set(
            range(
                min_year,
                max_year + 1
            )
        ),
        reverse=True
    )


    # ======================================================
    # NĂM NGƯỜI DÙNG CHỌN
    # ======================================================

    selected_years_raw = request.GET.getlist("nam")

    selected_years = []

    for value in selected_years_raw:

        try:
            year = int(value)

        except (ValueError, TypeError):
            continue

        if year in nam_list and year not in selected_years:
            selected_years.append(year)


    # ======================================================
    # KHÔNG CHỌN NĂM
    # => MẶC ĐỊNH NĂM MỚI NHẤT CÓ DỮ LIỆU
    # ======================================================

    if not selected_years:

        selected_years = [
            max_year
        ]


    # ======================================================
    # SẮP XẾP NĂM ĐƯỢC CHỌN
    # NĂM MỚI NHẤT TRƯỚC
    # ======================================================

    selected_years = sorted(
        selected_years,
        reverse=True
    )


    # ======================================================
    # STRING CHO TEMPLATE
    # ======================================================

    selected_years_str = [
        str(year)
        for year in selected_years
    ]


    # ======================================================
    # DEBUG
    # ======================================================

    print("========== NĂM BÁO CÁO ==========")
    print("current_year =", current_year)
    print("min_year =", min_year)
    print("max_year =", max_year)
    print("nam_list =", nam_list)
    print("selected_years_raw =", selected_years_raw)
    print("selected_years =", selected_years)
    print("=================================")


    # ======================================================
    # FILTER
    # ======================================================

    brand = request.GET.get(
        "brand",
        ""
    ).strip()

    supplier = request.GET.get(
        "supplier",
        ""
    ).strip()



    # ======================================================
    # NẾU KHÔNG CHỌN NĂM
    # => DÙNG NĂM TÀI CHÍNH HIỆN TẠI
    # ======================================================

    if not selected_years:

        selected_years = [
            current_year
        ]


    # ======================================================
    # GIỮ DẠNG STRING CHO TEMPLATE
    # ======================================================

    selected_years_str = [
        str(year)
        for year in selected_years
    ]





    # ======================================================
    # DANH SÁCH HÃNG
    # ======================================================

    brand_list = (
        Brand.objects
        .filter(is_active=True)
        .order_by("name")
    )


    # ======================================================
    # DANH SÁCH NHÀ CUNG CẤP
    # ======================================================

    supplier_list = (
        Supplier.objects
        .exclude(
            ma_so_thue="0314858906"
        )
        .order_by("ten_dv_ban")
    )


    # ======================================================
    # DANH SÁCH LOẠI HÀNG
    #
    # Ví dụ:
    # Cao cấp
    # Trung cấp
    # Phổ thông
    # ======================================================

    level_objects = (
        ProductLevel.objects
        .filter(is_active=True)
        .order_by("name")
    )


    # ======================================================
    # DANH SÁCH PHÂN LOẠI
    #
    # Ví dụ:
    # Trong nhà
    # Ngoài trời
    # ...
    # ======================================================

    type_objects = (
        ProductType.objects
        .filter(is_active=True)
        .order_by("name")
    )


    # ======================================================
    # TẠO COLUMN CHO TEMPLATE
    # ======================================================

    level_columns = [
        {
            "key": f"level_{obj.id}",
            "name": obj.name,
        }
        for obj in level_objects
    ]

    type_columns = [
        {
            "key": f"type_{obj.id}",
            "name": obj.name,
        }
        for obj in type_objects
    ]


    # ======================================================
    # TẠO MAP PRODUCT
    #
    # Ưu tiên:
    # 1. SKU
    # 2. Tên hàng
    # ======================================================

    product_by_sku = {}
    product_by_name = {}

    products = (
        ProductName.objects
        .select_related(
            "brand",
            "product_type",
            "product_level",
        )
        .all()
    )

    for product in products:

        if product.sku:

            sku = product.sku.strip().lower()

            if sku:
                product_by_sku[sku] = product


        if product.ten_hang:

            key = normalize_text(
                product.ten_hang
            )

            if key:
                product_by_name[key] = product


    # ======================================================
    # QUERY INVOICE
    # ======================================================

    invoices = (
        Invoice.objects
        .filter(
            fiscal_year__in=selected_years,
            loai_hd="VAO",
        )
        .exclude(
            ma_so_thue="0314858906"
        )
        .select_related(
            "supplier"
        )
        .prefetch_related(
            "items"
        )
        .order_by(
            "ngay_hd"
        )
    )
    print("========== BAO CAO MUA HANG ==========")
    print("selected_years =", selected_years)
    print("invoice_count =", invoices.count())
    print(
        "invoice_years =",
        list(
            invoices
            .values("fiscal_year")
            .annotate(total=Count("id"))
            .order_by("fiscal_year")
        )
    )


    # ======================================================
    # LỌC NHÀ CUNG CẤP
    # ======================================================

    if supplier:

        try:
            supplier_id = int(supplier)

            supplier_obj = Supplier.objects.filter(
                id=supplier_id
            ).first()

            if supplier_obj and supplier_obj.ma_so_thue:

                invoices = invoices.filter(
                    ma_so_thue=supplier_obj.ma_so_thue
                )

            else:

                invoices = invoices.none()

        except (ValueError, TypeError):

            invoices = invoices.none()


    # ======================================================
    # DATA REPORT
    # ======================================================

    monthly_data = defaultdict(dict)

    quarterly_data = defaultdict(dict)

    yearly_data = defaultdict(dict)


    # ======================================================
    # HÀM TẠO ROW
    # ======================================================

    def create_row():

        row = {
            "tong": Decimal("0"),
            "tc_son_nuoc": Decimal("0"),
            "tc_cao_cap": Decimal("0"),
        }

        # -------------------------------
        # LOẠI HÀNG
        # -------------------------------

        for column in level_columns:

            row[column["key"]] = Decimal("0")


        # -------------------------------
        # PHÂN LOẠI
        # -------------------------------

        for column in type_columns:

            row[column["key"]] = Decimal("0")


        return row

    # ======================================================
    # DUYỆT INVOICE
    # ======================================================

    for invoice in invoices:

        if not invoice.ngay_hd:
            continue

        # QUAN TRỌNG:
        # Năm lấy theo fiscal_year
        year = invoice.fiscal_year

        # Tháng lấy theo ngày hóa đơn
        month = invoice.ngay_hd.month

        quarter = (
            (month - 1) // 3
        ) + 1

        month_key = (
            year,
            month
        )

        quarter_key = (
            year,
            quarter
        )

        year_key = year



        # ==================================================
        # KHỞI TẠO ROW
        # ==================================================

        if month_key not in monthly_data:

            monthly_data[month_key] = create_row()

            monthly_data[month_key]["year"] = year
            monthly_data[month_key]["month"] = month
            monthly_data[month_key]["quarter"] = quarter
            monthly_data[month_key][
                "quarter_name"
            ] = f"Q{quarter}"


        if quarter_key not in quarterly_data:

            quarterly_data[quarter_key] = create_row()

            quarterly_data[quarter_key]["year"] = year
            quarterly_data[quarter_key][
                "quarter"
            ] = quarter

            quarterly_data[quarter_key][
                "quarter_name"
            ] = f"Q{quarter}"


        if year_key not in yearly_data:

            yearly_data[year_key] = create_row()

            yearly_data[year_key][
                "year"
            ] = year


        # ==================================================
        # ITEMS
        # ==================================================

        for item in invoice.items.all():

            amount = (
                item.thanh_tien
                or Decimal("0")
            )

            if not amount:
                continue


            # ==================================================
            # TÌM PRODUCT
            # ==================================================

            product = None


            # -------------------------------
            # 1. TÌM THEO SKU
            # -------------------------------

            if item.sku:

                sku_key = (
                    item.sku
                    .strip()
                    .lower()
                )

                product = product_by_sku.get(
                    sku_key
                )


            # -------------------------------
            # 2. TÌM THEO TÊN
            # -------------------------------

            if not product:

                name_key = normalize_text(
                    item.ten_hang
                )

                product = product_by_name.get(
                    name_key
                )


            # ==================================================
            # BRAND FILTER
            # ==================================================

            if brand:

                if not product:
                    continue

                if not product.brand:
                    continue

                if str(
                    product.brand.id
                ) != str(brand):

                    continue


            # ==================================================
            # THÁNG
            # ==================================================

            mrow = monthly_data[month_key]

            mrow["tong"] += amount


            # ==================================================
            # QUÝ
            # ==================================================

            qrow = quarterly_data[quarter_key]

            qrow["tong"] += amount


            # ==================================================
            # NĂM
            # ==================================================

            yrow = yearly_data[year_key]

            yrow["tong"] += amount


            # ==================================================
            # NHÓM HÀNG
            # ==================================================

            if item.nhom_hang == "son_nuoc":

                mrow["tc_son_nuoc"] += amount
                qrow["tc_son_nuoc"] += amount
                yrow["tc_son_nuoc"] += amount


            # ==================================================
            # LOẠI HÀNG
            # ==================================================

            if product and product.product_level:

                level_key = (
                    f"level_{product.product_level_id}"
                )

                if level_key in mrow:

                    mrow[level_key] += amount


                if level_key in qrow:

                    qrow[level_key] += amount


                if level_key in yrow:

                    yrow[level_key] += amount


                # ------------------------------------------
                # CAO CẤP
                # ------------------------------------------

                level_name = normalize_text(
                    product.product_level.name
                )

                if "cao cap" in level_name:

                    mrow["tc_cao_cap"] += amount

                    qrow["tc_cao_cap"] += amount

                    yrow["tc_cao_cap"] += amount


            # ==================================================
            # PHÂN LOẠI
            # ==================================================

            if product and product.product_type:

                type_key = (
                    f"type_{product.product_type_id}"
                )

                if type_key in mrow:

                    mrow[type_key] += amount


                if type_key in qrow:

                    qrow[type_key] += amount


                if type_key in yrow:

                    yrow[type_key] += amount


    # ======================================================
    # MONTHLY REPORT
    # ======================================================

    monthly_report = []

    for key in sorted(
        monthly_data.keys()
    ):

        row = monthly_data[key]

        # -------------------------------
        # TỶ LỆ CAO CẤP
        # -------------------------------

        if row["tc_son_nuoc"]:

            row["ty_le_cao_cap"] = (
                row["tc_cao_cap"]
                / row["tc_son_nuoc"]
                * Decimal("100")
            )

        else:

            row["ty_le_cao_cap"] = Decimal("0")


        monthly_report.append(
            row
        )


    # ======================================================
    # QUARTERLY REPORT
    # ======================================================

    quarterly_report = []

    for key in sorted(
        quarterly_data.keys()
    ):

        row = quarterly_data[key]

        if row["tc_son_nuoc"]:

            row["ty_le_cao_cap"] = (
                row["tc_cao_cap"]
                / row["tc_son_nuoc"]
                * Decimal("100")
            )

        else:

            row["ty_le_cao_cap"] = Decimal("0")


        quarterly_report.append(
            row
        )


    # ======================================================
    # YEARLY REPORT
    # ======================================================

    yearly_report = []

    for key in sorted(
        yearly_data.keys()
    ):

        row = yearly_data[key]

        if row["tc_son_nuoc"]:

            row["ty_le_cao_cap"] = (
                row["tc_cao_cap"]
                / row["tc_son_nuoc"]
                * Decimal("100")
            )

        else:

            row["ty_le_cao_cap"] = Decimal("0")


        yearly_report.append(
            row
        )


    # ======================================================
    # YEARLY QUARTER REPORT
    # ======================================================

    yearly_quarter_report = []

    for key in sorted(
        yearly_data.keys()
    ):

        row = yearly_data[key]

        yearly_quarter_report.append(
            row
        )


    # ======================================================
    # CONTEXT
    # ======================================================
    print("monthly_data =", len(monthly_data))
    print("quarterly_data =", len(quarterly_data))
    print("yearly_data =", len(yearly_data))

    print(
        "monthly_report years =",
        sorted(
            set(
                row["year"]
                for row in monthly_report
            )
        )
    )

    print(
        "yearly_report years =",
        sorted(
            set(
                row["year"]
                for row in yearly_report
            )
        )
    )

    print("======================================")

    context = {

        # -----------------------------
        # FILTER
        # -----------------------------

        "brand": brand,

        "supplier": supplier,

        "nam": selected_years_str,
        "selected_years": selected_years,

        # -----------------------------
        # FILTER LIST
        # -----------------------------

        "brand_list": brand_list,

        "supplier_list": supplier_list,

        "nam_list": nam_list,

        # -----------------------------
        # COLUMNS
        # -----------------------------

        "level_columns": level_columns,

        "type_columns": type_columns,

        # -----------------------------
        # REPORT
        # -----------------------------

        "monthly_report": monthly_report,

        "quarterly_report": quarterly_report,

        "yearly_report": yearly_report,

        "yearly_quarter_report":
            yearly_quarter_report,

    }


    return render(
        request,
        "bao_cao_mua_hang.html",
        context
    )


