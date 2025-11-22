from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Sum, FloatField, ExpressionWrapper, F
from django.core.paginator import Paginator
from django.contrib import messages
from invoice_reader_app.model_invoice import Customer, InvoiceItem
from django.db.models import FloatField, F, Sum, ExpressionWrapper
from django.db.models import Sum, FloatField, F, ExpressionWrapper
from django.db.models import F, Sum, FloatField, ExpressionWrapper, Min, Max
from django.db.models import Sum, FloatField, F, ExpressionWrapper
from django.core.paginator import Paginator
from django.db.models import Sum, FloatField, F, ExpressionWrapper
from django.core.paginator import Paginator
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.core.paginator import Paginator

from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum, F, FloatField, ExpressionWrapper, Q
from invoice_reader_app.model_invoice import Customer, InvoiceItem

def customers_view(request):
    search_customer = request.GET.get('search_customer', '').strip()

    # Lấy danh sách khách hàng từ model Customer
    customers_qs = Customer.objects.all()

    # Tìm kiếm theo tên hoặc MST
    if search_customer:
        customers_qs = customers_qs.filter(
            Q(ten_khach_hang__icontains=search_customer) |
            Q(ma_so_thue__icontains=search_customer)
        )

    # (Tùy chọn) Tính tổng số lượng, tổng tiền, tổng tiền thuế từ hóa đơn liên quan
    customers_qs = customers_qs.annotate(
        total_so_luong=Sum('invoiceitem__so_luong'),
        total_thanh_tien=Sum(
            ExpressionWrapper(
                F('invoiceitem__so_luong') * F('invoiceitem__don_gia'),
                output_field=FloatField()
            )
        ),
        total_tien_thue=Sum(
            ExpressionWrapper(
                F('invoiceitem__so_luong') * F('invoiceitem__don_gia') * F('invoiceitem__thue_suat') / 100,
                output_field=FloatField()
            )
        )
    ).order_by('ten_khach_hang')

    # Phân trang: 10 khách hàng/trang
    paginator = Paginator(customers_qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'customers': page_obj,
        'search_customer': search_customer,
    }
    return render(request, 'customers.html', context)


# --- Thêm khách hàng ---
def customer_add(request):
    if request.method == 'POST':
        ma_so_thue = request.POST.get('ma_so_thue')
        ten_khach_hang = request.POST.get('ten_khach_hang')
        dia_chi = request.POST.get('dia_chi')
        phan_loai = request.POST.get('phan_loai')

        Customer.objects.create(
            ma_so_thue=ma_so_thue,
            ten_khach_hang=ten_khach_hang,
            dia_chi=dia_chi,
            phan_loai=phan_loai,
           
        )
        return redirect('customers')

    return render(request, 'customer_form.html', {'action': 'Thêm'})


# --- Chỉnh sửa khách hàng ---
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)


    # Nếu là "Cung cấp hàng hoá", lấy danh mục sản phẩm liên quan đến khách hàng
    products = []
    if customer.phan_loai == "Cung cấp hàng hoá":
        products = InvoiceItem.objects.filter(
            customer=customer,
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
        customer.ten_khach_hang = request.POST.get('ten_khach_hang', '').strip()
        customer.ma_so_thue = request.POST.get('ma_so_thue', '').strip()
        customer.dia_chi = request.POST.get('dia_chi', '').strip()
        customer.phan_loai = request.POST.get('phan_loai', '').strip()
        customer.save()
        messages.success(request, "✅ Cập nhật khách hàng thành công!")
        return redirect('customers')

    return render(request, 'customer_form.html', {
        'customer': customer,
        'action': 'Chỉnh sửa',
        'products': products,
    })


# --- Xóa khách hàng ---
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.delete()
    messages.success(request, "Đã xóa khách hàng.")
    return redirect("customers")

