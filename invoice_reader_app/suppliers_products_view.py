from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.core.paginator import Paginator
from invoice_reader_app.model_invoice import Supplier
from django.contrib import messages
from invoice_reader_app.forms import SupplierForm


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

    # Phân trang
    page_size = 10
    page_number = request.GET.get('page', 1)
    paginator = Paginator(suppliers, page_size)

    context = {
        'suppliers': paginator.get_page(page_number),
        'search_supplier': search_supplier,
    }
    return render(request, 'suppliers.html', context)



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


from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum, FloatField, ExpressionWrapper, Q
from invoice_reader_app.model_invoice import InvoiceItem, Invoice
from django.db.models import Sum, FloatField, ExpressionWrapper, Q
from django.core.paginator import Paginator
from invoice_reader_app.model_invoice import Supplier, InvoiceItem

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




def supplier_delete(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    if request.method == 'POST':
        supplier.delete()
        return redirect('suppliers')

    return render(request, 'supplier_confirm_delete.html', {'supplier': supplier})
