from django.core.management.base import BaseCommand
from django.db import transaction

from invoice_reader_app.models_purchaseorder import PurchaseOrder
from invoice_reader_app.model_invoice import Customer


class Command(BaseCommand):
    help = "Đồng bộ Customer của PX theo MST người mua trong Invoice"

    def handle(self, *args, **options):

        updated = 0
        created_customer = 0
        skipped = 0

        qs = PurchaseOrder.objects.filter(
            po_number__startswith="PX",
            invoice__isnull=False
        ).select_related("invoice", "customer")

        total = qs.count()

        self.stdout.write(
            f"Tìm thấy {total} PX cần kiểm tra"
        )

        with transaction.atomic():

            for po in qs:

                invoice = po.invoice

                mst_customer = (
                    invoice.ma_so_thue_mua or ""
                ).strip()

                if not mst_customer:
                    self.stdout.write(
                        self.style.WARNING(
                            f"{po.po_number}: Không có MST người mua"
                        )
                    )
                    skipped += 1
                    continue


                customer, created = Customer.objects.get_or_create(
                    ma_so_thue=mst_customer,
                    defaults={
                        "ten_khach_hang": (
                            invoice.ten_nguoi_mua
                            or "Khách hàng"
                        ),
                        "dia_chi": (
                            invoice.dia_chi_mua
                            or ""
                        ),
                    }
                )


                if created:
                    created_customer += 1


                # Chỉ cập nhật khi khác nhau
                if po.customer_id != customer.id:
                    old_customer = po.customer_id

                    po.customer = customer
                    po.save(
                        update_fields=[
                            "customer"
                        ]
                    )

                    updated += 1

                    self.stdout.write(
                        f"{po.po_number}: "
                        f"{old_customer} -> {customer.id} "
                        f"(MST {mst_customer})"
                    )


        self.stdout.write(
            self.style.SUCCESS(
                f"Tạo mới Customer: {created_customer}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Cập nhật PX: {updated}"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                f"Bỏ qua: {skipped}"
            )
        )


# python manage.py fix_px_customer 