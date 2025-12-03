import sys
import os
import django
from decimal import Decimal
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')




# Đường dẫn tới project Django
PROJECT_PATH = r"E:\My Drive\Python Web\XML\271khohang"
if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

# Thiết lập settings Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "khohang271.settings")
django.setup()

# --- Phần logic xử lý file XML ---
folder = r"E:\My Drive\DT-CP\HD_VAO\THU"


from invoice_reader_app.model_invoice import Invoice, InvoiceItem, Supplier, Customer, ProductName
from invoice_reader_app.upload_invoice import parse_invoice_xml

def to_decimal(value):
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except:
        return Decimal("0")

def normalize(t):
    import re
    if not t:
        return ""
    return re.sub(r"\s+", "", t).strip().upper()

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None

def run():

    # Folder chứa file XML mới trên Windows
    folder = r"E:\My Drive\DT-CP\HD_VAO\THU"
    # Folder chứa file đã xử lý
    #processed_folder = r"E:\My Drive\Python Web\XML\271khohang\uploads_processed"
    
    #os.makedirs(processed_folder, exist_ok=True)
    
    files = [f for f in os.listdir(folder) if f.endswith(".xml")]
    
    for file_name in files:
        path = os.path.join(folder, file_name)
        try:
            invoice_data, items_data = parse_invoice_xml(open(path, "rb"))
            # Tương tự logic của save_multiple_invoices
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
                defaults={
                    "mau_so": mau_so,
                    "hinh_thuc_tt": invoice_data.get("hinh_thuc_tt") or "",
                    "ten_dv_ban": invoice_data.get("ten_dv_ban") or "",
                    "dia_chi": invoice_data.get("dia_chi") or "",
                    "ten_nguoi_mua": invoice_data.get("ten_nguoi_mua") or "",
                    "ma_so_thue_mua": invoice_data.get("ma_so_thue_mua") or "",
                    "dia_chi_mua": invoice_data.get("dia_chi_mua") or "",
                    "so_tk": invoice_data.get("so_tk") or "",
                    "ten_ngan_hang": invoice_data.get("ten_ngan_hang") or "",
                    "tong_tien": to_decimal(invoice_data.get("tong_tien")),
                    "file_name": file_name
                }
            )

            # Xóa item cũ và insert item mới
            InvoiceItem.objects.filter(invoice=invoice_obj).delete()
            invoice_items = []
            for item in items_data:
                quantity = to_decimal(item.get("so_luong") or 0)
                unit_price = to_decimal(item.get("don_gia") or 0)
                total_price = quantity * unit_price
                raw_tax = item.get("thue_suat", 0)
                if isinstance(raw_tax, float) and raw_tax < 1:
                    raw_tax *= 100
                tax_rate = to_decimal(str(raw_tax).replace("%", "").strip())
                tien_thue = total_price * tax_rate / Decimal("100")
                chiet_khau_item = to_decimal(item.get("chiet_khau") or 0)
                invoice_items.append(
                    InvoiceItem(
                        invoice=invoice_obj,
                        ten_hang=item.get("ten_hang"),
                        dvt=item.get("dvt"),
                        so_luong=quantity,
                        don_gia=unit_price,
                        thanh_tien=total_price,
                        chiet_khau=chiet_khau_item,
                        thue_suat=tax_rate,
                        tien_thue=tien_thue,
                        thanh_toan=(total_price - chiet_khau_item + tien_thue),
                    )
                )
            if invoice_items:
                InvoiceItem.objects.bulk_create(invoice_items)
            
            # Di chuyển file đã xử lý sang folder processed
            #os.rename(path, os.path.join(processed_folder, file_name))
            print(f"File {file_name} đã insert thành công.")

        except Exception as e:
            print(f"❌ Lỗi file {file_name}: {e}")

if __name__ == "__main__":
    run()
