from django.core.management.base import BaseCommand
from invoice_reader_app.models_purchaseorder import PurchaseOrder


MY_MST = "0314858906"


def clean_text(value):
    return ''.join(
        c for c in str(value or '')
        if c.isalnum()
    )


def generate_px_number(invoice):
    date_str = invoice.ngay_hd.strftime("%Y%m%d")

    ky_hieu = clean_text(invoice.ky_hieu)
    so_hd = clean_text(invoice.so_hoa_don)

    return f"PX-{date_str}-{ky_hieu}-{so_hd}"


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        px = 0

        for po in PurchaseOrder.objects.select_related("invoice"):

            invoice = po.invoice

            if not invoice:
                continue

            # Chỉ xử lý hóa đơn xuất
            if invoice.ma_so_thue == MY_MST:

                po.phan_loai_phieu = "PX"
                po.po_number = generate_px_number(invoice)

                po.save(
                    update_fields=[
                        "phan_loai_phieu",
                        "po_number"
                    ]
                )

                px += 1


        self.stdout.write(
            self.style.SUCCESS(
                f"Đã cập nhật PX={px}"
            )
        )

        
# python manage.py update_po_number