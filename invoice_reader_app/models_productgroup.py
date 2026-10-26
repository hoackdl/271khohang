from django.db import models
from invoice_reader_app.models_activitytype import ActivityType



class ProductGroup(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Mã nhóm hàng"
    )

    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Tên nhóm hàng"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Đang sử dụng"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
    activity_type = models.ForeignKey(        ActivityType,        on_delete=models.SET_NULL,        null=True,        blank=True,        related_name="product_groups",
        verbose_name="Loại hình hoạt động"
    )
    class Meta:
        ordering = ["name"]
        verbose_name = "Nhóm hàng"
        verbose_name_plural = "Nhóm hàng"

    def __str__(self):
        return f"{self.code} - {self.name}"