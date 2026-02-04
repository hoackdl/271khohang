# views.py
from django.shortcuts import render
from django.http import JsonResponse
from invoice_reader_app.model_invoice import Invoice, InvoiceItem, Supplier
from invoice_reader_app.upload_invoice import parse_invoice_xml  # hàm parse XML
import json
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import pandas as pd  # ← thêm dòng này
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q, Sum
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from django.utils.dateparse import parse_date
import json
from invoice_reader_app.model_invoice import Invoice, InvoiceItem, Supplier, Customer, ProductName
from datetime import datetime
from datetime import datetime
from decimal import Decimal

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None

import re

def normalize(t):
    if not t:
        return ""
    return re.sub(r"\s+", "", t).strip().upper()

def normalize_ky_hieu(value):
    if not value:
        return ""
    return (
        str(value)
        .strip()
        .strip("'")
        .strip('"')
        .replace(" ", "")
    )

import hashlib

def invoice_business_hash(ma_so_thue, ky_hieu, so_hoa_don, ngay_hd, loai_hd):
    raw = f"{ma_so_thue}|{ky_hieu}|{so_hoa_don}|{ngay_hd}|{loai_hd}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def upload_invoices(request):
    """Upload nhiều file XML và preview nội dung"""
    if request.method == "POST":
        files = request.FILES.getlist('files')
        invoices_preview = []

        for f in files:
            try:
                invoice_data, items_data = parse_invoice_xml(f)
                invoices_preview.append({
                    "invoice": invoice_data,
                    "items": items_data,
                    "file_name": f.name
                })
            except Exception as e:
                continue

        return JsonResponse({"invoices_preview": invoices_preview})

    return render(request, 'uploads.html')


