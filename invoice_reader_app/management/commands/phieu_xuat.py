from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from invoice_reader_app.model_invoice import Invoice
from invoice_reader_app.export_order import create_or_update_purchase_order_from_invoice

SELLER_MST = "0314858906"  # MST người bán để xác định hóa đơn xuất

class Command(BaseCommand):
    help = "Tạo PO từ các hóa đơn xuất của MST người bán 0314858906"

    def add_arguments(self, parser):
        parser.add_argument('--invoice_ids', nargs='+', type=int, help="ID hóa đơn muốn tạo PO")
        parser.add_argument('--limit', type=int, help="Số lượng hóa đơn muốn tạo PO")
        parser.add_argument('--search', type=str, help="Tìm kiếm theo số hóa đơn hoặc tên người mua")
        parser.add_argument('--start_date', type=str, help="Ngày bắt đầu lọc hóa đơn (YYYY-MM-DD)")
        parser.add_argument('--end_date', type=str, help="Ngày kết thúc lọc hóa đơn (YYYY-MM-DD)")

    def handle(self, *args, **options):
        invoice_ids = options.get('invoice_ids')
        limit = options.get('limit')
        search = options.get('search')
        start_date = options.get('start_date')
        end_date = options.get('end_date')

        # --- Lấy tất cả hóa đơn xuất theo MST bán ---
        invoices = Invoice.objects.filter(
            ma_so_thue=SELLER_MST
        ).exclude(
            ma_so_thue_mua=SELLER_MST
        ).order_by('ngay_hd')

        # --- Lọc theo ID nếu có ---
        if invoice_ids:
            invoices = invoices.filter(id__in=invoice_ids)

        # --- Lọc theo search ---
        if search:
            invoices = invoices.filter(
                Q(so_hoa_don__icontains=search) |
                Q(ten_nguoi_mua__icontains=search) |
                Q(ma_so_thue_mua__icontains=search)
            )

        # --- Lọc theo ngày ---
        if start_date:
            invoices = invoices.filter(ngay_hd__date__gte=start_date)
        if end_date:
            invoices = invoices.filter(ngay_hd__date__lte=end_date)

        # --- Giới hạn số hóa đơn ---
        if limit:
            invoices = invoices[:limit]

        if not invoices.exists():
            self.stdout.write(self.style.WARNING("Không có hóa đơn xuất nào để tạo PO."))
            return

        created_pos = []
        failed_invoices = []

        for invoice in invoices:
            try:
                po = create_or_update_purchase_order_from_invoice(invoice)
                created_pos.append(po)
                self.stdout.write(self.style.SUCCESS(
                    f"Tạo/ cập nhật PO {po.po_number} từ hóa đơn {invoice.so_hoa_don} thành công!"
                ))
            except Exception as e:
                failed_invoices.append(invoice)
                self.stdout.write(self.style.ERROR(
                    f"❌ Không tạo được PO từ hóa đơn {invoice.so_hoa_don}: {str(e)}"
                ))

        self.stdout.write("\n=== TÓM TẮT ===")
        self.stdout.write(f"Số hóa đơn tạo được PO: {len(created_pos)}")
        if created_pos:
            self.stdout.write("Danh sách PO mới tạo:")
            for po in created_pos:
                self.stdout.write(f"- {po.po_number} | Ngày: {po.created_at} | Nhà cung cấp: {po.supplier}")

        self.stdout.write(f"Số hóa đơn không tạo được PO: {len(failed_invoices)}")
        if failed_invoices:
            self.stdout.write("Danh sách hóa đơn thất bại:")
            for inv in failed_invoices:
                self.stdout.write(f"- {inv.so_hoa_don} | Ngày: {inv.ngay_hd} | Người mua: {inv.ten_nguoi_mua}")
