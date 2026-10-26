
from django.core.management.base import BaseCommand
from django.db import transaction

from invoice_reader_app.model_invoice import ProductName, ProductGroup
from invoice_reader_app.models_activitytype import ActivityType

from django.core.management.base import BaseCommand
from django.db import transaction

from invoice_reader_app.model_invoice import (
    ProductName,
    ProductGroup,
)
from invoice_reader_app.models_activitytype import ActivityType


class Command(BaseCommand):
    help = (
        "Gán nhóm hàng 271LTT và loại hình CH271LTT "
        "cho toàn bộ ProductName"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Chỉ kiểm tra và hiển thị kết quả, "
                "không cập nhật database."
            ),
        )

    def handle(self, *args, **options):

        dry_run = options["dry_run"]

        # ==========================================
        # 1. Lấy nhóm hàng
        # ==========================================
        try:
            group = ProductGroup.objects.get(
                code="271LTT",
                is_active=True
            )
        except ProductGroup.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "Không tìm thấy nhóm hàng:"
                )
            )

            self.stdout.write(
                "code = 271LTT"
            )

            return

        # ==========================================
        # 2. Lấy loại hình hoạt động
        # ==========================================
        try:
            activity = ActivityType.objects.get(
                code="CH271LTT",
                is_active=True
            )
        except ActivityType.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "Không tìm thấy loại hình hoạt động:"
                )
            )

            self.stdout.write(
                "code = CH271LTT"
            )

            return

        # ==========================================
        # 3. Tổng số sản phẩm
        # ==========================================
        total = ProductName.objects.count()

        # ==========================================
        # 4. Số sản phẩm sẽ thay đổi
        # ==========================================
        queryset = ProductName.objects.exclude(
            nhom_hang=group,
            activity_type=activity,
        )

        will_update = queryset.count()

        # ==========================================
        # 5. Hiển thị thông tin
        # ==========================================
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "=== THÔNG TIN CẬP NHẬT ==="
            )
        )

        self.stdout.write(
            f"Nhóm hàng:"
        )

        self.stdout.write(
            f"  ID   : {group.id}"
        )

        self.stdout.write(
            f"  Code : {group.code}"
        )

        self.stdout.write(
            f"  Name : {group.name}"
        )

        self.stdout.write("")

        self.stdout.write(
            f"Loại hình hoạt động:"
        )

        self.stdout.write(
            f"  ID   : {activity.id}"
        )

        self.stdout.write(
            f"  Code : {activity.code}"
        )

        self.stdout.write(
            f"  Name : {activity.name}"
        )

        self.stdout.write("")

        self.stdout.write(
            f"Tổng sản phẩm     : {total}"
        )

        self.stdout.write(
            f"Sẽ được cập nhật  : {will_update}"
        )

        # ==========================================
        # 6. Dry run
        # ==========================================
        if dry_run:

            self.stdout.write("")

            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN: Không có dữ liệu nào được cập nhật."
                )
            )

            return

        # ==========================================
        # 7. Cập nhật database
        # ==========================================
        with transaction.atomic():

            updated = queryset.update(
                nhom_hang=group,
                activity_type=activity,
            )

        # ==========================================
        # 8. Kết quả
        # ==========================================
        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "=== HOÀN TẤT ==="
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Đã cập nhật: {updated} sản phẩm"
            )
        )


# python manage.py init_product_groups --dry-run

# python manage.py init_product_groups