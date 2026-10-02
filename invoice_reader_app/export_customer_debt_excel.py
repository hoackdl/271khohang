from decimal import Decimal

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from invoice_reader_app.model_invoice import Supplier, InvoiceItem, Invoice
from invoice_reader_app.models_purchaseorder import BankPayment, PurchaseOrder, CashReceipt, BankPaymentAllocation
from invoice_reader_app.model_invoice import Customer, InvoiceItem
from django.db.models import F, Sum, FloatField, ExpressionWrapper, Min, Max
from invoice_reader_app.model_invoice import Supplier, InvoiceItem, Invoice
from invoice_reader_app.models_purchaseorder import BankPayment, PurchaseOrder, CashReceipt, BankPaymentAllocation

from decimal import Decimal
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from openpyxl import Workbook
from openpyxl.styles import (
    Font,
    PatternFill,
    Alignment,
    Border,
    Side,
)
from openpyxl.utils import get_column_letter


from datetime import datetime
from decimal import Decimal

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from openpyxl import Workbook
from openpyxl.styles import (
    Font,
    PatternFill,
    Border,
    Side,
    Alignment,
)
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins

# ==========================================================
# IMPORT MODEL
# ==========================================================




# ==========================================================
# HÀM HỖ TRỢ
# ==========================================================

def decimal(value):
    if value is None:
        return Decimal("0")

    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def format_date_vn(value):
    if not value:
        return ""

    return value.strftime("%d/%m/%Y")


# ==========================================================
# EXPORT CÔNG NỢ KHÁCH HÀNG
# ==========================================================

