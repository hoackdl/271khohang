from django.core.management.base import BaseCommand
from invoice_reader_app.models_purchaseorder import PurchaseOrder, FiscalYear
from django.db import transaction

class Command(BaseCommand):
    help = "Tự tạo FiscalYear cho mọi PurchaseOrder và gán, tránh lỗi FK"

    def handle(self, *args, **options):
        self.stdout.write("Bắt đầu kiểm tra và tạo FiscalYear...")

        # Lấy tất cả năm từ PO hiện tại
        po_years = set()
        for po in PurchaseOrder.objects.all():
            if po.created_at:
                po_years.add(po.created_at.year)

        self.stdout.write(f"Tìm thấy các năm từ PO: {sorted(po_years)}")

        # Dùng transaction để an toàn
        with transaction.atomic():
            for year in po_years:
                fiscal_year, created = FiscalYear.objects.get_or_create(year=year)
                if created:
                    self.stdout.write(f"Tạo FiscalYear mới cho năm {year}")
                else:
                    self.stdout.write(f"FiscalYear {year} đã tồn tại")

            # Gán fiscal_year cho PO nếu chưa có
            updated_count = 0
            for po in PurchaseOrder.objects.all():
                if not getattr(po, 'fiscal_year', None) and po.created_at:
                    fy = FiscalYear.objects.get(year=po.created_at.year)
                    po.fiscal_year = fy
                    po.save()
                    updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Hoàn tất. Đã gán FiscalYear cho {updated_count} PO."
        ))


        
# python manage.py fix_fiscal_years