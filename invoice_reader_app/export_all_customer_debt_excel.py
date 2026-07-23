from openpyxl import Workbook
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum
from invoice_reader_app.model_invoice import Supplier, InvoiceItem, Invoice
from invoice_reader_app.models_purchaseorder import BankPayment, PurchaseOrder, CashReceipt, BankPaymentAllocation

def export_all_customer_debt_excel(request):

    invoices = (
        Invoice.objects
        .exclude(loai_hd="TMP")
        .select_related()
        .order_by(
            "ma_so_thue_mua",
            "ngay_hd"
        )
    )


    wb = Workbook()

    ws = wb.active
    ws.title = "Chi tiết công nợ"


    ws.append([
        "STT",
        "Khách hàng",
        "MST",
        "Ngày HĐ",
        "Số hóa đơn",
        "Tiền hóa đơn",
        "Thu NH/PO",
        "Thu tiền mặt",
        "Tổng đã thu",
        "Còn nợ",
    ])


    stt = 1


    for inv in invoices:


        invoice_amount = (
            inv.tong_tien
            or Decimal("0")
        )


        # ===== Thu theo PO / NH =====

        paid_bank = (
            BankPaymentAllocation.objects
            .filter(
                purchase_order__invoice=inv,
                payment__is_summary=True
            )
            .aggregate(
                total=Sum(
                    "allocated_amount"
                )
            )
            ["total"]
            or Decimal("0")
        )


        # ===== Thu tiền mặt =====

        paid_cash = (
            CashReceipt.objects
            .filter(
                invoice=inv
            )
            .aggregate(
                total=Sum("amount")
            )
            ["total"]
            or Decimal("0")
        )


        total_paid = (
            paid_bank +
            paid_cash
        )


        debt = (
            invoice_amount -
            total_paid
        )


        ws.append([
            stt,
            inv.ten_nguoi_mua,
            inv.ma_so_thue_mua,
            inv.ngay_hd.strftime(
                "%d/%m/%Y"
            ) if inv.ngay_hd else "",
            inv.so_hoa_don,
            float(invoice_amount),
            float(paid_bank),
            float(paid_cash),
            float(total_paid),
            float(debt),
        ])


        stt += 1



    # chỉnh độ rộng cột

    widths = [
        8,25,15,15,20,
        15,15,15,15,15
    ]

    for i,w in enumerate(widths,1):
        ws.column_dimensions[
            chr(64+i)
        ].width = w



    filename = (
        "chi_tiet_cong_no_khach_hang_"
        + timezone.now().strftime("%Y%m%d")
        + ".xlsx"
    )


    response = HttpResponse(
        content_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )


    wb.save(response)

    return response