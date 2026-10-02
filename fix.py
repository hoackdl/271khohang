import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'khohang271.settings')
django.setup()

from invoice_reader_app.model_invoice import Invoice, Supplier

# 1️⃣ Tạo lại danh sách Supplier nếu chưa có
for inv in Invoice.objects.all():
    supplier, created = Supplier.objects.get_or_create(
        ma_so_thue=inv.ma_so_thue,
        defaults={
            "ten_dv_ban": inv.ten_dv_ban,
            "dia_chi": inv.dia_chi,
            "phan_loai": inv.phan_loai or "hang_hoa"
        }
    )
    inv.supplier = supplier
    inv.save(update_fields=["supplier"])

print("✅ Hoàn tất: tất cả hóa đơn đã được gán Supplier đúng.")
