from django.core.management.base import BaseCommand
from invoice_reader_app.model_invoice import Invoice, InvoiceItem
from django.db.models import Count


class Command(BaseCommand):
    help = 'Xóa các hóa đơn bị trùng dựa trên: số HĐ, ký hiệu, mẫu số, mã số thuế'
    def handle(self, *args, **kwargs):
        duplicates = (
            Invoice.objects
            .values('so_hoa_don', 'ky_hieu', 'mau_so', 'ma_so_thue')
            .annotate(dup_count=Count('id'))
            .filter(dup_count__gt=1)
        )

        total_deleted = 0
        for dup in duplicates:
            same_invoices = Invoice.objects.filter(
                so_hoa_don=dup['so_hoa_don'],
                ky_hieu=dup['ky_hieu'],
                mau_so=dup['mau_so'],
                ma_so_thue=dup['ma_so_thue'],
            ).order_by('id')

            to_delete = list(same_invoices[1:])  # cần chuyển sang list để tránh slicing queryset
            count = 0
            for dup_invoice in to_delete:
                dup_invoice.delete()
                count += 1

            total_deleted += count
            self.stdout.write(
                f"🧹 Đã xoá {count} bản ghi trùng của hóa đơn số {dup['so_hoa_don']} - {dup['ky_hieu']} - {dup['ma_so_thue']}"
            )

        self.stdout.write(self.style.SUCCESS(f"✅ Hoàn tất. Tổng số bản ghi bị xoá: {total_deleted}"))

# python manage.py clean_duplicate_invoices