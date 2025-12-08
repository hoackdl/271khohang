# invoices/views.py
import xml.etree.ElementTree as ET
from django.shortcuts import render, redirect
from invoice_reader_app.model_invoice import Invoice, InvoiceItem, Supplier
from .forms import UploadFileForm
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from .models_purcharoder import BankPayment
from datetime import datetime
from django.utils.dateparse import parse_date

from django.core.paginator import Paginator
from django.shortcuts import render
from django.core.paginator import Paginator

from django.db.models import F, Sum, FloatField, Case, When, Value
# Danh sách hóa đơn vào
from django.core.paginator import Paginator
from decimal import Decimal
from django.db.models import F, Sum, FloatField, Case, When, Value, Q
from django.db.models import Q, F, Value
from django.db.models.functions import Lower, Replace
from django.db.models.expressions import Func
# invoice_reader_app/views.py
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q, Sum
import unicodedata

from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.shortcuts import render
from .forms import UploadFileForm

import xml.etree.ElementTree as ET


def parse_invoice_xml(xml_file):
    """
    Parse hóa đơn XML và trả về:
    - invoice: dict thông tin chung
    - items: list các hàng hóa/dịch vụ
    """

    # ------------------------------
    # HÀM HỖ TRỢ
    # ------------------------------
    def parse_float(text):
        """Chuyển string sang float, bỏ dấu ',' và '%'"""
        if not text:
            return 0.0
        try:
            return float(text.replace(',', '').replace('%', '').strip())
        except:
            return 0.0

    def get_text_by_tag_all(root_elem, tag_name):
        """
        Duyệt tất cả node, bỏ namespace, và trả về text của node có tag_name
        """
        for elem in root_elem.iter():
            tag = elem.tag.split('}')[-1]
            if tag == tag_name:
                return (elem.text or '').strip()
        return ''

    # ------------------------------
    # ĐỌC XML
    # ------------------------------
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # ------------------------------
    # THÔNG TIN CHUNG HÓA ĐƠN
    # ------------------------------
    invoice = {
        'so_hoa_don': get_text_by_tag_all(root, 'SHDon'),
        'ngay_hd': get_text_by_tag_all(root, 'NLap'),
        'hinh_thuc_tt': get_text_by_tag_all(root, 'HTTToan'),
        'mau_so': get_text_by_tag_all(root, 'KHMSHDon'),
        'ky_hieu': get_text_by_tag_all(root, 'KHHDon'),

        'ten_dv_ban': get_text_by_tag_all(root, 'Ten') or '',
        'ma_so_thue': get_text_by_tag_all(root, 'MST') or '',
        'dia_chi': get_text_by_tag_all(root, 'DChi') or '',

        'so_tk': get_text_by_tag_all(root, 'SoTaiKhoan') or get_text_by_tag_all(root, 'STK') or '',
        'ten_ngan_hang': get_text_by_tag_all(root, 'TenNganHang') or get_text_by_tag_all(root, 'BankName') or '',

        'ten_nguoi_mua': '',
        'ma_so_thue_mua': '',
        'dia_chi_mua': '',
    }

    # Xác định loại hóa đơn
    mst_ban = invoice.get('ma_so_thue', '')
    invoice['loai_hd'] = 'XUAT' if mst_ban == '0314858906' else 'VAO'

    # ------------------------------
    # THÔNG TIN NGƯỜI MUA
    # ------------------------------
    nmua_el = None
    for elem in root.iter():
        if elem.tag.split('}')[-1] == 'NMua':
            nmua_el = elem
            break

    if nmua_el:
        invoice['ten_nguoi_mua'] = get_text_by_tag_all(nmua_el, 'Ten')
        invoice['ma_so_thue_mua'] = get_text_by_tag_all(nmua_el, 'MST')
        invoice['dia_chi_mua'] = get_text_by_tag_all(nmua_el, 'DChi')

    # ------------------------------
    # LẤY DANH SÁCH HÀNG HÓA / DỊCH VỤ
    # ------------------------------
    items = []
    tong_chiet_khau = 0.0

    item_elements = [elem for elem in root.iter() if elem.tag.split('}')[-1] == 'HHDVu']

    for i, item_el in enumerate(item_elements, start=1):
        ten_hang = get_text_by_tag_all(item_el, 'THHDVu')
        dvt = get_text_by_tag_all(item_el, 'DVTinh')
        so_luong = parse_float(get_text_by_tag_all(item_el, 'SLuong'))
        don_gia = parse_float(get_text_by_tag_all(item_el, 'DGia'))

        # Thành tiền trước chiết khấu
        thanh_tien_truoc_ck = so_luong * don_gia
        if thanh_tien_truoc_ck == 0:
            thanh_tien_truoc_ck = parse_float(get_text_by_tag_all(item_el, 'ThTien'))
            amount_ttkhac = get_text_by_tag_all(item_el, 'Amount')
            if amount_ttkhac:
                thanh_tien_truoc_ck = parse_float(amount_ttkhac)

        # Chiết khấu
        ck_dl = parse_float(get_text_by_tag_all(item_el, 'CKDL'))
        tl_ck = parse_float(get_text_by_tag_all(item_el, 'TLCKhau')) / 100
        ck = ck_dl if ck_dl > 0 else thanh_tien_truoc_ck * tl_ck
        thanh_tien_sau_ck = round(thanh_tien_truoc_ck - ck, 2)
        tong_chiet_khau += ck

        # Thuế
        thue_suat_text = get_text_by_tag_all(item_el, 'TSuat')
        thue_suat = parse_float(thue_suat_text) / 100 if thue_suat_text else 0.0
        tien_thue = round(thanh_tien_sau_ck * thue_suat, 2)
        thanh_toan = round(thanh_tien_sau_ck + tien_thue, 2)

        items.append({
            'stt': i,
            'ten_hang': ten_hang,
            'dvt': dvt,
            'so_luong': so_luong,
            'don_gia': don_gia,
            'thanh_tien_truoc_ck': thanh_tien_truoc_ck,
            'chiet_khau': ck,
            'thanh_tien_sau_ck': thanh_tien_sau_ck,
            'thue_suat': round(thue_suat * 100, 2),
            'tien_thue': tien_thue,
            'thanh_toan': thanh_toan,
        })

    # ------------------------------
    # TỔNG TIỀN TỪ XML
    # ------------------------------
    invoice['tong_chiet_khau'] = round(tong_chiet_khau, 2)

    # 1. Tổng tiền hàng (trước thuế)
    invoice['tong_tien_hang'] = parse_float(get_text_by_tag_all(root, 'TgTCThue'))

    # 2. Tổng tiền thuế
    invoice['tong_tien_thue'] = parse_float(get_text_by_tag_all(root, 'TgTThue'))

    # 3. Tổng thanh toán
    tong_tien_xml = parse_float(get_text_by_tag_all(root, 'TgTTTBSo'))
    invoice['tong_tien'] = tong_tien_xml if tong_tien_xml > 0 else round(sum(i['thanh_toan'] for i in items), 2)

    return invoice, items




