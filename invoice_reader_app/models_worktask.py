from django.conf import settings
from django.db import models


class WorkTask(models.Model):

    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Đang xử lý"),
        (STATUS_COMPLETED, "Hoàn thành"),
    ]

    # =====================================================
    # NGÀY
    # =====================================================

    work_date = models.DateField(
        verbose_name="Ngày"
    )

    # =====================================================
    # NỘI DUNG CÔNG VIỆC
    # =====================================================

    content = models.TextField(
        verbose_name="Nội dung công việc"
    )

    # =====================================================
    # NGƯỜI XỬ LÝ
    # =====================================================

    handler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_tasks",
        verbose_name="Người xử lý"
    )

    # =====================================================
    # NỘI DUNG XỬ LÝ
    # =====================================================

    process_content = models.TextField(
        verbose_name="Nội dung xử lý",
        blank=True,
        default=""
    )

    # =====================================================
    # TRẠNG THÁI
    # =====================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="Trạng thái"
    )

    # =====================================================
    # THỜI GIAN
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ngày cập nhật"
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ngày hoàn thành"
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:

        ordering = [
            "-work_date",
            "-id"
        ]

        verbose_name = "Công việc"

        verbose_name_plural = "Công việc"

        indexes = [
            models.Index(
                fields=["work_date"]
            ),
            models.Index(
                fields=["status"]
            ),
            models.Index(
                fields=["handler"]
            ),
        ]

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):

        return (
            f"{self.work_date:%d/%m/%Y} - "
            f"{self.content[:80]}"
        )

    # =====================================================
    # PROPERTY
    # =====================================================

    @property
    def is_completed(self):

        return self.status == self.STATUS_COMPLETED

    @property
    def status_display(self):

        return self.get_status_display()
