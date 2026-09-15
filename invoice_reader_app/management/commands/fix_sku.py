from django.core.management.base import BaseCommand
import unicodedata

from invoice_reader_app.model_invoice import InvoiceItem, ProductName


def normalize(text):
    if not text:
        return ""
    text = text.lower().strip()
    text = unicodedata.normalize('NFD', text)
    return ''.join(c for c in text if unicodedata.category(c) != 'Mn')


class Command(BaseCommand):
    help = "Fix SKU cho InvoiceItem bằng cách mapping từ ProductName"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Bắt đầu mapping SKU...")

        products = list(ProductName.objects.all())

        count = 0
        not_found = 0

        for item in InvoiceItem.objects.all():
            key = normalize(item.ten_hang)

            found = None

            # ✅ 1. exact match
            for p in products:
                if normalize(p.ten_hang) == key:
                    found = p
                    break

            # ✅ 2. contains match
            if not found:
                for p in products:
                    p_name = normalize(p.ten_hang)
                    if len(p_name) > 5 and (p_name in key or key in p_name):
                        found = p
                        break

            if found:
                item.sku = found.sku
                item.save(update_fields=["sku"])
                count += 1
            else:
                self.stdout.write(self.style.WARNING(f"❌ Không map: {item.ten_hang}"))
                not_found += 1

        self.stdout.write(self.style.SUCCESS("✅ DONE"))
        self.stdout.write(f"✔ Mapped: {count}")
        self.stdout.write(f"❌ Not found: {not_found}")