from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.core.paginator import Paginator
from invoice_reader_app.model_invoice import Supplier
from django.contrib import messages
from invoice_reader_app.forms import SupplierForm
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum, FloatField, ExpressionWrapper, Q
from invoice_reader_app.model_invoice import InvoiceItem, Invoice
from django.db.models import Sum, FloatField, ExpressionWrapper, Q
from django.core.paginator import Paginator
from invoice_reader_app.model_invoice import Supplier, InvoiceItem
from .models_purcharoder import BankPayment, PurchaseOrder
def suppliers_view(request):
    search_supplier = request.GET.get('search_supplier', '')

    # Lấy tất cả nhà cung cấp
    suppliers = Supplier.objects.all()

    # Lọc tìm kiếm
    if search_supplier:
        suppliers = suppliers.filter(
            Q(ten_dv_ban__icontains=search_supplier) |
            Q(ma_so_thue__icontains=search_supplier)
        )

    # Thêm order_by để tránh cảnh báo
    suppliers = suppliers.order_by('ten_dv_ban')

    # Phân trang: 10 khách hàng/trang
    paginator = Paginator(suppliers, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Xử lý query params khác ngoài page (để giữ khi chuyển trang)
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')

# --- LẤY CHI TIẾT HÓA ĐƠN THEO TỪNG NHÀ CUNG CẤP ---
    supplier_invoices = {}
    supplier_totals = {}  # <-- thêm dòng này
    for s in page_obj:
        invoices = Invoice.objects.filter(
            ma_so_thue=s.ma_so_thue,
            loai_hd="VAO"   # hóa đơn đầu vào (nhà cung cấp)
        ).order_by('-ngay_hd')

        supplier_invoices[s.ma_so_thue] = invoices

        supplier_totals[s.ma_so_thue] = {
            'tong_tien_hang': round(sum(inv.tong_tien_hang for inv in invoices), 2),
            'tong_tien_thue': round(sum(inv.tong_tien_thue for inv in invoices), 2),
            'tong_tien': round(sum(inv.tong_tien for inv in invoices), 2),
        }



    query_params = request.GET.copy()
    query_params.pop('page', None)

    return render(request, 'suppliers.html', {
        'suppliers': page_obj,
        'data': page_obj,
        'search_supplier': search_supplier,
        'query_params': query_params.urlencode(),
        'label': 'nhà cung cấp',
        'supplier_invoices': supplier_invoices,
        'supplier_totals': supplier_totals,  # <-- thêm dòng này
    })



def supplier_add(request):
    if request.method == 'POST':
        ma_so_thue = request.POST.get('ma_so_thue')
        ten_dv_ban = request.POST.get('ten_dv_ban')
        dia_chi = request.POST.get('dia_chi')
        phan_loai = request.POST.get('phan_loai')

        Supplier.objects.create(
            ma_so_thue=ma_so_thue,
            ten_dv_ban=ten_dv_ban,
            dia_chi=dia_chi,
            phan_loai=phan_loai
        )
        return redirect('suppliers')

    return render(request, 'supplier_form.html', {'action': 'Thêm'})




def supplier_edit(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)

    # Nếu là "Cung cấp hàng hoá", lấy danh mục sản phẩm của nhà cung cấp này
    products = []
    if supplier.phan_loai == "Cung cấp hàng hoá":
        products = InvoiceItem.objects.filter(
            invoice__supplier=supplier,
            so_luong__gt=0
        ).values(
            'ten_hang'
        ).annotate(
            total_so_luong=Sum('so_luong'),
            total_thanh_tien=Sum('thanh_tien'),
            total_tien_thue=Sum('tien_thue'),
            avg_don_gia=ExpressionWrapper(
                (Sum('thanh_tien') + Sum('tien_thue')) / Sum('so_luong'),
                output_field=FloatField()
            )
        ).order_by('ten_hang')

    if request.method == 'POST':
        supplier.ten_dv_ban = request.POST.get('ten_dv_ban', '').strip()
        supplier.ma_so_thue = request.POST.get('ma_so_thue', '').strip()
        supplier.dia_chi = request.POST.get('dia_chi', '').strip()
        supplier.phan_loai = request.POST.get('phan_loai', '').strip()
        supplier.save()
        messages.success(request, "✅ Cập nhật nhà cung cấp thành công!")
        return redirect('suppliers')

    return render(request, 'supplier_form.html', {
        'supplier': supplier,
        'action': 'Chỉnh sửa',
        'products': products,  # truyền sản phẩm vào template
    })







def supplier_detail_view(request, id):
    # Lấy supplier theo id
    supplier = get_object_or_404(Supplier, id=id)

    # Lấy danh sách hóa đơn của nhà cung cấp
    invoices = Invoice.objects.filter(ma_so_thue=supplier.ma_so_thue, loai_hd='VAO').order_by('-ngay_hd')
    # Lấy chi tiết từng hóa đơn (có tổng tiền hàng, thuế, thanh toán)
    invoice_details = []

    for inv in invoices:
        invoice_details.append({
            'so_hoa_don': inv.so_hoa_don,
            'ngay_hd': inv.ngay_hd,
            'tong_tien_hang': inv.tong_tien_hang,
            'tong_tien_thue': inv.tong_tien_thue,
            'tong_tien': inv.tong_tien,
            'hinh_thuc_tt': inv.hinh_thuc_tt,

        })

    # Tính tổng cộng
    totals = {
        'tong_tien_hang': sum(inv.tong_tien_hang for inv in invoices),
        'tong_tien_thue': sum(inv.tong_tien_thue for inv in invoices),
        'tong_tien': sum(inv.tong_tien for inv in invoices),
    }

    return render(request, 'supplier_detail.html', {
        'supplier': supplier,
        'invoices': invoices,
        'totals': totals,
        'invoices': invoice_details,
    })



def supplier_delete(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    if request.method == 'POST':
        supplier.delete()
        return redirect('suppliers')

    return render(request, 'supplier_confirm_delete.html', {'supplier': supplier})