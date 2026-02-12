from django.core.management.base import BaseCommand
from invoice_reader_app.models_purcharoder import PurchaseOrder

class Command(BaseCommand):
    help = "Sync fiscal_year of PurchaseOrder from invoice.ngay_hd"

    def handle(self, *args, **options):
        count = 0
        qs = PurchaseOrder.objects.select_related("invoice").filter(
            invoice__ngay_hd__isnull=False
        )

        for po in qs:
            year = po.invoice.ngay_hd.year
            if po.fiscal_year != year:
                po.fiscal_year = year
                po.save(update_fields=["fiscal_year"])
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Updated: {count}"))