@csrf_protect
def upload_invoice(request):
    invoice = None
    items = []
    file_name = None  # 🔹 Khởi tạo biến tránh lỗi UnboundLocalError

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            xml_file = form.cleaned_data['file']
            file_name = xml_file.name  # 🔹 Lấy tên file để hiển thị

            try:
                invoice, items = parse_invoice_xml(xml_file)
                messages.success(request, f"Đã đọc thành công file: {file_name}")
                print("Invoice:", invoice)
                print("Items:", items)

            except Exception as e:
                messages.error(request, f"Lỗi khi phân tích XML: {e}")

        else:
            messages.error(request, "Form không hợp lệ")
    else:
        form = UploadFileForm()

    # 🔹 Trả về template cùng dữ liệu
    return render(request, 'upload.html', {
        'form': form,
        'invoice': invoice,
        'items': items,
        'file_name': file_name,  # ✅ Truyền tên file sang template
    })

@csrf_protect
def save_invoice(request):
    if request.method == 'POST':
        import json
        try:
            invoice_data = json.loads(request.POST.get('invoice_data'))
            items_data = json.loads(request.POST.get('items_data'))
            file_name = request.POST.get('file_name', None)

            # ✅ Kiểm tra trùng hóa đơn
            existing_invoice = Invoice.objects.filter(
                so_hoa_don=invoice_data.get('so_hoa_don', ''),
                ky_hieu=invoice_data.get('ky_hieu', ''),
                mau_so=invoice_data.get('mau_so', ''),
                ma_so_thue=invoice_data.get('ma_so_thue', '')
            ).first()

            if existing_invoice:
                messages.warning(request, "❗ Hóa đơn đã tồn tại, không lưu lại.")
                return redirect('invoice_list')

            # ✅ Xử lý ngày hóa đơn
            ngay_hd_str = invoice_data.get('ngay_hd', '').strip()
            ngay_hd = None
            if ngay_hd_str:
                ngay_hd = parse_date(ngay_hd_str)
                if not ngay_hd:
                    try:
                        ngay_hd = datetime.strptime(ngay_hd_str, '%d/%m/%Y').date()
                    except ValueError:
                        ngay_hd = None

            # ✅ Lưu hóa đơn mới
            invoice = Invoice.objects.create(
                so_hoa_don=invoice_data.get('so_hoa_don', ''),
                ngay_hd=invoice_data.get('ngay_hd', ''),
                hinh_thuc_tt=invoice_data.get('hinh_thuc_tt', ''),
                mau_so=invoice_data.get('mau_so', ''),
                ky_hieu=invoice_data.get('ky_hieu', ''),
                ten_dv_ban=invoice_data.get('ten_dv_ban', ''),
                ma_so_thue=invoice_data.get('ma_so_thue', ''),
                dia_chi=invoice_data.get('dia_chi', ''),
                ten_nguoi_mua=invoice_data.get('ten_nguoi_mua', ''),
                ma_so_thue_mua=invoice_data.get('ma_so_thue_mua', ''),
                dia_chi_mua=invoice_data.get('dia_chi_mua', ''),
                so_tk=invoice_data.get('so_tk', ''),
                ten_ngan_hang=invoice_data.get('ten_ngan_hang', ''),
                tong_tien=invoice_data.get('tong_tien', 0),
                file_name=file_name,
            )

            # ✅ Tự động lưu danh mục nhà cung cấp
            supplier, created = Supplier.objects.get_or_create(
                ma_so_thue=invoice.ma_so_thue,
                defaults={
                    'ten_dv_ban': invoice.ten_dv_ban,
                    'dia_chi': invoice.dia_chi
                }
            )
            if not created:
                changed = False
                if supplier.ten_dv_ban != invoice.ten_dv_ban:
                    supplier.ten_dv_ban = invoice.ten_dv_ban
                    changed = True
                if supplier.dia_chi != invoice.dia_chi:
                    supplier.dia_chi = invoice.dia_chi
                    changed = True
                if changed:
                    supplier.save()

            # ✅ Lưu các dòng hàng hóa (items)
            for item in items_data:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    supplier=supplier,

                    ten_hang=item.get("ten_hang", ""),
                    dvt=item.get("dvt", ""),
                    so_luong=item.get("so_luong", 0),
                    don_gia=item.get("don_gia", 0),

                    # XML trả về thanh_tien_truoc_ck → gán vào model.thanh_tien
                    thanh_tien=item.get("thanh_tien_truoc_ck", 0),

                    chiet_khau=item.get("chiet_khau", 0),

                    # XML trả về tổng sau CK
                    thanh_toan=item.get("thanh_toan", 0),

                    tien_thue=item.get("tien_thue", 0),
                    thue_suat=item.get("thue_suat", 0),

                )

            # ------------------------------
            # 🔥 CẬP NHẬT TỔNG TIỀN HÓA ĐƠN
            # ------------------------------
            from decimal import Decimal

            invoice.tong_tien = sum(
                Decimal(it.thanh_toan or 0)
                for it in invoice.items.all()
            )
            invoice.save()

            messages.success(request, "✅ Lưu hóa đơn và nhà cung cấp thành công!")
            return redirect('invoice_list')

        except Exception as e:
            import traceback
            print(traceback.format_exc())  # 👀 giúp debug khi lỗi
            messages.error(request, f"❌ Lỗi khi lưu hóa đơn: {e}")

    return redirect('upload_invoice')



