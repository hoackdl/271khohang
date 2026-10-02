from django.core.management.base import BaseCommand
from django.db import transaction

from invoice_reader_app.model_invoice import Invoice, InvoiceItem
from invoice_reader_app.models_purchaseorder import PurchaseOrder


class Command(BaseCommand):
    help = "Kiểm tra và xử lý ForeignKey mồ côi của PurchaseOrder và InvoiceItem"

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.WARNING(
                "\n=== KIỂM TRA FOREIGN KEY MỒ CÔI ===\n"
            )
        )

        # =========================================================
        # 1. KIỂM TRA InvoiceItem
        # =========================================================

        bad_invoice_items = InvoiceItem.objects.filter(
            invoice_id__isnull=False
        ).exclude(
            invoice_id__in=Invoice.objects.values_list(
                "id",
                flat=True
            )
        )

        invoice_item_count = bad_invoice_items.count()

        self.stdout.write(
            f"InvoiceItem lỗi: {invoice_item_count}"
        )

        # =========================================================
        # 2. KIỂM TRA PurchaseOrder
        # =========================================================

        bad_purchase_orders = PurchaseOrder.objects.filter(
            invoice_id__isnull=False
        ).exclude(
            invoice_id__in=Invoice.objects.values_list(
                "id",
                flat=True
            )
        )

        purchase_order_count = bad_purchase_orders.count()

        self.stdout.write(
            f"PurchaseOrder lỗi: {purchase_order_count}"
        )

        # =========================================================
        # 3. IN MỘT SỐ BẢN GHI ĐỂ KIỂM TRA
        # =========================================================

        self.stdout.write(
            self.style.WARNING(
                "\n--- InvoiceItem mồ côi ---"
            )
        )

        for item in bad_invoice_items[:20]:

            self.stdout.write(
                f"ID={item.id} | "
                f"invoice_id={item.invoice_id} | "
                f"ten_hang={item.ten_hang} | "
                f"thanh_toan={item.thanh_toan}"
            )

        self.stdout.write(
            self.style.WARNING(
                "\n--- PurchaseOrder mồ côi ---"
            )
        )

        for po in bad_purchase_orders[:20]:

            self.stdout.write(
                f"ID={po.id} | "
                f"invoice_id={po.invoice_id}"
            )

        # =========================================================
        # 4. KHÔNG CÓ DỮ LIỆU LỖI
        # =========================================================

        if invoice_item_count == 0 and purchase_order_count == 0:

            self.stdout.write(
                self.style.SUCCESS(
                    "\nDatabase không còn ForeignKey mồ côi."
                )
            )

            return

        # =========================================================
        # 5. XÁC NHẬN
        # =========================================================

        self.stdout.write("")

        confirm = input(
            "Nhập FIX để bỏ liên kết Invoice bị mất: "
        ).strip()

        if confirm != "FIX":

            self.stdout.write(
                self.style.WARNING(
                    "Đã hủy. Không thay đổi dữ liệu."
                )
            )

            return

        # =========================================================
        # 6. TRANSACTION
        # =========================================================

        with transaction.atomic():

            # -----------------------------------------------------
            # PurchaseOrder
            # -----------------------------------------------------

            po_updated = bad_purchase_orders.update(
                invoice=None
            )

            # -----------------------------------------------------
            # InvoiceItem
            # -----------------------------------------------------

            # Chỉ thực hiện nếu ForeignKey cho phép NULL
            invoice_field = InvoiceItem._meta.get_field(
                "invoice"
            )

            if not invoice_field.null:

                raise RuntimeError(
                    "InvoiceItem.invoice đang null=False. "
                    "Không được tự động đặt invoice=None."
                )

            item_updated = bad_invoice_items.update(
                invoice=None
            )

        # =========================================================
        # 7. KẾT QUẢ
        # =========================================================

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"Đã xử lý {po_updated} PurchaseOrder."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Đã xử lý {item_updated} InvoiceItem."
            )
        )

        # =========================================================
        # 8. KIỂM TRA LẠI
        # =========================================================

        bad_invoice_items_after = InvoiceItem.objects.filter(
            invoice_id__isnull=False
        ).exclude(
            invoice_id__in=Invoice.objects.values_list(
                "id",
                flat=True
            )
        )

        bad_purchase_orders_after = PurchaseOrder.objects.filter(
            invoice_id__isnull=False
        ).exclude(
            invoice_id__in=Invoice.objects.values_list(
                "id",
                flat=True
            )
        )

        self.stdout.write("")

        self.stdout.write(
            f"InvoiceItem lỗi còn lại: "
            f"{bad_invoice_items_after.count()}"
        )

        self.stdout.write(
            f"PurchaseOrder lỗi còn lại: "
            f"{bad_purchase_orders_after.count()}"
        )

        if (
            bad_invoice_items_after.count() == 0
            and
            bad_purchase_orders_after.count() == 0
        ):

            self.stdout.write(
                self.style.SUCCESS(
                    "\n=== FOREIGN KEY ĐÃ SẠCH ==="
                )
            )

            self.stdout.write(
                "Bây giờ có thể chạy:"
            )

            self.stdout.write(
                "python manage.py migrate"
            )

        else:

            self.stdout.write(
                self.style.ERROR(
                    "\nVẫn còn ForeignKey mồ côi. "
                    "Chưa nên migrate."
                )
            )
