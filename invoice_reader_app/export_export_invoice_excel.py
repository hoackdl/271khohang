from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.http import HttpResponse
from io import BytesIO
import openpyxl
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
from decimal import Decimal, ROUND_HALF_UP


def no_decimal(v):
    if v is None:
        return 0
    return int(Decimal(v).quantize(0, rounding=ROUND_HALF_UP))



@login_required
@require_GET
def export_export_invoice_excel(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, loai_hd="TMP")
    items = invoice.items.all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "HoaDon"

    default_email = "tamanhlogistics@gmail.com"
    email = getattr(invoice, "email", "") or ""

    if email:
        # tránh trùng email mặc định
        email_list = [e.strip() for e in email.split(";") if e.strip()]
        if default_email not in email_list:
            email_list.append(default_email)
        email = ";".join(email_list)
    else:
        email = default_email


    headers = [
        "STT","IDChungTu/MaBill","TenHangHoaDichVu","DonViTinh/ChietKhau",
        "SoLuong","DonGia","ThanhTien","ThueSuat","TienThueGTGT",
        "NgayThangNamHD","HoTenNguoiMua","TenDonVi","MaSoThue","DiaChi",
        "SoTaiKhoan","HinhThucTT","NhanBangEmail","DSEmail",
        "NhanBangSMS","DSSMS","NhanBangBanIN","HoTenNguoiNhan",
        "SoDienThoaiNguoiNhan","SoNha","Tinh/ThanhPho",
        "Huyen/Quan/ThiXa","Xa/Phuong/ThiTran","GhiChu"
    ]
    ws.append(headers)

    for idx, item in enumerate(items, start=1):
        ws.append([
            idx,
            invoice.id,
            item.ten_hang,
            item.dvt,
            no_decimal(item.so_luong),
            no_decimal(item.don_gia),
            no_decimal(item.thanh_tien),
            no_decimal(item.thue_suat),
            no_decimal(item.tien_thue),
            invoice.ngay_hd.strftime("%d/%m/%Y"),
            "",
            invoice.ten_nguoi_mua,
            invoice.ma_so_thue_mua,
            invoice.dia_chi_mua,
            "",
            "TM/CK",
            "",
            email,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            ""
        ])


    output = BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="phieu_xuat_{invoice.id}.xlsx"'
    )
    return response