# Hàm bỏ dấu
def remove_accents(text):
    if not text:
        return ''
    return ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')
from django.db.models import F, Q, Case, When, FloatField, Sum
from decimal import Decimal
from django.core.paginator import Paginator
from django.shortcuts import render
def invoice_list(request):
    # Lấy tất cả hóa đơn, loại bỏ MST 0314858906
    invoices = Invoice.objects.exclude(ma_so_thue='0314858906').order_by('-ngay_hd')

    # --- Lọc theo GET params ---
    search = request.GET.get('search', '')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    per_page = request.GET.get('per_page', '10')

    if start_date:
        invoices = invoices.filter(ngay_hd__gte=start_date)
    if end_date:
        invoices = invoices.filter(ngay_hd__lte=end_date)

    data_list = []

    for inv in invoices:
        items = inv.items.all()  # đã parse từ XML

        # Tổng hợp số tiền từ XML
        inv.tong_tien_hang = sum(item.thanh_tien for item in items)
        inv.tong_chiet_khau = sum(item.chiet_khau for item in items)
        inv.tien_thue_gtgt = sum(item.tien_thue for item in items)
        inv.tong_thanh_toan = sum(item.thanh_toan for item in items)


        data_list.append(inv)

    # --- Tìm kiếm không phân biệt chữ hoa/thường + bỏ dấu ---
    if search:
        search_norm = remove_accents(search).lower()
        filtered_list = []
        for inv in data_list:
            haystack_fields = [
                remove_accents(inv.ten_dv_ban),
                remove_accents(inv.ma_so_thue),
                remove_accents(inv.so_hoa_don),
            ]
            items_text = ' '.join(remove_accents(item.ten_hang) for item in inv.items.all())
            haystack_fields.append(items_text)

            if any(search_norm in f.lower() for f in haystack_fields):
                filtered_list.append(inv)
        data_list = filtered_list

    # --- Phân trang ---
    if per_page.lower() == 'all':
        paginator = Paginator(data_list, len(data_list) or 1)
        paginated_invoices = paginator.get_page(1)
    else:
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10
        paginator = Paginator(data_list, per_page)
        page_number = request.GET.get('page')
        paginated_invoices = paginator.get_page(page_number)

    context = {
        'invoices': paginated_invoices,
    }
    return render(request, 'invoice_list.html', context)





# views.py
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from django.views.decorators.http import require_POST

@require_POST
def delete_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    invoice.delete()
    messages.success(request, "Đã xoá hóa đơn thành công.")
    return redirect('invoice_list')


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
@require_POST
def delete_selected_invoices(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        ids = data.get("ids", [])
        if not ids:
            return JsonResponse({"error": "No IDs provided."}, status=400)

        deleted_count, _ = Invoice.objects.filter(id__in=ids).delete()
        return JsonResponse({"success": True, "deleted_count": deleted_count})
    except Exception as e:
        print("Error deleting invoices:", e)
        return JsonResponse({"error": str(e)}, status=500)
