from django.core.management.base import BaseCommand
from decimal import Decimal, ROUND_HALF_UP
from django.core.management.base import BaseCommand
from decimal import Decimal, ROUND_HALF_UP
from invoice_reader_app.models_purcharoder import PurchaseOrder, PurchaseOrderItem

class Command(BaseCommand):
    help = "Fix toàn bộ thuế suất, tiền thuế và tổng PO."

    def handle(self, *args, **kwargs):
        items = PurchaseOrderItem.objects.all()
        self.stdout.write(f"Tìm thấy {items.count()} item để xử lý.\n")

        affected_pos = set()

        for item in items:
            # Chuyển sang Decimal để đảm bảo tính toán chính xác
            total_price = Decimal(item.total_price)
            raw_tax = item.thue_suat_field

            # Nếu là string, convert sang Decimal
            if isinstance(raw_tax, str):
                raw_tax = raw_tax.replace("%", "").strip()
                raw_tax = Decimal(raw_tax) if raw_tax else Decimal("0")

            else:
                raw_tax = Decimal(raw_tax)

            # Nếu thuế suất nhỏ hơn 1 → giả sử là 0.08, 0.1 -> nhân 100
            if raw_tax < 1:
                raw_tax = (raw_tax * 100).quantize(Decimal("0.01"))

            item.thue_suat_field = raw_tax

            # Tính lại tiền thuế
            item.tien_thue_field = (total_price * raw_tax / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            item.save(update_fields=['thue_suat_field', 'tien_thue_field'])
            affected_pos.add(item.purchase_order_id)

            self.stdout.write(
                f"Item {item.id}: thuế suất = {item.thue_suat_field}, tiền thuế = {item.tien_thue_field}"
            )

        self.stdout.write("\nCập nhật tổng tiền và tổng thuế của các PO...\n")

        for po_id in affected_pos:
            po = PurchaseOrder.objects.get(id=po_id)

            po.total_amount = sum(Decimal(i.total_price) for i in po.items.all()).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            po.total_tax = sum(Decimal(i.tien_thue_field) for i in po.items.all()).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            po.save(update_fields=['total_amount', 'total_tax'])

            self.stdout.write(
                f"PO {po.po_number}: total_amount = {po.total_amount}, total_tax = {po.total_tax}"
            )

        self.stdout.write("\n🎉 Hoàn tất fix thuế suất, tiền thuế và tổng PO cho tất cả item.")





# python manage.py fix_tax_rate