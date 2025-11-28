# invoices/models.py
from django.db import models
# invoices/models.py

from decimal import Decimal


class Supplier(models.Model):
    ten_dv_ban = models.CharField(max_length=200)
    ma_so_thue = models.CharField(max_length=50, unique=True)
    dia_chi = models.TextField(blank=True)
    phan_loai = models.CharField(max_length=100, blank=True, null=True, default='')

    def __str__(self):
        return f"{self.ten_dv_ban} ({self.ma_so_thue})"

class Customer(models.Model):
    ten_khach_hang = models.CharField(max_length=255)
    ma_so_thue = models.CharField(max_length=20, blank=True)
    dia_chi = models.CharField(max_length=255, blank=True)
    phan_loai = models.CharField(max_length=100, blank=True, null=True, default='')

class ProductName(models.Model):
    NHOM_HANG_CHOICES = [
        ("son_nuoc", "Sơn nước"),
        ("son_dau", "Sơn dầu"),
        ("chat_mau", "Chất màu"),
        ("chong_tham", "Chống thấm"),
    ]
    sku = models.CharField(max_length=100, blank=True, null=True)  # ✅ thêm SKU
    ten_hang = models.CharField(max_length=255)
    ten_goi_chung = models.CharField(max_length=255, blank=True, null=True)
    ten_goi_xuat = models.CharField(max_length=255, blank=True, null=True)
    nhom_hang = models.CharField(
        max_length=30,
        choices=NHOM_HANG_CHOICES,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.ten_hang} ({self.sku})" if self.sku else self.ten_hang

class Invoice(models.Model):
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    so_hoa_don = models.CharField(max_length=50)
    ngay_hd = models.DateField(null=True)
    hinh_thuc_tt = models.CharField(max_length=100, blank=True)
    mau_so = models.CharField(max_length=50, blank=True)
    ky_hieu = models.CharField(max_length=50, blank=True)
    ten_dv_ban = models.CharField(max_length=200)
    ma_so_thue = models.CharField(max_length=50)
    dia_chi = models.TextField(blank=True)
    ten_nguoi_mua = models.CharField(max_length=200, blank=True)
    ma_so_thue_mua = models.CharField(max_length=50, blank=True)
    dia_chi_mua = models.TextField(blank=True)
    so_tk = models.CharField(max_length=100, blank=True)
    ten_ngan_hang = models.CharField(max_length=100, blank=True)
    tong_tien = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)

    LOAI_HD_CHOICES = (
        ('VAO', 'Hóa đơn vào'),
        ('XUAT', 'Hóa đơn xuất'),
    )
    loai_hd = models.CharField(max_length=10, choices=LOAI_HD_CHOICES, default='VAO')

    class Meta:
         unique_together = ("so_hoa_don", "ky_hieu", "ma_so_thue", "ngay_hd", "loai_hd")

class InvoiceItem(models.Model):
    NHOM_HANG_CHOICES = [
        ("son_nuoc", "Sơn nước"),
        ("son_dau", "Sơn dầu"),
        ("chat_mau", "Chất màu"),
        ("chong_tham", "Chống thấm"),
    ]
    invoice = models.ForeignKey(Invoice, related_name="items", on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    ten_hang = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, blank=True, null=True)  # ✅ lưu SKU tương ứng
    dvt = models.CharField(max_length=200)
    so_luong =models.DecimalField(max_digits=18, decimal_places=2, default=0)   # <-- thêm
    don_gia = models.DecimalField(max_digits=18, decimal_places=2, default=0)   # <-- thêm
    thanh_tien = models.DecimalField(max_digits=18, decimal_places=2, default=0)   # <-- thêm
    thue_suat = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tien_thue = models.DecimalField(max_digits=18, decimal_places=2, default=0)   # <-- thêm
    thanh_toan = models.DecimalField(max_digits=18, decimal_places=2, default=0)   # <-- thêm
    chiet_khau = models.DecimalField(max_digits=18, decimal_places=2, default=0)   # <-- thêm
    ten_goi_xuat = models.CharField(max_length=255, null=True, blank=True)
    ten_goi_chung = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=True)
    po_item_id = models.IntegerField(blank=True, null=True)
    nhom_hang = models.CharField(
        max_length=50,
        choices=NHOM_HANG_CHOICES,
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        # Lấy giá trị từ ProductName nếu chưa có
        lookup_name = self.ten_hang or self.ten_goi_chung
        product = ProductName.objects.filter(ten_hang__iexact=lookup_name).first()
        if product:
            if not self.sku:
                self.sku = product.sku
            if not self.ten_goi_chung:
                self.ten_goi_chung = product.ten_goi_chung
            if not self.nhom_hang:
                self.nhom_hang = product.nhom_hang  # <-- lấy nhóm hàng

        # Tính toán thanh_tien và tien_thue
        so_luong = Decimal(self.so_luong or 0)
        don_gia = Decimal(self.don_gia or 0)
        thue_suat = Decimal(self.thue_suat or 0)

        self.thanh_tien = so_luong * don_gia
        self.tien_thue = self.thanh_tien * thue_suat / Decimal(100)

        super().save(*args, **kwargs)