from decimal import Decimal, ROUND_HALF_UP
@require_POST
def save_multiple_invoices(request):
    try:
        data = json.loads(request.body)
        invoices_list = data.get("invoices", [])
        is_export = data.get("export", False)

        with transaction.atomic():
            for pack in invoices_list:
                inv = pack.get("invoice", {})
                items = pack.get("items", [])
                file_name = pack.get("file_name", "")

                so_hoa_don = normalize(inv.get("so_hoa_don"))
                ky_hieu = normalize_ky_hieu(inv.get("ky_hieu"))



                mau_so = normalize(inv.get("mau_so"))
                ma_so_thue = normalize(inv.get("ma_so_thue"))

                ngay_hd = parse_date(inv.get("ngay_hd")) if inv.get("ngay_hd") else None
                loai_hd = "XUAT" if is_export else "VAO"

                # Bỏ qua hóa đơn nội bộ nhà cung cấp của bạn (nếu cần)
                if loai_hd == "VAO" and ma_so_thue == "0314858906":
                    continue
                
                print({
                    "so_hoa_don": so_hoa_don,
                    "ky_hieu": repr(ky_hieu),
                    "ma_so_thue": ma_so_thue,
                    "ngay_hd": ngay_hd,
                    "loai_hd": loai_hd,
                })


                # 🧹 DỌN DUPLICATE CŨ (PHÒNG THỦ)
                # 🧹 DỌN DUPLICATE CŨ (PHÒNG THỦ – ĐÚNG CÁCH)
                qs = Invoice.objects.filter(
                    ma_so_thue=ma_so_thue,
                    ky_hieu=ky_hieu,
                    so_hoa_don=so_hoa_don,
                    ngay_hd=ngay_hd,
                    loai_hd=loai_hd,
                ).order_by("id")

                ids = list(qs.values_list("id", flat=True))

                if len(ids) > 1:
                    Invoice.objects.filter(id__in=ids[1:]).delete()


                
                # -----------------------------
                # TẠO / CẬP NHẬT HÓA ĐƠN
                # -----------------------------
                invoice_obj, created = Invoice.objects.update_or_create(
                    ma_so_thue=ma_so_thue,
                    ky_hieu=ky_hieu,
                    so_hoa_don=so_hoa_don,
                    ngay_hd=ngay_hd,
                    loai_hd=loai_hd,
                    defaults={
                        "mau_so": mau_so,
                        "hinh_thuc_tt": inv.get("hinh_thuc_tt") or "",
                        "ten_dv_ban": inv.get("ten_dv_ban") or "",
                        "dia_chi": inv.get("dia_chi") or "",
                        "ten_nguoi_mua": inv.get("ten_nguoi_mua") or "",
                        "ma_so_thue_mua": inv.get("ma_so_thue_mua") or "",
                        "dia_chi_mua": inv.get("dia_chi_mua") or "",
                        "so_tk": inv.get("so_tk") or "",
                        "ten_ngan_hang": inv.get("ten_ngan_hang") or "",
                        "tong_tien": to_decimal(inv.get("tong_tien")),
                        "file_name": file_name,
                    }
                )






                # -----------------------------
                # CẬP NHẬT NHÀ CUNG CẤP
                # -----------------------------
                supplier, _ = Supplier.objects.update_or_create(
                    ma_so_thue=invoice_obj.ma_so_thue,
                    defaults={
                        "ten_dv_ban": invoice_obj.ten_dv_ban,
                        "dia_chi": invoice_obj.dia_chi,
                    }
                )

                invoice_obj.supplier = supplier
                invoice_obj.save(update_fields=["supplier"])

                # -----------------------------
                # CẬP NHẬT KHÁCH HÀNG
                # -----------------------------
                Customer.objects.update_or_create(
                    ma_so_thue=invoice_obj.ma_so_thue_mua,
                    defaults={
                        "ten_khach_hang": invoice_obj.ten_nguoi_mua,
                        "dia_chi": invoice_obj.dia_chi_mua,
                    }
                )

                # 🔒 Ép save cho chắc
                # invoice_obj.save()

                # 🧹 Xóa item cũ (an toàn)
                if invoice_obj.pk:
                    InvoiceItem.objects.filter(invoice_id=invoice_obj.pk).delete()


                # -----------------------------
                # LƯU ITEM HÓA ĐƠN — KHÔNG TÍNH LẠI
                # -----------------------------
                invoice_items = []

                for item in items:
                    ten_hang = item.get("ten_hang") or ""

                    # Lookup product
                    if loai_hd == "VAO":
                        product = ProductName.objects.filter(ten_hang=ten_hang).first()
                    else:
                        product = ProductName.objects.filter(ten_goi_xuat=ten_hang).first()

                    ten_goi_chung = product.ten_goi_chung if product else None

                    # Chuẩn hóa thuế suất
                    raw_tax = item.get("thue_suat", 0)
                    raw_tax = str(raw_tax).replace("%", "").strip()
                    tax_rate = to_decimal(raw_tax)

                    # LẤY TRỰC TIẾP TỪ XML — KHÔNG TÍNH LẠI
                    so_luong = to_decimal(item.get("so_luong") or 0)
                    don_gia = to_decimal(item.get("don_gia") or 0)

                    thanh_tien_truoc_ck = to_decimal(item.get("thanh_tien_truoc_ck") or 0)
                    chiet_khau_item = to_decimal(item.get("chiet_khau") or 0)
                    thanh_tien_sau_ck = to_decimal(item.get("thanh_tien_sau_ck") or (thanh_tien_truoc_ck - chiet_khau_item))
                    tien_thue = to_decimal(item.get("tien_thue") or (thanh_tien_sau_ck * tax_rate / 100))
                    thanh_toan = to_decimal(item.get("thanh_toan") or (thanh_tien_sau_ck + tien_thue))

                    # TẠO ITEM
                    invoice_items.append(
                        InvoiceItem(
                            invoice_id=invoice_obj.pk,
                            ten_hang=ten_hang,
                            dvt=item.get("dvt"),

                            so_luong=so_luong,
                            don_gia=don_gia,

                            thanh_tien=thanh_tien_truoc_ck,  # trước CK
                            chiet_khau=chiet_khau_item,
                            tien_thue=tien_thue,
                            thue_suat=tax_rate,
                            thanh_toan=thanh_toan,

                            ten_goi_chung=ten_goi_chung,
                            supplier=invoice_obj.supplier,
                        )
                    )

                if invoice_items:
                    InvoiceItem.objects.bulk_create(invoice_items)

        return JsonResponse({"success": True})

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({"success": False, "error": str(e)})



# Utility function to ensure the conversion of any input to Decimal
def to_decimal(value):
    """Chuyển mọi giá trị sang Decimal, nếu không có giá trị thì trả về Decimal(0)"""
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except:
        return Decimal("0")




from django.db.models import Sum, Q