def export_customer_debt_excel(request, customer_id):

    # ------------------------------------------------------
    # 1. KHÁCH HÀNG
    # ------------------------------------------------------

    customer = get_object_or_404(
        Customer,
        pk=customer_id
    )

    # ------------------------------------------------------
    # 2. KHOẢNG NGÀY
    # ------------------------------------------------------

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    start_date = (
        parse_date(start_date_str)
        if start_date_str and start_date_str != "None"
        else None
    )

    end_date = (
        parse_date(end_date_str)
        if end_date_str and end_date_str != "None"
        else None
    )

    # ------------------------------------------------------
    # 3. LẤY HÓA ĐƠN
    # ------------------------------------------------------

    invoices_qs = (
        Invoice.objects
        .filter(
            ma_so_thue_mua=customer.ma_so_thue
        )
        .order_by(
            "-ngay_hd",
            "-so_hoa_don"
        )
    )

    if start_date:
        invoices_qs = invoices_qs.filter(
            ngay_hd__gte=start_date
        )

    if end_date:
        invoices_qs = invoices_qs.filter(
            ngay_hd__lte=end_date
        )

    # ------------------------------------------------------
    # 4. LOẠI HÓA ĐƠN TRÙNG SỐ
    # ------------------------------------------------------

    seen = set()
    invoices = []

    for inv in invoices_qs:

        if inv.so_hoa_don in seen:
            continue

        seen.add(inv.so_hoa_don)
        invoices.append(inv)

    # ------------------------------------------------------
    # 5. PO
    # ------------------------------------------------------

    purchase_orders = (
        PurchaseOrder.objects
        .filter(
            invoice__in=invoices
        )
        .select_related(
            "invoice",
            "customer"
        )
    )

    # ------------------------------------------------------
    # 6. PHÂN BỔ TIỀN NGÂN HÀNG
    # ------------------------------------------------------

    allocations = (
        BankPaymentAllocation.objects
        .filter(
            purchase_order__in=purchase_orders
        )
        .select_related(
            "payment",
            "payment__parent_payment",
            "purchase_order",
            "purchase_order__invoice"
        )
    )

    invoice_payment_map = {}

    for alloc in allocations:

        if not alloc.purchase_order:
            continue

        invoice = alloc.purchase_order.invoice

        if not invoice:
            continue

        invoice_id = invoice.id

        payment = alloc.payment

        parent_payment = (
            payment.parent_payment
            if payment
            else None
        )

        invoice_payment_map.setdefault(
            invoice_id,
            []
        ).append({

            # Phiếu tổng hợp
            "doc_no": (
                payment.doc_no
                if payment
                else ""
            ),

            # Phiếu ngân hàng gốc
            "bank_doc_no": (
                parent_payment.doc_no
                if parent_payment
                else ""
            ),

            "bank_content": (
                parent_payment.content
                if parent_payment
                else ""
            ),

            # Nội dung phiếu tổng hợp
            "content": (
                payment.content
                if payment
                else ""
            ),

            "payment_date": (
                payment.payment_date
                if payment
                else None
            ),

            "credit": decimal(
                alloc.allocated_amount
            ),
        })

    # ------------------------------------------------------
    # 7. PHIẾU THU TIỀN MẶT
    # ------------------------------------------------------

    cash_receipts = (
        CashReceipt.objects
        .filter(
            invoice__in=invoices
        )
        .order_by(
            "created_at"
        )
    )

    cash_map = {}

    for receipt in cash_receipts:

        amount = decimal(
            receipt.amount
        )

        cash_map[receipt.invoice_id] = (
            cash_map.get(
                receipt.invoice_id,
                Decimal("0")
            )
            + amount
        )

    # ------------------------------------------------------
    # 8. LẬP DỮ LIỆU XUẤT
    # ------------------------------------------------------

    invoice_rows = []

    total_invoice = Decimal("0")
    total_bank_paid = Decimal("0")
    total_cash_paid = Decimal("0")
    total_paid = Decimal("0")

    for inv in invoices:

        invoice_amount = decimal(
            inv.tong_tien
        )

        # ------------------------------
        # Ngân hàng
        # ------------------------------

        bank_items = invoice_payment_map.get(
            inv.id,
            []
        )

        bank_paid = sum(
            (
                decimal(x["credit"])
                for x in bank_items
            ),
            Decimal("0")
        )

        # ------------------------------
        # Phiếu thu TM
        # ------------------------------

        cash_paid = cash_map.get(
            inv.id,
            Decimal("0")
        )

        # ------------------------------
        # Tổng đã thu
        # ------------------------------

        paid = (
            bank_paid
            + cash_paid
        )

        remaining = (
            invoice_amount
            - paid
        )

        # Không cho số âm do sai số làm tròn
        if remaining < 0:
            remaining = Decimal("0")

        # ------------------------------
        # Phiếu ngân hàng
        # ------------------------------

        bank_doc_numbers = []

        for item in bank_items:

            bank_no = (
                item["bank_doc_no"]
                or item["doc_no"]
            )

            if bank_no and bank_no not in bank_doc_numbers:
                bank_doc_numbers.append(
                    bank_no
                )

        bank_docs = ", ".join(
            bank_doc_numbers
        )

        # ------------------------------
        # Nội dung thanh toán
        # ------------------------------

        contents = []

        for item in bank_items:

            content = (
                item["content"]
                or item["bank_content"]
                or ""
            )

            if content and content not in contents:
                contents.append(content)

        content_text = ", ".join(contents)

        invoice_rows.append({

            "invoice": inv,

            "bank_docs": bank_docs,

            "cash_paid": cash_paid,

            "bank_paid": bank_paid,

            "paid": paid,

            "remaining": remaining,

            "content": content_text,
        })

        total_invoice += invoice_amount
        total_bank_paid += bank_paid
        total_cash_paid += cash_paid
        total_paid += paid

    # ======================================================
    # 9. SỐ DƯ ĐẦU KỲ
    # ======================================================

    opening_balance = (
        decimal(customer.phai_thu_dau_ky)
        -
        decimal(customer.phai_tra_dau_ky)
    )

    # ======================================================
    # 10. THU NỢ ĐẦU KỲ
    # ======================================================

    opening_payments = (
        BankPayment.objects
        .filter(
            is_summary=True,
            customer=customer,
            content__startswith="Thu nợ đầu kỳ KH:",
        )
        .order_by(
            "payment_date"
        )
    )

    opening_paid = sum(
        (
            decimal(p.credit)
            for p in opening_payments
        ),
        Decimal("0")
    )

    # ======================================================
    # 11. THU TRỰC TIẾP KHÁCH HÀNG
    # ======================================================

    customer_payments = (
        BankPayment.objects
        .filter(
            is_summary=True,
            customer=customer
        )
        .exclude(
            content__startswith="Thu nợ đầu kỳ KH:"
        )
        .exclude(
            purchase_orders__isnull=False
        )
        .distinct()
        .order_by(
            "payment_date"
        )
    )

    customer_payment_paid = sum(
        (
            decimal(p.credit)
            for p in customer_payments
        ),
        Decimal("0")
    )

    # ======================================================
    # 12. SỐ DƯ CUỐI KỲ
    # ======================================================

    closing_balance = (
        opening_balance
        + total_invoice
        - total_paid
        - opening_paid
        - customer_payment_paid
    )

    # ======================================================
    # 13. TẠO EXCEL
    # ======================================================

    wb = Workbook()

    ws = wb.active
    ws.title = "Công nợ khách hàng"

    # ------------------------------------------------------
    # Màu
    # ------------------------------------------------------

    BLUE = "4472C4"
    LIGHT_BLUE = "D9EAF7"
    YELLOW = "FFFF00"
    LIGHT_YELLOW = "FFF2CC"
    GRAY = "D9E1F2"
    RED = "C00000"
    GREEN = "008000"
    WHITE = "FFFFFF"
    BLACK = "000000"

    thin = Side(
        style="thin",
        color="A6A6A6"
    )

    border = Border(
        left=thin,
        right=thin,
        top=thin,
        bottom=thin
    )

    # ------------------------------------------------------
    # Font
    # ------------------------------------------------------

    company_font = Font(
        name="Arial",
        size=12,
        bold=True
    )

    normal_font = Font(
        name="Arial",
        size=10
    )

    bold_font = Font(
        name="Arial",
        size=10,
        bold=True
    )

    title_font = Font(
        name="Arial",
        size=15,
        bold=True
    )

    header_font = Font(
        name="Arial",
        size=10,
        bold=True,
        color=WHITE
    )

    # ======================================================
    # 14. THÔNG TIN CÔNG TY
    # ======================================================

    ws.merge_cells("A1:I1")
    ws["A1"] = (
        "CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ "
        "TÂM ANH LOGISTICS"
    )
    ws["A1"].font = company_font

    ws.merge_cells("A2:I2")
    ws["A2"] = "MST: 0314858906"
    ws["A2"].font = normal_font

    ws.merge_cells("A3:I3")
    ws["A3"] = (
        "Địa chỉ: 139 Thành Thái, Phường Diên Hồng, "
        "Tp. Hồ Chí Minh"
    )
    ws["A3"].font = normal_font

    # ------------------------------------------------------
    # Ngày xuất
    # ------------------------------------------------------

    today = datetime.now()

    ws.merge_cells("F5:I5")

    ws["F5"] = (
        f"Tp. Hồ Chí Minh, ngày "
        f"{today.day:02d} tháng "
        f"{today.month:02d} năm "
        f"{today.year}"
    )

    ws["F5"].alignment = Alignment(
        horizontal="right"
    )

    ws["F5"].font = normal_font

    # ======================================================
    # 15. TIÊU ĐỀ
    # ======================================================

    ws.merge_cells("A7:I7")

    ws["A7"] = (
        "CHI TIẾT CÔNG NỢ KHÁCH HÀNG"
    )

    ws["A7"].font = title_font

    ws["A7"].alignment = Alignment(
        horizontal="center",
        vertical="center"
    )

    # ======================================================
    # 16. THÔNG TIN KHÁCH HÀNG
    # ======================================================

    ws["C8"] = "Khách hàng:"
    ws["C8"].font = bold_font

    ws.merge_cells("D8:I8")
    ws["D8"] = customer.ten_khach_hang
    ws["D8"].font = normal_font

    ws["C9"] = "MST:"
    ws["C9"].font = bold_font

    ws.merge_cells("D9:I9")
    ws["D9"] = customer.ma_so_thue
    ws["D9"].font = normal_font

    ws["C10"] = "Từ ngày"
    ws["C10"].font = bold_font

    ws["D10"] = (
        format_date_vn(start_date)
        if start_date
        else ""
    )

    ws["E10"] = "Đến ngày"
    ws["E10"].font = bold_font

    ws["F10"] = (
        format_date_vn(end_date)
        if end_date
        else ""
    )

    # ======================================================
    # 17. HEADER BẢNG
    # ======================================================

    header_row = 12

    headers = [
        "TT",
        "Số hóa đơn",
        "Ngày hóa đơn",
        "Tổng hóa đơn",
        "Phiếu ngân hàng",
        "Phiếu thu TM",
        "Đã thu",
        "Còn nợ",
        "Nội dung thanh toán",
    ]

    for col, value in enumerate(
        headers,
        start=1
    ):

        cell = ws.cell(
            row=header_row,
            column=col,
            value=value
        )

        cell.font = header_font
        cell.fill = PatternFill(
            "solid",
            fgColor=BLUE
        )

        cell.border = border

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True
        )

    ws.row_dimensions[
        header_row
    ].height = 28

    # ======================================================
    # 18. SỐ DƯ ĐẦU KỲ
    # ======================================================

    opening_row = 13

    ws.merge_cells(
        start_row=opening_row,
        start_column=1,
        end_row=opening_row,
        end_column=6
    )

    ws.cell(
        opening_row,
        1
    ).value = "SỐ DƯ ĐẦU KỲ"

    ws.cell(
        opening_row,
        1
    ).font = bold_font

    ws.cell(
        opening_row,
        1
    ).fill = PatternFill(
        "solid",
        fgColor=YELLOW
    )

    ws.cell(
        opening_row,
        1
    ).alignment = Alignment(
        horizontal="center"
    )

    ws.cell(
        opening_row,
        8
    ).value = opening_balance

    ws.cell(
        opening_row,
        8
    ).number_format = '#,##0'

    for col in range(1, 10):

        ws.cell(
            opening_row,
            col
        ).border = border

        ws.cell(
            opening_row,
            col
        ).fill = PatternFill(
            "solid",
            fgColor=YELLOW
        )

    # ======================================================
    # 19. DÒNG HÓA ĐƠN
    # ======================================================

    row = opening_row + 1

    for index, item in enumerate(
        invoice_rows,
        start=1
    ):

        inv = item["invoice"]

        values = [

            index,

            inv.so_hoa_don,

            inv.ngay_hd,

            decimal(inv.tong_tien),

            item["bank_docs"],

            item["cash_paid"],

            item["paid"],

            item["remaining"],

            item["content"],
        ]

        for col, value in enumerate(
            values,
            start=1
        ):

            cell = ws.cell(
                row=row,
                column=col,
                value=value
            )

            cell.font = normal_font
            cell.border = border

            cell.alignment = Alignment(
                vertical="center",
                wrap_text=True
            )

        # --------------------------------------------------
        # Căn giữa
        # --------------------------------------------------

        for col in [
            1,
            2,
            3,
            5
        ]:

            ws.cell(
                row,
                col
            ).alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True
            )

        # --------------------------------------------------
        # Số tiền
        # --------------------------------------------------

        for col in [
            4,
            6,
            7,
            8
        ]:

            ws.cell(
                row,
                col
            ).number_format = '#,##0'

            ws.cell(
                row,
                col
            ).alignment = Alignment(
                horizontal="right",
                vertical="center"
            )

        # --------------------------------------------------
        # Ngày
        # --------------------------------------------------

        ws.cell(
            row,
            3
        ).number_format = "dd/mm/yyyy"

        row += 1

    # ======================================================
    # 20. TỔNG CỘNG
    # ======================================================

    total_row = row

    ws.merge_cells(
        start_row=total_row,
        start_column=1,
        end_row=total_row,
        end_column=3
    )

    ws.cell(
        total_row,
        1
    ).value = "TỔNG CỘNG"

    ws.cell(
        total_row,
        1
    ).font = bold_font

    ws.cell(
        total_row,
        1
    ).alignment = Alignment(
        horizontal="center"
    )

    # Tổng hóa đơn
    ws.cell(
        total_row,
        4
    ).value = total_invoice

    # Tổng phiếu ngân hàng
    ws.cell(
        total_row,
        5
    ).value = total_bank_paid

    # Tổng phiếu TM
    ws.cell(
        total_row,
        6
    ).value = total_cash_paid

    # Tổng đã thu
    ws.cell(
        total_row,
        7
    ).value = total_paid

    # Tổng còn nợ
    ws.cell(
        total_row,
        8
    ).value = (
        total_invoice
        - total_paid
    )

    for col in range(1, 10):

        cell = ws.cell(
            total_row,
            col
        )

        cell.font = bold_font
        cell.border = border

        cell.fill = PatternFill(
            "solid",
            fgColor=LIGHT_BLUE
        )

    for col in range(4, 9):

        ws.cell(
            total_row,
            col
        ).number_format = '#,##0'

        ws.cell(
            total_row,
            col
        ).alignment = Alignment(
            horizontal="right"
        )

    # ======================================================
    # 21. SỐ DƯ CUỐI KỲ
    # ======================================================

    closing_row = total_row + 1

    ws.merge_cells(
        start_row=closing_row,
        start_column=1,
        end_row=closing_row,
        end_column=7
    )

    ws.cell(
        closing_row,
        1
    ).value = (
        "SỐ DƯ CUỐI KỲ "
        "(PHẢI THU / PHẢI TRẢ)"
    )

    ws.cell(
        closing_row,
        1
    ).font = Font(
        name="Arial",
        size=10,
        bold=True,
        color=RED
    )

    ws.cell(
        closing_row,
        1
    ).fill = PatternFill(
        "solid",
        fgColor=YELLOW
    )

    ws.cell(
        closing_row,
        1
    ).alignment = Alignment(
        horizontal="center"
    )

    ws.cell(
        closing_row,
        8
    ).value = closing_balance

    ws.cell(
        closing_row,
        8
    ).font = Font(
        name="Arial",
        size=10,
        bold=True,
        color=RED
    )

    ws.cell(
        closing_row,
        8
    ).number_format = '#,##0'

    ws.cell(
        closing_row,
        8
    ).alignment = Alignment(
        horizontal="right"
    )

    for col in range(1, 10):

        ws.cell(
            closing_row,
            col
        ).border = border

        ws.cell(
            closing_row,
            col
        ).fill = PatternFill(
            "solid",
            fgColor=YELLOW
        )

    # ======================================================
    # 22. ĐỊNH DẠNG CỘT
    # ======================================================

    widths = {
        "A": 7,
        "B": 16,
        "C": 15,
        "D": 18,
        "E": 24,
        "F": 16,
        "G": 16,
        "H": 16,
        "I": 60,
    }

    for column, width in widths.items():

        ws.column_dimensions[
            column
        ].width = width

    # ======================================================
    # 23. FONT TOÀN BỘ SHEET
    # ======================================================

    for row_cells in ws.iter_rows():

        for cell in row_cells:

            if cell.font.name is None:

                cell.font = normal_font

    # ======================================================
    # 24. CỐ ĐỊNH HEADER
    # ======================================================

    ws.freeze_panes = "A13"

    # ======================================================
    # 25. IN ẤN
    # ======================================================

    ws.sheet_view.showGridLines = True

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4

    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    ws.sheet_properties.pageSetUpPr.fitToPage = True

    ws.page_margins = PageMargins(
        left=0.25,
        right=0.25,
        top=0.5,
        bottom=0.5,
        header=0.2,
        footer=0.2,
    )

    ws.print_title_rows = "1:12"

    ws.print_area = (
        f"A1:I{closing_row}"
    )

    # ======================================================
    # 26. TRẢ FILE
    # ======================================================

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    filename = (
        f"Cong_no_"
        f"{customer.ma_so_thue}_"
        f"{today.strftime('%Y%m%d')}.xlsx"
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; filename="{filename}"'
    )

    wb.save(response)

    return response