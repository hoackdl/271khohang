from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Exists, OuterRef
from invoice_reader_app.model_invoice import Invoice
from invoice_reader_app.models_purcharoder import PurchaseOrderItem
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Exists, OuterRef, IntegerField, Value, Case, When
from django.db.models.functions import Cast
from invoice_reader_app.model_invoice import Invoice
from invoice_reader_app.models_purcharoder import PurchaseOrderItem


def invoice_export_list(request):
    # --- Ép số hóa đơn sang số nguyên an toàn --- Danh sách hóa đơn xuất
    invoices = Invoice.objects.filter(
        ma_so_thue='0314858906',
        loai_hd='XUAT'
    ).annotate(
        so_hd_int=Case(
            When(so_hoa_don__regex=r'^\d+$', then=Cast('so_hoa_don', IntegerField())),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('-so_hd_int', '-ngay_hd')   # sắp theo số HĐ giảm dần, sau đó theo ngày

    # --- Lọc dữ liệu theo GET ---
    search = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    per_page = request.GET.get('per_page', '10').strip()

    if search:
        invoices = invoices.filter(
            Q(ten_nguoi_mua__icontains=search) |
            Q(ma_so_thue_mua__icontains=search) |
            Q(so_hoa_don__icontains=search)
        )

    if start_date:
        invoices = invoices.filter(ngay_hd__gte=start_date)
    if end_date:
        invoices = invoices.filter(ngay_hd__lte=end_date)

    # --- Annotate trạng thái phiếu xuất ---
    po_export_subquery = PurchaseOrderItem.objects.filter(
        purchase_order__invoice=OuterRef('pk'),
        is_export=True
    )
    invoices = invoices.annotate(has_exported=Exists(po_export_subquery))

    # --- Phân trang ---
    if per_page.lower() == 'all':
        paginated_invoices = invoices
        page_number = None
    else:
        try:
            per_page_int = int(per_page)
        except ValueError:
            per_page_int = 10

        paginator = Paginator(invoices, per_page_int)
        page_number = request.GET.get('page', 1)
        try:
            paginated_invoices = paginator.get_page(page_number)
        except (EmptyPage, PageNotAnInteger):
            paginated_invoices = paginator.get_page(1)

    context = {
        'invoices': paginated_invoices,
        'search': search,
        'start_date': start_date,
        'end_date': end_date,
        'per_page': per_page,
        'page_number': page_number,
    }

    return render(request, 'invoice_export_list.html', context)



import openpyxl
from django.http import HttpResponse

def export_invoices_excel(request):
    invoices = Invoice.objects.all()  # Có thể lọc theo GET params giống danh sách

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hóa đơn"

    # Header
    headers = [
        "Số HĐ", "Ngày HĐ", "Tên đơn vị bán", "MST", "Địa chỉ", "HT Thanh toán", "Tổng tiền"
    ]
    ws.append(headers)

    for inv in invoices:
        ws.append([
            inv.so_hoa_don,
            inv.ngay_hd.strftime("%d/%m/%Y") if inv.ngay_hd else "",
            inv.ten_dv_ban,
            inv.ma_so_thue,
            inv.dia_chi,
            inv.hinh_thuc_tt,
            inv.tong_tien
        ])

    # Trả file Excel về client
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=invoices.xlsx'
    wb.save(response)
    return response
