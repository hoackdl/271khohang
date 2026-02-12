


from invoice_reader_app.model_invoice import Customer, InvoiceItem, Invoice
from decimal import Decimal
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.http import HttpResponse
import openpyxl
from invoice_reader_app.model_invoice import InvoiceItem, ProductName
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from .models_purcharoder import PurchaseOrder, PurchaseOrderItem
from datetime import datetime
from django.db.models import Sum

def get_avg_export_price(sku):
    qs = (
        PurchaseOrderItem.objects
        .filter(
            purchase_order__phan_loai_phieu='PX',
            sku=sku
        )
        .aggregate(
            tong_qty=Sum('quantity'),
            tong_tien=Sum('total_price')
        )
    )

    qty = qs['tong_qty'] or 0
    tien = qs['tong_tien'] or 0

    return tien / qty if qty else 0



from django.utils import timezone
from django.db.models import Max

def generate_temp_invoice_number():
    today = timezone.now().date()
    prefix = f"TMP-{today.strftime('%Y%m%d')}-"

    last_invoice = Invoice.objects.filter(
        so_hoa_don__startswith=prefix
    ).aggregate(max_no=Max("so_hoa_don"))["max_no"]

    if last_invoice:
        last_number = int(last_invoice.split("-")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:04d}"


@login_required
@transaction.atomic
def create_export_invoice(request):
    if request.method == "POST":
        # =========================
        # 1️⃣ KHÁCH HÀNG
        # =========================
        customer_id = request.POST.get("customer_id", "").strip()
        mst = request.POST.get("mst", "").strip()
        ten_khach_hang = request.POST.get("ten_khach_hang", "").strip()
        dia_chi = request.POST.get("dia_chi", "").strip()
        email = request.POST.get("email", "").strip()


        customer = None

        if customer_id:
            try:
                customer = Customer.objects.get(id=int(customer_id))
            except (Customer.DoesNotExist, ValueError):
                return HttpResponseBadRequest("❌ Khách hàng không hợp lệ")

        # 🔥 Nếu chưa có customer nhưng có MST → tự tạo
        if not customer and mst:
            customer, _ = Customer.objects.get_or_create(
                ma_so_thue=mst,
                defaults={
                    "ten_khach_hang": ten_khach_hang or "Chưa xác định",
                    "dia_chi": dia_chi,
                }
            )

        if not customer:
            return HttpResponseBadRequest("❌ Không xác định được khách hàng")

        # =========================
        # 2️⃣ TẠO HOÁ ĐƠN
        # =========================
  

        ngay_hd_str = request.POST.get("ngay_hd")
        if not ngay_hd_str:
            return HttpResponseBadRequest("❌ Thiếu ngày hoá đơn")

        try:
            ngay_hd = datetime.strptime(ngay_hd_str, "%Y-%m-%d").date()
        except ValueError:
            return HttpResponseBadRequest("❌ Ngày hoá đơn không hợp lệ")

        invoice = Invoice.objects.create(
            loai_hd="TMP",      # ✅ đổi từ XUAT thành TMP
            ngay_hd=ngay_hd,
            so_hoa_don=generate_temp_invoice_number(),
            ky_hieu="TMP",
            ma_so_thue="0314858906",
            ten_nguoi_mua=customer.ten_khach_hang,
            ma_so_thue_mua=customer.ma_so_thue,
            dia_chi_mua=customer.dia_chi,
            email=email,
            trang_thai="DRAFT",   # đổi luôn cho rõ nghĩa
            tong_tien_hang=0,
            tong_tien_thue=0,
            tong_tien=0,
        )

        # =========================
        # 3️⃣ DÒNG SẢN PHẨM
        # =========================
        total_tien = 0
        total_thue = 0

        try:
            items_count = int(request.POST.get("items_count", 0))
        except ValueError:
            items_count = 0

        for i in range(items_count):
            sku = request.POST.get(f"sku_{i}", "").strip()
            ten_hang = request.POST.get(f"ten_goi_chung_{i}", "").strip()
            dvt = request.POST.get(f"dvt_{i}", "").strip()   # ✅ THÊM DÒNG NÀY



            if not sku:
                continue  # bỏ dòng trống

            try:
                so_luong = Decimal(request.POST.get(f"so_luong_{i}", "0"))
                don_gia = Decimal(request.POST.get(f"don_gia_{i}", "0"))



                # 🔥 Nếu frontend chưa có giá → backend tự lấy giá TB xuất
                if don_gia <= 0:
                    don_gia = get_avg_export_price(sku)

                thue_suat = Decimal(request.POST.get(f"thue_suat_{i}", "0"))
            except ValueError:
                continue

            if so_luong <= 0:
                continue

            thanh_tien = so_luong * don_gia
            tien_thue = thanh_tien * thue_suat / 100

            InvoiceItem.objects.create(
                invoice=invoice,
                sku=sku,
                ten_hang=ten_hang,
                dvt=dvt,
                so_luong=so_luong,
                don_gia=don_gia,
                thanh_tien=thanh_tien,
                thue_suat=thue_suat,   # 👈 QUAN TRỌNG
                tien_thue=tien_thue,
            )

            total_tien += thanh_tien
            total_thue += tien_thue

        if total_tien == 0:
            return HttpResponseBadRequest("❌ Hoá đơn không có sản phẩm")

        # =========================
        # 4️⃣ TỔNG TIỀN
        # =========================
        invoice.tong_tien_hang = total_tien
        invoice.tong_tien_thue = total_thue
        invoice.tong_tien = total_tien + total_thue
        invoice.save()

        return redirect("export_invoice_waiting_list")


    # =========================
    # GET
    # =========================
    customers = Customer.objects.all().order_by("ten_khach_hang")
    return render(request, "create_export_invoice.html", {
        "customers": customers
    })

