from django.db import models


# =========================================================
# NHÂN SỰ
# =========================================================

class Employee(models.Model):

    STATUS_CHOICES = [
        ("active", "Đang làm việc"),
        ("inactive", "Tạm nghỉ"),
        ("resigned", "Đã nghỉ việc"),
    ]

    employee_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Mã nhân viên"
    )

    full_name = models.CharField(
        max_length=255,
        verbose_name="Họ và tên"
    )

    gender = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Giới tính"
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name="Ngày sinh"
    )

    citizen_id = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="CCCD"
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Điện thoại"
    )

    email = models.EmailField(
        blank=True,
        verbose_name="Email"
    )

    address = models.TextField(
        blank=True,
        verbose_name="Địa chỉ"
    )

    department = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Phòng ban"
    )

    position = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Chức vụ"
    )

    join_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Ngày vào làm"
    )

    salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Mức lương"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        verbose_name="Trạng thái"
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Ghi chú"
    )

    created_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "employees"
        ordering = ["employee_code"]
        verbose_name = "Nhân sự"
        verbose_name_plural = "Nhân sự"

    def __str__(self):
        return f"{self.employee_code} - {self.full_name}"


# =========================================================
# BHXH / BHYT / BHTN
# =========================================================

class SocialInsurance(models.Model):

    STATUS_CHOICES = [
        ("active", "Đang tham gia"),
        ("suspended", "Tạm dừng"),
        ("stopped", "Đã dừng"),
    ]

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name="social_insurance",
        verbose_name="Nhân sự"
    )

    social_insurance_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Mã số BHXH"
    )

    social_insurance_book = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Số sổ BHXH"
    )

    health_insurance_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Số thẻ BHYT"
    )

    health_insurance_hospital = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nơi KCB ban đầu"
    )

    insurance_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Ngày tham gia BHXH"
    )

    health_insurance_start = models.DateField(
        null=True,
        blank=True,
        verbose_name="BHYT từ ngày"
    )

    health_insurance_expiry = models.DateField(
        null=True,
        blank=True,
        verbose_name="BHYT đến ngày"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        verbose_name="Trạng thái"
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Ghi chú"
    )

    created_at = models.DateTimeField(
            null=True,
            blank=True,
        )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "social_insurances"
        ordering = ["employee__employee_code"]
        verbose_name = "BHXH"
        verbose_name_plural = "BHXH"

    def __str__(self):
        return (
            f"{self.employee.employee_code} - "
            f"{self.employee.full_name}"
        )


# =========================================================
# LỊCH SỬ MỨC LƯƠNG ĐÓNG BH
# =========================================================

class InsuranceSalaryHistory(models.Model):

    social_insurance = models.ForeignKey(
        SocialInsurance,
        on_delete=models.CASCADE,
        related_name="salary_histories",
        verbose_name="Hồ sơ BHXH"
    )

    effective_from = models.DateField(
        null=True,
        blank=True,
    )

    effective_to = models.DateField(
        null=True,
        blank=True,
        verbose_name="Áp dụng đến ngày"
    )

    insurance_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Mức lương đóng BH"
    )

    position_allowance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Phụ cấp chức vụ"
    )

    other_allowance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Phụ cấp khác"
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Ghi chú"
    )

    created_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "insurance_salary_histories"

        ordering = [
            "-effective_from"
        ]

        verbose_name = "Lịch sử mức lương đóng BH"
        verbose_name_plural = "Lịch sử mức lương đóng BH"

    def __str__(self):
        return (
            f"{self.social_insurance.employee.employee_code} - "
            f"{self.effective_from:%d/%m/%Y} - "
            f"{self.insurance_salary:,.0f}"
        )

    @property
    def total_insurance_salary(self):
        return (
            (self.insurance_salary or 0)
            + (self.position_allowance or 0)
            + (self.other_allowance or 0)
        )


# =========================================================
# LỊCH SỬ TỶ LỆ ĐÓNG
# =========================================================

class InsuranceRateHistory(models.Model):

    social_insurance = models.ForeignKey(
        SocialInsurance,
        on_delete=models.CASCADE,
        related_name="rate_histories",
        verbose_name="Hồ sơ BHXH"
    )

    effective_from = models.DateField(
        null=True,
        blank=True,
    )

    effective_to = models.DateField(
        null=True,
        blank=True,
        verbose_name="Áp dụng đến ngày"
    )

    # -----------------------------------------------------
    # NLĐ
    # -----------------------------------------------------

    employee_social_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=8,
        verbose_name="NLĐ - BHXH (%)"
    )

    employee_health_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.5,
        verbose_name="NLĐ - BHYT (%)"
    )

    employee_unemployment_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1,
        verbose_name="NLĐ - BHTN (%)"
    )

    # -----------------------------------------------------
    # DOANH NGHIỆP
    # -----------------------------------------------------

    company_social_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=17.5,
        verbose_name="DN - BHXH (%)"
    )

    company_health_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=3,
        verbose_name="DN - BHYT (%)"
    )

    company_unemployment_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1,
        verbose_name="DN - BHTN (%)"
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Ghi chú"
    )

    created_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "insurance_rate_histories"

        ordering = [
            "-effective_from"
        ]

        verbose_name = "Lịch sử tỷ lệ đóng"
        verbose_name_plural = "Lịch sử tỷ lệ đóng"

    def __str__(self):
        return (
            f"{self.social_insurance.employee.employee_code} - "
            f"{self.effective_from:%d/%m/%Y}"
        )

    @property
    def employee_total_rate(self):

        return (
            self.employee_social_rate
            + self.employee_health_rate
            + self.employee_unemployment_rate
        )

    @property
    def company_total_rate(self):

        return (
            self.company_social_rate
            + self.company_health_rate
            + self.company_unemployment_rate
        )
