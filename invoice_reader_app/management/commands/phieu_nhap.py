from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from invoice_reader_app.model_invoice import Invoice, Supplier
from invoice_reader_app.models_purcharoder import PurchaseOrder
from invoice_reader_app.purchase_oder import sync_po_items_from_invoice, generate_pn

BUYER_MST = "0314858906"  # MST người mua để xác định hóa đơn nhập

class Command(BaseCommand):
    help = "Tạo PN từ các hóa đơn mua của MST người mua 0314858906"

    def add_arguments(self, parser):
        parser.add_argument('--invoice_ids', nargs='+', type=int, help="ID hóa đơn muốn tạo PN")
        parser.add_argument('--limit', type=int, help="Số lượng hóa đơn muốn tạo PN")
        parser.add_argument('--search', type=str, help="Tìm kiếm theo số hóa đơn hoặc tên nhà cung cấp")
        parser.add_argument('--start_date', type=str, help="Ngày bắt đầu lọc hóa đơn (YYYY-MM-DD)")
        parser.add_argument('--end_date', type=str, help="Ngày kết thúc lọc hóa đơn (YYYY-MM-DD)")

    def handle(self, *args, **options):
        invoice_ids = options.get('invoice_ids')
        limit = options.get('limit')
        search = options.get('search')
        start_date = options.get('start_date')
        end_date = options.get('end_date')

        # --- Lấy tất cả hóa đơn mua theo MST người mua ---
        invoices = Invoice.objects.filter(
            ma_so_thue_mua=BUYER_MST
        ).exclude(
            ma_so_thue=BUYER_MST
        ).order_by('ngay_hd')

        # --- Lọc theo ID nếu có ---
        if invoice_ids:
            invoices = invoices.filter(id__in=invoice_ids)

        # --- Lọc theo search ---
        if search:
            invoices = invoices.filter(
                Q(so_hoa_don__icontains=search) |
                Q(ten_dv_ban__icontains=search) |
                Q(ma_so_thue__icontains=search)
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
            self.stdout.write(self.style.WARNING("Không có hóa đơn mua nào để tạo PN."))
            return

        created_pos = []
        updated_pos = []

        for invoice in invoices:
            # --- Lấy hoặc tạo Supplier ---
            supplier_instance, _ = Supplier.objects.get_or_create(
                ten_dv_ban=invoice.ten_dv_ban,
                defaults={
                    "ma_so_thue": invoice.ma_so_thue or "",
                    "dia_chi": invoice.dia_chi or ""
                }
            )

            # --- Kiểm tra PO/PN đã tồn tại chưa ---
            po = PurchaseOrder.objects.filter(invoice=invoice).first()

            if not po:
                # --- Tạo PN mới ---
                po_number = generate_pn(invoice)
                po = PurchaseOrder.objects.create(
                    invoice=invoice,
                    po_number=po_number,
                    supplier=supplier_instance,
                    total_amount=invoice.tong_tien or 0,
                    total_tax=0,
                    phan_loai_phieu='PN'
                )
                created_pos.append(po)
                action = "Tạo mới"
            else:
                action = "Đồng bộ"
                updated_pos.append(po)

            # --- Đồng bộ items ---
            sync_po_items_from_invoice(po, invoice)

            self.stdout.write(self.style.SUCCESS(
                f"{action} PN {po.po_number} từ hóa đơn {invoice.so_hoa_don}"
            ))

        self.stdout.write("\n=== TÓM TẮT ===")
        self.stdout.write(f"Tổng số PN vừa tạo: {len(created_pos)}")
        self.stdout.write(f"Tổng số PN đã cập nhật: {len(updated_pos)}")

        if created_pos:
            self.stdout.write("Danh sách PN mới tạo:")
            for po in created_pos:
                self.stdout.write(f"- {po.po_number} | Ngày: {po.created_at} | Nhà cung cấp: {po.supplier.ten_dv_ban}")


# python manage.py phieu_nhap
# python manage.py phieu_nhap --limit 5