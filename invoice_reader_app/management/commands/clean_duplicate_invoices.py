from django.core.management.base import BaseCommand
from invoice_reader_app.model_invoice import Invoice
from django.db.models import Count

class Command(BaseCommand):
    help = 'Xóa các hóa đơn trùng hoặc chỉ liệt kê (--dry-run)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Chỉ hiển thị hóa đơn trùng mà không xóa'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

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

            if dry_run:
                self.stdout.write(f"⚠️  Tìm thấy {len(same_invoices)} bản trùng của hóa đơn {dup['so_hoa_don']} - {dup['ky_hieu']} - {dup['ma_so_thue']}")
                continue

            to_delete = list(same_invoices[1:])
            count = 0
            for dup_invoice in to_delete:
                dup_invoice.delete()
                count += 1

            total_deleted += count
            self.stdout.write(f"🧹 Đã xoá {count} bản trùng của hóa đơn {dup['so_hoa_don']} - {dup['ky_hieu']} - {dup['ma_so_thue']}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"✅ Dry-run hoàn tất, không xóa bản ghi nào."))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Hoàn tất. Tổng số bản ghi bị xoá: {total_deleted}"))



#python manage.py clean_duplicate_invoices --dry-run

# python manage.py clean_duplicate_invoices