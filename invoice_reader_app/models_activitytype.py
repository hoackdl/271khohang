
from django.db import models
# invoices/models.py
from django.db.models import Sum
from decimal import Decimal






class ActivityType(models.Model):

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Mã hoạt động"
    )

    name = models.CharField(
        max_length=255,
        verbose_name="Tên hoạt động"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Đang sử dụng"
    )

    class Meta:
        db_table = "activity_types"
        verbose_name = "Loại hình hoạt động"
        verbose_name_plural = "Loại hình hoạt động"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"