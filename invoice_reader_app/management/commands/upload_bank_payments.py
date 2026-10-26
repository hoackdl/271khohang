import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db.models import Q

from invoice_reader_app.upload_bank_payments import parse_date_excel, parse_decimal_excel
from invoice_reader_app.models_purchaseorder import PurchaseOrder, FiscalYear, BankPayment



# 📌 CHỌN FOLDER CỐ ĐỊNH (CHỈNH TẠI ĐÂY)
FOLDER_PATH = r"E:\My Drive\DT-CP\Năm 2025\BAO_CAO\BANK"


class Command(BaseCommand):
    help = "Import giao dịch ngân hàng từ tất cả file Excel trong FOLDER cố định"

    def add_arguments(self, parser):
        parser.add_argument(
            "--latest",
            action="store_true",
            help="Chỉ lấy file Excel mới nhất trong folder"
        )
        parser.add_argument(
            "--update-po",
            action="store_true",
            help="Tự động gán PO dựa theo nội dung giao dịch"
        )

    def handle(self, *args, **options):

        update_po = options.get("update_po")
        only_latest = options.get("latest")

        if not os.path.exists(FOLDER_PATH):
            self.stdout.write(self.style.ERROR(f"❌ Folder không tồn tại: {FOLDER_PATH}"))
            return

        # Lấy danh sách file trong folder
        excel_files = [
            os.path.join(FOLDER_PATH, f)
            for f in os.listdir(FOLDER_PATH)
            if f.lower().endswith((".xlsx", ".xls"))
        ]

        if not excel_files:
            self.stdout.write(self.style.WARNING("⚠ Không có file Excel trong folder!"))
            return

        # Nếu chỉ lấy file mới nhất
        if only_latest:
            excel_files = [max(excel_files, key=os.path.getmtime)]
            self.stdout.write(self.style.WARNING(f"🔍 Chỉ import file mới nhất: {excel_files[0]}"))

        total_added = 0
        total_po_linked = 0

        # Xử lý từng file
        for excel_file in excel_files:
            self.stdout.write(self.style.WARNING(f"\n📄 Đang xử lý: {os.path.basename(excel_file)}"))

            # Đọc Excel
            try:
                df = pd.read_excel(excel_file, engine="openpyxl")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Lỗi đọc file {excel_file}: {e}"))
                continue

            # Chuẩn hoá tên cột
            df.rename(columns={
                'Ngày hiệu lực2/\nEffective date': 'payment_date',
                'Số tiền ghi có/\nCredit': 'credit',
                'Số tiền ghi nợ/\nDebit': 'debit',
                'Số dư/\nBalance': 'balance',
                'Nội dung chi tiết/\nTransactions in detail': 'content',
                'Ngày1/\nTNX Date/ Số CT/ Doc No': 'doc_no',
                'STT\nNo.': 'stt'
            }, inplace=True)

            added_count = 0
            updated_po_count = 0

            # Import từng dòng
            for _, row in df.iterrows():
                content = str(row.get("content", ""))
                credit = parse_decimal_excel(row.get("credit"))
                debit = parse_decimal_excel(row.get("debit"))
                balance = parse_decimal_excel(row.get("balance"))
                payment_date = parse_date_excel(row.get("payment_date"))
                doc_no = str(row.get("doc_no", ""))

                # Check trùng
                exists = BankPayment.objects.filter(
                    doc_no=doc_no,
                    payment_date=payment_date,
                    credit=credit,
                    debit=debit
                ).exists()
                if exists:
                    continue

                payment = BankPayment.objects.create(
                    credit=credit,
                    debit=debit,
                    balance=balance,
                    payment_date=payment_date,
                    content=content,
                    doc_no=doc_no,
                    stt=row.get("stt")
                )
                added_count += 1

                # Auto link PO
                if update_po:
                    po_match = PurchaseOrder.objects.filter(
                        Q(po_number__icontains=doc_no) |
                        Q(po_number__icontains=content)
                    ).first()

                    if po_match:
                        payment.purchase_orders.add(po_match)
                        updated_po_count += 1

            total_added += added_count
            total_po_linked += updated_po_count

            self.stdout.write(self.style.SUCCESS(
                f"✔ File {os.path.basename(excel_file)}: thêm {added_count} giao dịch."
            ))

        # Tổng kết
        self.stdout.write(self.style.SUCCESS(f"\n🎉 HOÀN TẤT IMPORT BANK"))
        self.stdout.write(self.style.SUCCESS(f"➕ Tổng giao dịch thêm mới: {total_added}"))
        if update_po:
            self.stdout.write(self.style.SUCCESS(f"🔗 Tổng giao dịch đã gán PO: {total_po_linked}"))


# python manage.py upload_bank_payments  