def invoice_summary(request):
    qs = Invoice.objects.all()

    # 🔹 Bộ lọc
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    search = request.GET.get("search")
    per_page = request.GET.get("per_page", "10")

    if start_date:
        qs = qs.filter(ngay_hd__gte=start_date)
    if end_date:
        qs = qs.filter(ngay_hd__lte=end_date)
    if search:
        qs = qs.filter(
            Q(ten_dv_ban__icontains=search) |
            Q(ma_so_thue__icontains=search) |
            Q(so_hoa_don__icontains=search)
        )

    # 🔹 Tính tổng tiền hàng và thuế GTGT cho mỗi hóa đơn
    data_list = []
    for inv in qs:
        # Tính tổng tiền hàng, thuế và chiết khấu cho mỗi hóa đơn
        items = inv.items.aggregate(
            tong_tien_hang=Sum('thanh_tien'),
            tien_thue_gtgt=Sum('tien_thue'),
            tong_chiet_khau=Sum('chiet_khau')    # <-- thêm
        )
        inv.tong_tien_hang = items['tong_tien_hang'] or 0
        inv.tien_thue_gtgt = items['tien_thue_gtgt'] or 0
        inv.tong_chiet_khau = items['tong_chiet_khau'] or 0   # <-- thêm

        data_list.append(inv)

    # 🔹 Phân trang
    if per_page != "all":
        try:
            per_page = int(per_page)
            from django.core.paginator import Paginator
            paginator = Paginator(data_list, per_page)
            page_number = request.GET.get("page")
            data = paginator.get_page(page_number)
        except:
            data = data_list
    else:
        data = data_list

    context = {
        "data": data,
        "query_params": request.GET.urlencode(),
    }
    return render(request, "invoice_summary.html", context)

def invoice_summary_export_excel(request):
    invoice_ids = request.GET.get("invoice_ids")
    if invoice_ids:
        ids = [int(i) for i in invoice_ids.split(",")]
        qs = Invoice.objects.filter(id__in=ids)
    else:
        qs = Invoice.objects.all()  # Nếu không chọn gì, xuất tất cả

    # Tạo DataFrame và xuất Excel
    data_list = []
    for idx, inv in enumerate(qs, start=1):
        items = inv.items.aggregate(
            tong_tien_hang=Sum('thanh_tien'),
            tien_thue_gtgt=Sum('tien_thue')
        )
        data_list.append({
            "STT": idx,
            "Tên đơn vị bán": inv.ten_dv_ban,
            "Mã số thuế": inv.ma_so_thue,
            "Số hóa đơn": inv.so_hoa_don,
            "Ngày HĐ": inv.ngay_hd,
            "Tiền hàng": items['tong_tien_hang'] or 0,
            "Chiết khấu": items['tong_chiet_khau'] or 0,  # <-- thêm
            "Thuế GTGT": items['tien_thue_gtgt'] or 0,
            "Tổng tiền": inv.tong_tien,
        })


    df = pd.DataFrame(data_list)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response['Content-Disposition'] = f'attachment; filename=TongHop_HoaDon_{datetime.today().strftime("%Y%m%d")}.xlsx'

    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Tổng hợp hóa đơn')
        workbook  = writer.book
        worksheet = writer.sheets['Tổng hợp hóa đơn']
        money_format = workbook.add_format({'num_format': '#,##0'})
        worksheet.set_column('F:I', None, money_format)  # mở rộng cột để chiết khấu


    return response

