# invoices/models.py
from django.db import models
# invoices/models.py
from django.db.models import Sum
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
    ma_so_thue = models.CharField(max_length=20, blank=True, unique=True)
    dia_chi = models.CharField(max_length=255, blank=True)
    phan_loai = models.CharField(max_length=100, blank=True, null=True, default='')
    phai_thu_dau_ky = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    phai_tra_dau_ky = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    @property
    def invoices(self):
        return Invoice.objects.filter(ma_so_thue_mua=self.ma_so_thue)

    @property
    def total_invoice(self):
        return sum(inv.tong_tien or 0 for inv in self.invoices)

    @property
    def total_paid(self):
        return sum(inv.total_paid or 0 for inv in self.invoices)

    @property
    def percent_paid(self):
        if self.total_invoice == 0:
            return 0
        return round((self.total_paid / self.total_invoice) * 100, 2)





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
    fiscal_year = models.IntegerField(db_index=True)



    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
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
    tong_tien_hang = models.FloatField(default=0)
    tong_tien_thue = models.FloatField(default=0)
    tong_tien = models.DecimalField(max_digits=18, decimal_places=2)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    xml_uuid = models.CharField(
            max_length=50,
            null=True,
            blank=True,
            unique=True   # ✅ ĐÂY MỚI LÀ CHUẨN
        )


    LOAI_HD_CHOICES = (
        ('VAO', 'Hóa đơn vào'),
        ('XUAT', 'Hóa đơn xuất'),
    )
    loai_hd = models.CharField(max_length=10, choices=LOAI_HD_CHOICES, default='VAO')

    TRANG_THAI_CHOICES = (
        ("CHO_XUAT", "Chờ xuất hóa đơn"),
        ("DA_XUAT", "Đã xuất hóa đơn"),
    )

    trang_thai = models.CharField(
        max_length=20,
        choices=TRANG_THAI_CHOICES,
        default="CHO_XUAT"
    )

    class Meta:
        indexes = [
            models.Index(fields=["ma_so_thue", "ky_hieu", "so_hoa_don"]),
        ]

    # -------------------------
    # PROPERTY ĐÚNG CHÍNH XÁC
    # -------------------------



    from django.db.models import QuerySet
    
    def save(self, *args, **kwargs):
        if not self.fiscal_year:
            if self.ngay_hd:
                self.fiscal_year = self.ngay_hd.year
            else:
                raise ValueError("Hóa đơn phải có ngày hóa đơn")
        super().save(*args, **kwargs)

    @property
    def payments(self):
        from .models_purcharoder import BankPayment
        if not self.pk:
            return BankPayment.objects.none()

        pos = self.purchase_orders.all()
        return BankPayment.objects.filter(purchase_orders__in=pos).distinct()

    @property
    def total_debit(self):
        return self.payments.aggregate(total=Sum('debit'))['total'] or Decimal(0)

    @property
    def total_credit(self):
        return self.payments.aggregate(total=Sum('credit'))['total'] or Decimal(0)

    @property
    def total_paid(self):     # alias
        return self.total_credit

    @property
    def remaining(self):
        if not self.pk:
            return Decimal(0)

        tong = Decimal(self.tong_tien or 0)
        
        payments = self.payments
        total_debit = Decimal(0)
        total_credit = Decimal(0)

        for p in payments:
            pos = p.purchase_orders.all()
            # Lấy Invoice liên quan đến PO này
            related_invoices = Invoice.objects.filter(purchase_orders__in=pos).distinct()

            total_payment_invoices = sum(Decimal(inv.tong_tien or 0) for inv in related_invoices)
            if total_payment_invoices == 0:
                continue

            ratio = Decimal(self.tong_tien or 0) / Decimal(total_payment_invoices)

            total_debit += Decimal(p.debit or 0) * ratio
            total_credit += Decimal(p.credit or 0) * ratio

        if total_debit > 0 and total_credit == 0:
            return tong - total_debit
        if total_credit > 0 and total_debit == 0:
            return tong + total_credit

        return tong - total_debit + total_credit

    # invoices/models.py
    @property
    def customer_obj(self):
        if not self.pk:
            return None   # ⛔ TUYỆT ĐỐI không tạo quan hệ khi chưa save

        if self.ma_so_thue_mua:
            customer, _ = Customer.objects.get_or_create(
                ma_so_thue=self.ma_so_thue_mua,
                defaults={
                    'ten_khach_hang': self.ten_nguoi_mua or "Khách hàng",
                    'dia_chi': self.dia_chi_mua or ""
                }
            )
            return customer
        else:
            placeholder_mst = f"TEMP-{self.id}"
            customer, _ = Customer.objects.get_or_create(
                ma_so_thue=placeholder_mst,
                defaults={
                    'ten_khach_hang': "Khách lẻ",
                    'dia_chi': self.dia_chi_mua or ""
                }
            )
            return customer



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
        lookup_name = self.ten_hang or self.ten_goi_chung
        product = ProductName.objects.filter(ten_hang__iexact=lookup_name).first()
        if product:
            if not self.sku:
                self.sku = product.sku
            if not self.ten_goi_chung:
                self.ten_goi_chung = product.ten_goi_chung
            if not self.nhom_hang:
                self.nhom_hang = product.nhom_hang

        # ⛔ KHÔNG TÍNH LẠI NẾU ĐÃ CÓ GIÁ TRỊ TỪ XML
        if (self.so_luong > 0 or self.don_gia > 0) and self.thanh_tien == 0:
            self.thanh_tien = Decimal(self.so_luong) * Decimal(self.don_gia)

        if self.tien_thue == 0:
            self.tien_thue = Decimal(self.thanh_tien) * Decimal(self.thue_suat) / Decimal(100)

        super().save(*args, **kwargs)



 