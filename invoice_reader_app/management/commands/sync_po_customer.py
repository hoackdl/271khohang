from django.core.management.base import BaseCommand
from invoice_reader_app.models_purchaseorder import PurchaseOrder
from invoice_reader_app.model_invoice import Customer

from django.core.management.base import BaseCommand
from django.db import transaction




def clean_mst(value):
    if not value:
        return None
    return str(value).strip().replace(" ", "").replace("-", "")


class Command(BaseCommand):
    def handle(self, *args, **kwargs):

        updated = 0
        skipped = 0

        qs = PurchaseOrder.objects.select_related("invoice", "customer")

        for po in qs:

            if po.customer:
                skipped += 1
                continue

            customer = None

            # =========================
            # 1. lấy từ invoice FK nếu có
            # =========================
            if po.invoice and hasattr(po.invoice, "customer"):
                customer = po.invoice.customer

            # =========================
            # 2. lấy từ MST mua
            # =========================
            if not customer and po.invoice and po.invoice.ma_so_thue_mua:
                mst = clean_mst(po.invoice.ma_so_thue_mua)
                customer = Customer.objects.filter(
                    ma_so_thue__iexact=mst
                ).first()

            # =========================
            # 3. fallback theo tên người mua
            # =========================
            if not customer and po.invoice and po.invoice.ten_nguoi_mua:
                customer = Customer.objects.filter(
                    ten_khach_hang__icontains=po.invoice.ten_nguoi_mua
                ).first()

            # =========================
            # update
            # =========================
            if customer:
                po.customer = customer
                po.save(update_fields=["customer"])
                updated += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done! Updated={updated}, Skipped={skipped}"
        ))