@require_POST
def save_multiple_invoices(request):
    try:
        data = json.loads(request.body)
        invoices_list = data.get("invoices", [])
        is_export = data.get("export", False)

        with transaction.atomic():
            for pack in invoices_list:
                inv = pack.get("invoice", {})
                items = pack.get("items", [])
                file_name = pack.get("file_name", "")

                # =============================
                # 1️⃣ NORMALIZE BUSINESS KEY
                # =============================
                ky_hieu = normalize_ky_hieu(inv.get("ky_hieu"))
                so_hoa_don = normalize(inv.get("so_hoa_don"))
                mau_so = normalize(inv.get("mau_so"))
                ma_so_thue = normalize(inv.get("ma_so_thue"))

                ngay_hd = parse_date(inv.get("ngay_hd")) if inv.get("ngay_hd") else None
                loai_hd = "XUAT" if is_export else "VAO"

                # Skip nội bộ
                if loai_hd == "VAO" and ma_so_thue == "0314858906":
                    continue

                print({
                    "so_hoa_don": so_hoa_don,
                    "ky_hieu": repr(ky_hieu),
                    "ma_so_thue": ma_so_thue,
                    "ngay_hd": ngay_hd,
                    "loai_hd": loai_hd,
                })
                biz_hash = invoice_business_hash(
                    ma_so_thue,
                    ky_hieu,
                    so_hoa_don,
                    ngay_hd,
                    loai_hd,
                )

                print("🧾 INVOICE KEY:", biz_hash)

                # =============================
                # 2️⃣ DỌN DUPLICATE (PHÒNG THỦ)
                # =============================
                ids = list(
                    Invoice.objects.filter(
                        ma_so_thue=ma_so_thue,
                        ky_hieu=ky_hieu,
                        so_hoa_don=so_hoa_don,
                        ngay_hd=ngay_hd,
                        loai_hd=loai_hd,
                    )
                    .order_by("id")
                    .values_list("id", flat=True)
                )

                if len(ids) > 1:
                    Invoice.objects.filter(id__in=ids[1:]).delete()

                # =============================
                # 3️⃣ SUPPLIER (KHÔNG DÙNG invoice_obj)
                # =============================
                supplier, _ = Supplier.objects.update_or_create(
                    ma_so_thue=ma_so_thue,
                    defaults={
                        "ten_dv_ban": inv.get("ten_dv_ban") or "",
                        "dia_chi": inv.get("dia_chi") or "",
                    }
                )

                # =============================
                # 4️⃣ INVOICE (UPSERT DUY NHẤT)
                # =============================
                qs = Invoice.objects.filter(
                    ma_so_thue=ma_so_thue,
                    ky_hieu=ky_hieu,
                    so_hoa_don=so_hoa_don,
                    ngay_hd=ngay_hd,
                    loai_hd=loai_hd,
                ).order_by("id")

                invoice_obj = qs.first()

                if invoice_obj:
                    # update
                    for k, v in {
                        "mau_so": mau_so,
                        "supplier": supplier,
                        "hinh_thuc_tt": inv.get("hinh_thuc_tt") or "",
                        "ten_dv_ban": inv.get("ten_dv_ban") or "",
                        "dia_chi": inv.get("dia_chi") or "",
                        "ten_nguoi_mua": inv.get("ten_nguoi_mua") or "",
                        "ma_so_thue_mua": inv.get("ma_so_thue_mua") or "",
                        "dia_chi_mua": inv.get("dia_chi_mua") or "",
                        "so_tk": inv.get("so_tk") or "",
                        "ten_ngan_hang": inv.get("ten_ngan_hang") or "",
                        "tong_tien": to_decimal(inv.get("tong_tien")),
                        "file_name": file_name,
                    }.items():
                        setattr(invoice_obj, k, v)

                    invoice_obj.save()
                else:
                    invoice_obj = Invoice.objects.create(
                        ma_so_thue=ma_so_thue,
                        ky_hieu=ky_hieu,
                        so_hoa_don=so_hoa_don,
                        ngay_hd=ngay_hd,
                        loai_hd=loai_hd,
                        mau_so=mau_so,
                        supplier=supplier,
                        hinh_thuc_tt=inv.get("hinh_thuc_tt") or "",
                        ten_dv_ban=inv.get("ten_dv_ban") or "",
                        dia_chi=inv.get("dia_chi") or "",
                        ten_nguoi_mua=inv.get("ten_nguoi_mua") or "",
                        ma_so_thue_mua=inv.get("ma_so_thue_mua") or "",
                        dia_chi_mua=inv.get("dia_chi_mua") or "",
                        so_tk=inv.get("so_tk") or "",
                        ten_ngan_hang=inv.get("ten_ngan_hang") or "",
                        tong_tien=to_decimal(inv.get("tong_tien")),
                        file_name=file_name,
                    )


                # =============================
                # 5️⃣ CUSTOMER
                # =============================
                Customer.objects.update_or_create(
                    ma_so_thue=invoice_obj.ma_so_thue_mua,
                    defaults={
                        "ten_khach_hang": invoice_obj.ten_nguoi_mua,
                        "dia_chi": invoice_obj.dia_chi_mua,
                    }
                )

                # =============================
                # 6️⃣ ITEMS
                # =============================
                InvoiceItem.objects.filter(invoice_id=invoice_obj.pk).delete()

                invoice_items = []
                for item in items:
                    ten_hang = item.get("ten_hang") or ""

                    product = (
                        ProductName.objects.filter(
                            ten_hang=ten_hang if loai_hd == "VAO" else None,
                            ten_goi_xuat=ten_hang if loai_hd == "XUAT" else None,
                        ).first()
                    )

                    tax_rate = to_decimal(str(item.get("thue_suat", 0)).replace("%", ""))

                    invoice_items.append(
                        InvoiceItem(
                            invoice_id=invoice_obj.pk,
                            ten_hang=ten_hang,
                            dvt=item.get("dvt"),
                            so_luong=to_decimal(item.get("so_luong")),
                            don_gia=to_decimal(item.get("don_gia")),
                            thanh_tien=to_decimal(item.get("thanh_tien_truoc_ck")),
                            chiet_khau=to_decimal(item.get("chiet_khau")),
                            tien_thue=to_decimal(item.get("tien_thue")),
                            thue_suat=tax_rate,
                            thanh_toan=to_decimal(item.get("thanh_toan")),
                            ten_goi_chung=product.ten_goi_chung if product else None,
                            supplier=supplier,
                        )
                    )

                if invoice_items:
                    InvoiceItem.objects.bulk_create(invoice_items)

        return JsonResponse({"success": True})

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({"success": False, "error": str(e)})
