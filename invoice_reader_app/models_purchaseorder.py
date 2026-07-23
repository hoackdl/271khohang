from django.db import models

from invoice_reader_app.model_invoice import Customer,Supplier,Invoice
from decimal import Decimal
from decimal import Decimal, InvalidOperation
from django.db import models
from django.utils import timezone
from django.db.models import Sum
from .models_fiscalyear import FiscalYear  # hoặc file chứa FiscalYear



class PurchaseOrder(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)

    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)

    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders')

    po_number = models.CharField(max_length=50, unique=True)
   

    is_export = models.BooleanField(default=False)  # PX = True, PN = False
    

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)        
    fiscal_year = models.IntegerField(        null=True,        blank=True,        db_index=True    )

    PHAN_LOAI_CHOICES = [
        ('HH', 'Hàng hóa'),
        ('PN', 'Phiếu nhập'),
        ('PX', 'Phiếu xuất'),    # <-- THÊM DÒNG NÀY
        ('KH', 'Khác'),
    ]
    phan_loai_phieu = models.CharField(
        max_length=2,
        choices=PHAN_LOAI_CHOICES,
        default='HH',
        verbose_name='Phân loại phiếu'
    )
    def __str__(self):
        return self.po_number
    

    @property
    def bank_payments(self):
        """
        Lấy tất cả phiếu NH liên quan tới PO này
        """
        return self.bankpayment_set.filter(
            credit__gt=0,
            doc_no__startswith="NH"
        )

    @property
    def total_nh(self):
        from django.db.models import Sum

        return (
            self.allocations.aggregate(
                total=Sum("allocated_amount")
            )["total"] or 0
        )

    @property
    def remaining_amount(self):
        """
        Còn phải thu
        """
        return self.total_payment - self.total_nh

    @property
    def payment_status(self):
        """
        Trạng thái thanh toán
        """
        if self.total_nh == 0:
            return "unpaid"
        elif self.total_nh < self.total_payment:
            return "partial"
        else:
            return "paid"

    @property
    def total_payment(self):
        items = self.items.all()  # assuming related_name='items'
        total_amount = sum(getattr(item, 'total_price', 0) for item in items)
        total_tax = sum(getattr(item, 'tien_thue', 0) for item in items)
        return total_amount + total_tax

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
    product_name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    so_luong_quy_doi = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=50, blank=True, null=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    thue_suat_field = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tien_thue_field = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sku = models.CharField(max_length=100, blank=True, null=True)
    ten_goi_chung = models.CharField(max_length=200, blank=True, null=True)
    is_export = models.BooleanField(default=False)
        # Thêm các trường chiết khấu nếu muốn
    chiet_khau = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    thanh_tien_sau_ck = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    thanh_toan_field = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    thanh_tien = models.DecimalField(max_digits=18, decimal_places=2, default=0)  # <-- thêm field này




    def save(self, *args, **kwargs):
        try:
            quantity = Decimal(self.quantity or 0)
        except (InvalidOperation, TypeError):
            quantity = Decimal('0')

        try:
            unit_price = Decimal(self.unit_price or 0)
        except (InvalidOperation, TypeError):
            unit_price = Decimal('0')

        self.total_price = quantity * unit_price

        try:
            thue_suat = Decimal(self.thue_suat_field or 0)
        except (InvalidOperation, TypeError):
            thue_suat = Decimal('0')

        self.tien_thue_field = self.total_price * thue_suat / Decimal('100')

        super().save(*args, **kwargs)




    def __str__(self):
        return self.product_name


    # Thuộc tính chỉ để hiển thị, không tính lại
    @property
    def thue_suat(self):
        return self.thue_suat_field

    @property
    def tien_thue(self):
        return self.tien_thue_field

    @property
    def total_price_calc(self):
        return self.total_price

    # ✅ Đổi tên property để không ghi đè field thật
    @property
    def sku_auto(self):
        if self.sku:
            return self.sku
        from invoice_reader_app.model_invoice import ProductName  # ✅ import local
        product = ProductName.objects.filter(ten_hang__iexact=self.product_name).first()
        return product.sku if product else ""

    @property
    def ten_goi_chung_auto(self):
        if self.ten_goi_chung:
            return self.ten_goi_chung
        from invoice_reader_app.model_invoice import ProductName  # ✅ import local
        product = ProductName.objects.filter(ten_hang__iexact=self.product_name).first()
        return product.ten_goi_chung if product else ""




# models_purcharoder.py
from django.db import models

class BankPayment(models.Model):
    purchase_orders = models.ManyToManyField(
        'PurchaseOrder',
        blank=True,
        related_name='bank_payments'
    )
    amount = models.DecimalField(max_digits=20, decimal_places=0, default=0)  # tổng số tiền (hoặc credit)
    debit = models.DecimalField(max_digits=20, decimal_places=0, default=0)
    credit = models.DecimalField(max_digits=20, decimal_places=0, default=0)
    balance = models.DecimalField(max_digits=20, decimal_places=0, default=0)
    customer = models.ForeignKey(        Customer,        null=True,        blank=True,        on_delete=models.SET_NULL    )
    interest_amount = models.DecimalField(        max_digits=18,        decimal_places=0,        default=0    )
    source_payment = models.ForeignKey(        "self",        null=True,        blank=True,        on_delete=models.CASCADE,        related_name="summary_records"    )
    cash_deposit = models.DecimalField(        max_digits=18,        decimal_places=0,        default=0    )
        
    doc_no = models.CharField(max_length=255, blank=True)
    stt = models.CharField(max_length=50, blank=True, null=True)
    logic_version = models.PositiveSmallIntegerField(        default=1    )
    content = models.TextField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    is_summary = models.BooleanField(default=False)  # True = phiếu tổng hợp, False = phiếu gốc
    bank_doc_no = models.CharField(max_length=255, blank=True)
    related_payment = models.ForeignKey("self",null=True,blank=True,on_delete=models.SET_NULL,related_name="summaries")
    parent_payment = models.ForeignKey(        "self",        null=True,        blank=True,        related_name="summary_children",        on_delete=models.SET_NULL
                                       
                                           )
    @property
    def nh_doc_no(self):
        """
        Trả về doc_no chuẩn NHyyyymmdd-xxx.
        Nếu đã có doc_no dạng NH thì giữ nguyên, 
        nếu là OB hoặc Excel import thì tạo mới tạm.
        """
        if self.doc_no.startswith("NH"):
            return self.doc_no
        elif self.doc_no == "OB":
            return self.doc_no
        else:
            # tạo doc_no tạm để hiển thị, không lưu DB
            date_str = self.payment_date.strftime("%y%m%d")
            return f"NH{date_str}-000"

class BankPaymentAllocation(models.Model):
    payment = models.ForeignKey(        BankPayment,        on_delete=models.CASCADE,        related_name="allocations"    )

    purchase_order = models.ForeignKey(        PurchaseOrder,        on_delete=models.CASCADE,        related_name="allocations"    )

    allocated_amount = models.DecimalField(        max_digits=20,        decimal_places=0,        default=0    )

    # Logic nào tạo ra dòng phân bổ này
    logic_version = models.PositiveSmallIntegerField(        default=1    )
    created_at = models.DateTimeField(        auto_now_add=True    )
    
    class Meta:
        unique_together = ("payment", "purchase_order")

    def __str__(self):
        return f"{self.payment.doc_no} - {self.purchase_order.po_number}"

class CashReceipt(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)
    receipt_no = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    
    def __str__(self):
        return self.receipt_no or "Phiếu thu"