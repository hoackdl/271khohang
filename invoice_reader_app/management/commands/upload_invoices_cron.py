import os
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.core.management.base import BaseCommand

from invoice_reader_app.model_invoice import Invoice, InvoiceItem, Supplier, Customer, ProductName
from invoice_reader_app.upload_invoice import parse_invoice_xml


# ------------------------------
# Hàm hỗ trợ
# ------------------------------
def to_decimal(value):
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


def normalize(t):
    if not t:
        return ""
    return re.sub(r"\s+", "", t).strip().upper()


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None


FOLDERS = {
    #"VAO": r"E:\My Drive\DT-CP\Năm 2025\BAO_CAO\HD_XUAT",
    "XUAT": r"E:\My Drive\DT-CP\Năm 2025\BAO_CAO\HD_XUAT"
}


MAX_RETRY = 3


# ------------------------------
# Command
# ------------------------------
class Command(BaseCommand):
    help = "Import hóa đơn XML vào database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, help="Số file tối đa muốn xử lý"
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        retries = 0
        files_to_retry = None

        while retries < MAX_RETRY:
            if retries > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"\n--- Bắt đầu thử lại lần {retries} cho {len(files_to_retry)} file lỗi ---"
                    )
                )
            files_to_retry = self.run(files_to_process=files_to_retry, limit=limit)
            if not files_to_retry:
                self.stdout.write(self.style.SUCCESS("✅ Tất cả các file lỗi đã được xử lý thành công."))
                break
            retries += 1

        if files_to_retry:
            self.stdout.write("\n=== Danh sách file vẫn lỗi sau tất cả lượt retry ===")
            for f in files_to_retry:
                self.stdout.write(f"- {f}")
        else:
            self.stdout.write("\n🎉 Hoàn tất: không còn file lỗi.")

    # ------------------------------
    # Chạy import
    # ------------------------------
    def run(self, files_to_process=None, limit=None):
        error_files = []

        for loai_hd, folder in FOLDERS.items():
            if not os.path.exists(folder):
                self.stdout.write(self.style.WARNING(f"Folder {folder} không tồn tại, bỏ qua {loai_hd}"))
                continue

            files = files_to_process if files_to_process is not None else [f for f in os.listdir(folder) if f.endswith(".xml")]

            if limit is not None:
                files = files[:limit]

            for file_name in files:
                path = os.path.join(folder, file_name)
                try:
                    with open(path, "rb") as f:
                        invoice_data, items_data = parse_invoice_xml(f)

                    # Chuẩn hóa thông tin hóa đơn
                    so_hoa_don = normalize(invoice_data.get("so_hoa_don"))
                    ky_hieu = normalize(invoice_data.get("ky_hieu"))
                    mau_so = normalize(invoice_data.get("mau_so"))
                    ma_so_thue = normalize(invoice_data.get("ma_so_thue"))
                    ngay_hd = parse_date(invoice_data.get("ngay_hd"))

                    invoice_obj, _ = Invoice.objects.update_or_create(
                        so_hoa_don=so_hoa_don,
                        ky_hieu=ky_hieu,
                        ma_so_thue=ma_so_thue,
                        ngay_hd=ngay_hd,
                        loai_hd=loai_hd,
                        defaults={
                            "mau_so": mau_so,
                            "hinh_thuc_tt": invoice_data.get("hinh_thuc_tt") or "",
                            "ten_dv_ban": invoice_data.get("ten_dv_ban") or "",
                            "dia_chi": invoice_data.get("dia_chi") or "",
                            "ten_nguoi_mua": invoice_data.get("ten_nguoi_mua") or "Khách lẻ",
                            "ma_so_thue_mua": invoice_data.get("ma_so_thue_mua") or f"TEMP-{so_hoa_don}",
                            "dia_chi_mua": invoice_data.get("dia_chi_mua") or "",
                            "so_tk": invoice_data.get("so_tk") or "",
                            "ten_ngan_hang": invoice_data.get("ten_ngan_hang") or "",
                            "tong_tien": to_decimal(invoice_data.get("tong_tien")),
                            "file_name": file_name
                        }
                    )

                    Supplier.objects.update_or_create(
                        ma_so_thue=invoice_obj.ma_so_thue,
                        defaults={"ten_dv_ban": invoice_obj.ten_dv_ban, "dia_chi": invoice_obj.dia_chi}
                    )

                    Customer.objects.update_or_create(
                        ma_so_thue=invoice_obj.ma_so_thue_mua,
                        defaults={"ten_khach_hang": invoice_obj.ten_nguoi_mua, "dia_chi": invoice_obj.dia_chi_mua}
                    )

                    InvoiceItem.objects.filter(invoice=invoice_obj).delete()

                    invoice_items = []
                    for item in items_data:
                        ten_hang = item.get("ten_hang") or ""
                        product = ProductName.objects.filter(ten_goi_xuat=ten_hang).first()
                        ten_goi_chung = product.ten_goi_chung if product else None

                        invoice_items.append(
                            InvoiceItem(
                                invoice=invoice_obj,
                                ten_hang=ten_hang,
                                dvt=item.get("dvt"),
                                so_luong=to_decimal(item.get("so_luong")),
                                don_gia=to_decimal(item.get("don_gia")),
                                thanh_tien=to_decimal(item.get("thanh_tien_truoc_ck")),
                                chiet_khau=to_decimal(item.get("chiet_khau")),
                                thue_suat=to_decimal(item.get("thue_suat")),
                                tien_thue=to_decimal(item.get("tien_thue")),
                                thanh_toan=to_decimal(item.get("thanh_toan")),
                                ten_goi_chung=ten_goi_chung,
                                supplier=Supplier.objects.get(ma_so_thue=invoice_obj.ma_so_thue)
                            )
                        )

                    if invoice_items:
                        InvoiceItem.objects.bulk_create(invoice_items)

                    self.stdout.write(self.style.SUCCESS(f"[{loai_hd}] File {file_name} đã insert thành công."))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"[{loai_hd}] ❌ Lỗi file {file_name}: {e}"))
                    error_files.append(file_name)

        return error_files
