# invoice_reader_app/utils/get_item_sku.py

from invoice_reader_app.model_invoice import ProductName
import unicodedata


def normalize_text(text):
    """
    Chuẩn hóa chuỗi:
    - None -> ""
    - bỏ khoảng trắng đầu/cuối
    - lowercase
    - bỏ dấu tiếng Việt
    """
    if not text:
        return ""

    text = str(text).strip().lower()

    text = unicodedata.normalize("NFD", text)

    text = "".join(
        c for c in text
        if unicodedata.category(c) != "Mn"
    )

    return text


def get_item_sku(item):

    # ==================================================
    # 1. ƯU TIÊN SKU ĐÃ LƯU TRỰC TIẾP TRÊN InvoiceItem
    # ==================================================

    if item.sku:
        sku = str(item.sku).strip()

        if sku:


            return sku

    # ==================================================
    # 2. TÌM THEO TÊN HÀNG - KHÔNG PHÂN BIỆT HOA THƯỜNG
    #    VÀ KHÔNG PHÂN BIỆT DẤU TIẾNG VIỆT
    # ==================================================

    item_name = normalize_text(item.ten_hang)

    if item_name:

        products = (
            ProductName.objects
            .exclude(sku__isnull=True)
            .exclude(sku="")
        )

        for product in products:

            product_name = normalize_text(product.ten_hang)

            if product_name == item_name:

                sku = str(product.sku).strip()

    
                return sku

    # ==================================================
    # 3. TÌM THEO TÊN GỌI CHUNG
    # ==================================================

    common_name = normalize_text(
        getattr(item, "ten_goi_chung", "")
    )

    if common_name:

        products = (
            ProductName.objects
            .exclude(sku__isnull=True)
            .exclude(sku="")
        )

        for product in products:

            product_common_name = normalize_text(
                getattr(product, "ten_goi_chung", "")
            )

            if product_common_name == common_name:

                sku = str(product.sku).strip()



                return sku

    # ==================================================
    # 4. KHÔNG TÌM THẤY
    # ==================================================



    return ""


