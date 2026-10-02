# invoice_reader_app/management/commands/backfill_ky_hieu_xuat.py

from django.core.management.base import BaseCommand
from django.db import transaction
from invoice_reader_app.model_invoice import Invoice
from invoice_reader_app.upload_invoice import parse_invoice_xml
import os


class Command(BaseCommand):
    help = "Backfill ky_hieu cho hóa đơn bán (XUAT) từ XML gốc"

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True, help="Thư mục chứa XML hóa đơn bán")

    def handle(self, *args, **options):
        base_path = options["path"]

        updated = 0
        skipped = 0

        for root, _, files in os.walk(base_path):
            for name in files:
                if not name.lower().endswith(".xml"):
                    continue

                xml_path = os.path.join(root, name)

                try:
                    inv_xml, _ = parse_invoice_xml(open(xml_path, "rb"))
                except Exception:
                    skipped += 1
                    continue

                so_hd = inv_xml.get("so_hoa_don")
                ky_hieu = inv_xml.get("ky_hieu")

                if not so_hd or not ky_hieu:
                    skipped += 1
                    continue

                qs = Invoice.objects.filter(
                    loai_hd="XUAT",
                    so_hoa_don=so_hd,
                    ma_so_thue_mua="0314858906",
                ).filter(
                    ky_hieu__isnull=True
                ) | Invoice.objects.filter(
                    loai_hd="XUAT",
                    so_hoa_don=so_hd,
                    ma_so_thue_mua="0314858906",
                    ky_hieu=""
                )

                if qs.count() != 1:
                    skipped += 1
                    continue

                inv = qs.first()
                inv.ky_hieu = ky_hieu
                inv.save(update_fields=["ky_hieu"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"🎉 Backfill xong: {updated} hóa đơn | bỏ qua: {skipped}"
        ))

# python manage.py backfill_ky_hieu_xuat --path "E:\My Drive\DT-CP\Nam 2025\BAO_CAO\HD_XUAT"