@login_required
@transaction.atomic
def export_invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.loai_hd == "TMP":

        if request.method == "POST":
            invoice.items.all().delete()

            total_tien = Decimal("0")
            total_thue = Decimal("0")

            items_count = int(request.POST.get("items_count", 0))

            for i in range(items_count):
                sku = request.POST.get(f"sku_{i}", "").strip()
                if not sku:
                    continue

                so_luong = Decimal(request.POST.get(f"so_luong_{i}", "0"))
                don_gia = Decimal(request.POST.get(f"don_gia_{i}", "0"))
                thue_suat = Decimal(request.POST.get(f"thue_suat_{i}", "0"))
                ten_hang = request.POST.get(f"ten_hang_{i}", "")
                dvt = request.POST.get(f"dvt_{i}", "")

                thanh_tien = so_luong * don_gia
                tien_thue = thanh_tien * thue_suat / 100

                InvoiceItem.objects.create(
                    invoice=invoice,
                    sku=sku,
                    ten_hang=ten_hang,
                    dvt=dvt,
                    so_luong=so_luong,
                    don_gia=don_gia,
                    thanh_tien=thanh_tien,
                    thue_suat=thue_suat,
                    tien_thue=tien_thue,
                )

                total_tien += thanh_tien
                total_thue += tien_thue

            invoice.tong_tien_hang = total_tien
            invoice.tong_tien_thue = total_thue
            invoice.tong_tien = total_tien + total_thue
            invoice.save()

            return redirect("export_invoice_detail", pk=pk)

        return render(request, "export_invoice_edit.html", {
            "invoice": invoice,
            "items": invoice.items.all(),
        })

    # Nếu không phải TMP → chỉ xem
    return render(request, "export_invoice_detail.html", {
        "invoice": invoice,
        "items": invoice.items.all(),
    })


from django.db.models import Q


from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

@login_required
def export_invoice_mark_done(request, pk):
    invoice = get_object_or_404(
        Invoice,
        pk=pk,
        
    )

    invoice.trang_thai = "DA_XUAT"
    invoice.save(update_fields=["trang_thai"])

    return redirect("export_invoice_detail", pk=pk)


@login_required
def export_invoice_waiting_list(request):
    invoices = (
        Invoice.objects
        
        .exclude(file_name__isnull=False)
        .exclude(file_name="")
        .order_by("-id")
    )

    paginator = Paginator(invoices, 20)
    page = request.GET.get("page")

    return render(request, "export_invoice_waiting_list.html", {
        "invoices": paginator.get_page(page)
    })


from django.views.decorators.http import require_POST
from django.contrib import messages

@login_required
@require_POST
def export_invoice_bulk_delete(request):
    ids = request.POST.getlist("invoice_ids")

    if not ids:
        messages.warning(request, "Chưa chọn phiếu nào")
        return redirect("export_invoice_waiting_list")

    Invoice.objects.filter(
        id__in=ids,
        loai_hd="TMP",
        file_name__isnull=True   # 🔒 chỉ cho xoá phiếu tạo tay
    ).delete()

    messages.success(request, f"Đã xoá {len(ids)} phiếu")

    return redirect("export_invoice_waiting_list")
