from django.core.management.base import BaseCommand
from django.db import transaction

from invoice_reader_app.models_purchaseorder import PurchaseOrder


class Command(BaseCommand):
    help = (
        "Sửa các PurchaseOrder có số PN: "
        "đưa phan_loai_phieu về PN và bổ sung fiscal_year."
    )

    def handle(self, *args, **options):

        qs = (
            PurchaseOrder.objects
            .filter(
                po_number__startswith="PN"
            )
            .select_related("invoice")
        )

        total = qs.count()

        self.stdout.write(
            self.style.WARNING(
                f"Tìm thấy {total} phiếu PN."
            )
        )

        count_type = 0
        count_year = 0
        count_updated = 0

        with transaction.atomic():

            for po in qs:

                changed_fields = []

                # ==========================================
                # 1. SỬA LOẠI PHIẾU
                # ==========================================

                if po.phan_loai_phieu != "PN":

                    po.phan_loai_phieu = "PN"

                    changed_fields.append(
                        "phan_loai_phieu"
                    )

                    count_type += 1

                # ==========================================
                # 2. BỔ SUNG NĂM TÀI CHÍNH
                # ==========================================

                if (
                    not po.fiscal_year
                    and po.invoice
                ):

                    fiscal_year = (
                        po.invoice.fiscal_year
                        or (
                            po.invoice.ngay_hd.year
                            if po.invoice.ngay_hd
                            else None
                        )
                    )

                    if fiscal_year:

                        po.fiscal_year = fiscal_year

                        changed_fields.append(
                            "fiscal_year"
                        )

                        count_year += 1

                # ==========================================
                # 3. SAVE
                # ==========================================

                if changed_fields:

                    po.save(
                        update_fields=changed_fields
                    )

                    count_updated += 1

                    self.stdout.write(
                        f"  ✓ {po.po_number} "
                        f"(ID={po.id}) → "
                        f"{po.phan_loai_phieu} / "
                        f"{po.fiscal_year}"
                    )

        # ==============================================
        # KẾT QUẢ
        # ==============================================

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "========== HOÀN TẤT =========="
            )
        )

        self.stdout.write(
            f"Tổng PN tìm thấy: {total}"
        )

        self.stdout.write(
            f"Đã sửa loại phiếu: {count_type}"
        )

        self.stdout.write(
            f"Đã bổ sung năm: {count_year}"
        )

        self.stdout.write(
            f"Tổng bản ghi cập nhật: {count_updated}"
        )



# python manage.py fix_purchase_order_pn