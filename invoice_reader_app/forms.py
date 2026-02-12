# invoices/forms.py
from django import forms

class UploadFileForm(forms.Form):
    file = forms.FileField()


# forms.py
from django import forms
from invoice_reader_app.model_invoice import Supplier, Customer, Invoice, InvoiceItem


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['ten_dv_ban', 'ma_so_thue', 'dia_chi', 'phan_loai']

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['ten_khach_hang', 'ma_so_thue', 'dia_chi', 'phan_loai']

from django import forms
from invoice_reader_app.model_invoice import InvoiceItem


from django import forms


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'so_hoa_don',
            'ngay_hd',
            'hinh_thuc_tt',
            'ten_nguoi_mua',
            'ma_so_thue_mua',
            'dia_chi_mua',
        ]
        widgets = {
            'ngay_hd': forms.TextInput(attrs={'type': 'date', 'class': 'form-control'}),
            'ten_nguoi_mua': forms.TextInput(attrs={'class': 'form-control'}),
            'ma_so_thue_mua': forms.TextInput(attrs={'class': 'form-control'}),
            'hinh_thuc_tt': forms.TextInput(attrs={'class': 'form-control'}),
            # 👇 Thêm widget Textarea cho địa chỉ
            'dia_chi_mua': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Nhập địa chỉ đầy đủ...',
                'style': 'resize: vertical;'
            }),
        }
        
class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = [
            'ten_hang',        # Tên hàng hóa
            'ten_goi_chung',   # Tên gọi chung
            'dvt',             # Đơn vị tính
            'so_luong',        # Số lượng
            'don_gia',         # Đơn giá
            'thanh_tien',      # Thành tiền
            'thue_suat',       # Thuế suất
            'tien_thue',       # Tiền thuế
            'sku',             # Mã SKU
        ]
        widgets = {
            'ten_hang': forms.TextInput(attrs={'class': 'form-control'}),
            'ten_goi_chung': forms.TextInput(attrs={'class': 'form-control'}),
            'dvt': forms.TextInput(attrs={'class': 'form-control'}),
            'so_luong': forms.NumberInput(attrs={'class': 'form-control'}),
            'don_gia': forms.NumberInput(attrs={'class': 'form-control'}),
            'thanh_tien': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'thue_suat': forms.NumberInput(attrs={'class': 'form-control'}),
            'tien_thue': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
        }

        
from invoice_reader_app.model_invoice import ProductName
class ProductForm(forms.ModelForm):
    class Meta:
        model = ProductName
        fields = ['sku', 'ten_hang', 'ten_goi_chung']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SKU'}),
            'ten_hang': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên hàng'}),
            'ten_goi_chung': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên gọi chung'}),        
        }



from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(
        label="Tên đăng nhập",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )


# inventory/forms.py

from django import forms

class UploadExcelForm(forms.Form):
    file = forms.FileField(label="Chọn file Excel (.xlsx)")
