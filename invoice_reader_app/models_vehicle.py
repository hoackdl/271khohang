from django.db import models

class Vehicle(models.Model):

    STATUS_CHOICES = [
        ("active", "Đang sử dụng"),
        ("inactive", "Ngừng sử dụng"),
        ("repair", "Đang sửa chữa"),
        ("liquidated", "Đã thanh lý"),
    ]

    # =====================================================
    # THÔNG TIN NHẬN DẠNG
    # =====================================================

    license_plate = models.CharField(
        "Biển số xe",
        max_length=30,
        unique=True,
    )

    vehicle_record_no = models.CharField(
        "Số quản lý",
        max_length=100,
        blank=True,
        default="",
    )

    vehicle_type = models.CharField(
        "Loại phương tiện",
        max_length=255,
        blank=True,
        default="",
    )

    brand = models.CharField(
        "Nhãn hiệu / tên thương mại",
        max_length=255,
        blank=True,
        default="",
    )

    model = models.CharField(
        "Mã kiểu loại",
        max_length=100,
        blank=True,
        default="",
    )

    color = models.CharField(
        "Màu sơn",
        max_length=100,
        blank=True,
        default="",
    )

    # =====================================================
    # SỐ NHẬN DẠNG XE
    # =====================================================

    chassis_number = models.CharField(
        "Số khung",
        max_length=100,
        blank=True,
        default="",
    )

    engine_number = models.CharField(
        "Số động cơ",
        max_length=100,
        blank=True,
        default="",
    )

    engine_model = models.CharField(
        "Ký hiệu động cơ",
        max_length=100,
        blank=True,
        default="",
    )

    # =====================================================
    # SẢN XUẤT
    # =====================================================

    manufacture_year = models.PositiveIntegerField(
        "Năm sản xuất",
        null=True,
        blank=True,
    )

    production_country = models.CharField(
        "Nước sản xuất",
        max_length=100,
        blank=True,
        default="",
    )

    lifetime_limit = models.PositiveIntegerField(
        "Niên hạn sử dụng",
        null=True,
        blank=True,
    )

    # =====================================================
    # KINH DOANH / CẢI TẠO
    # =====================================================

    commercial_use = models.BooleanField(
        "Có kinh doanh vận tải",
        default=False,
    )

    modified_vehicle = models.BooleanField(
        "Có cải tạo",
        default=False,
    )

    # =====================================================
    # KÍCH THƯỚC
    # =====================================================

    overall_dimensions = models.CharField(
        "Kích thước bao",
        max_length=255,
        blank=True,
        default="",
    )

    wheelbase = models.CharField(
        "Khoảng cách trục",
        max_length=100,
        blank=True,
        default="",
    )

    cargo_dimensions = models.CharField(
        "Kích thước lòng / bao thùng xe",
        max_length=255,
        blank=True,
        default="",
    )

    # =====================================================
    # KHỐI LƯỢNG
    # =====================================================

    curb_weight = models.DecimalField(
        "Khối lượng bản thân",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    total_weight_design = models.DecimalField(
        "Khối lượng toàn bộ theo thiết kế",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    total_weight_authorized = models.DecimalField(
        "Khối lượng toàn bộ cho phép",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    load_capacity_design = models.DecimalField(
        "Khối lượng hàng theo thiết kế",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    load_capacity_authorized = models.DecimalField(
        "Khối lượng hàng cho phép",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    towing_capacity_design = models.DecimalField(
        "Khối lượng kéo theo thiết kế",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    towing_capacity_authorized = models.DecimalField(
        "Khối lượng kéo theo cho phép",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Giữ lại trường cũ để tương thích code hiện tại
    load_capacity = models.DecimalField(
        "Tải trọng",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    total_weight = models.DecimalField(
        "Trọng lượng toàn bộ",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # =====================================================
    # SỐ NGƯỜI
    # =====================================================

    passenger_capacity = models.PositiveIntegerField(
        "Số người được phép chở",
        null=True,
        blank=True,
    )

    standing_capacity = models.PositiveIntegerField(
        "Số chỗ đứng",
        null=True,
        blank=True,
    )

    lying_capacity = models.PositiveIntegerField(
        "Số chỗ nằm",
        null=True,
        blank=True,
    )

    wheelchair_capacity = models.PositiveIntegerField(
        "Số xe lăn",
        null=True,
        blank=True,
    )

    # =====================================================
    # HỆ THỐNG BÁNH XE
    # =====================================================

    drive_configuration = models.CharField(
        "Công thức bánh xe",
        max_length=100,
        blank=True,
        default="",
    )

    tire_tread = models.CharField(
        "Vết bánh xe",
        max_length=100,
        blank=True,
        default="",
    )

    tire_specification = models.TextField(
        "Số lượng / cỡ lốp / trục",
        blank=True,
        default="",
    )

    # =====================================================
    # ĐỘNG CƠ
    # =====================================================

    engine_type = models.CharField(
        "Loại động cơ đốt trong",
        max_length=255,
        blank=True,
        default="",
    )

    engine_displacement = models.DecimalField(
        "Thể tích làm việc",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    fuel_type = models.CharField(
        "Loại nhiên liệu",
        max_length=100,
        blank=True,
        default="",
    )

    emission_level = models.CharField(
        "Mức khí thải",
        max_length=100,
        blank=True,
        default="",
    )

    max_power = models.DecimalField(
        "Công suất lớn nhất",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    max_power_rpm = models.PositiveIntegerField(
        "Tốc độ quay công suất lớn nhất",
        null=True,
        blank=True,
    )

    # =====================================================
    # THIẾT BỊ ĐẶC TRƯNG
    # =====================================================

    has_tachograph = models.BooleanField(
        "Có thiết bị giám sát hành trình",
        default=False,
    )

    has_passenger_camera = models.BooleanField(
        "Có camera khoang chở khách",
        default=False,
    )

    has_driver_camera = models.BooleanField(
        "Có camera người lái",
        default=False,
    )

    has_child_detection = models.BooleanField(
        "Có thiết bị cảnh báo trẻ em",
        default=False,
    )

    carries_explosives = models.BooleanField(
        "Vận chuyển vật liệu nổ",
        default=False,
    )

    # =====================================================
    # ĐĂNG KIỂM
    # =====================================================

    inspection_number = models.CharField(
        "Số giấy / số đăng kiểm",
        max_length=100,
        blank=True,
        default="",
    )

    inspection_date = models.DateField(
        "Ngày đăng kiểm",
        null=True,
        blank=True,
    )

    inspection_expiry = models.DateField(
        "Đăng kiểm có hiệu lực đến",
        null=True,
        blank=True,
    )

    inspection_sticker_number = models.CharField(
        "Số seri tem kiểm định",
        max_length=100,
        blank=True,
        default="",
    )

    inspection_stamp_issued = models.BooleanField(
        "Được cấp tem kiểm định",
        default=True,
    )

    exempt_initial_inspection = models.BooleanField(
        "Miễn kiểm định lần đầu",
        default=False,
    )

    inspection_station = models.CharField(
        "Cơ sở đăng kiểm",
        max_length=255,
        blank=True,
        default="",
    )

    inspection_signer = models.CharField(
        "Người ký chứng nhận",
        max_length=255,
        blank=True,
        default="",
    )

    inspection_verification_url = models.URLField(
        "Website tra cứu đăng kiểm",
        max_length=500,
        blank=True,
        default="",
    )

    inspection_qr_code = models.TextField(
        "QR tra cứu chứng nhận",
        blank=True,
        default="",
    )

    # =====================================================
    # PHÙ HIỆU
    # =====================================================

    badge_number = models.CharField(
        "Số phù hiệu",
        max_length=100,
        blank=True,
        default="",
    )

    badge_expiry = models.DateField(
        "Phù hiệu có hiệu lực đến",
        null=True,
        blank=True,
    )

    # =====================================================
    # QUẢN LÝ NỘI BỘ
    # =====================================================

    put_into_use_date = models.DateField(
        "Ngày đưa vào sử dụng",
        null=True,
        blank=True,
    )

    status = models.CharField(
        "Trạng thái",
        max_length=30,
        choices=STATUS_CHOICES,
        default="active",
    )

    notes = models.TextField(
        "Ghi chú",
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "vehicles"
        verbose_name = "Phương tiện"
        verbose_name_plural = "Phương tiện"
        ordering = ["license_plate"]

    def __str__(self):
        return self.license_plate