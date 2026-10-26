from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from invoice_reader_app.models_social_insurance import Employee, SocialInsurance, InsuranceRateHistory


# =========================================================
# XEM BHXH CỦA NHÂN VIÊN
# =========================================================

@login_required
def social_insurance_employee(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )

    try:
        insurance = employee.social_insurance
    except SocialInsurance.DoesNotExist:
        insurance = None

    context = {
        "employee": employee,
        "insurance": insurance,
    }

    return render(
        request,
        "social_insurance/social_insurance_employee.html",
        context
    )


# =========================================================
# THÊM BHXH CHO NHÂN VIÊN
# =========================================================

@login_required
def social_insurance_create(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )

    # -----------------------------------------------------
    # MỖI NHÂN VIÊN CHỈ CÓ 1 HỒ SƠ BHXH
    # -----------------------------------------------------

    try:
        insurance = employee.social_insurance

        messages.warning(
            request,
            "Nhân viên này đã có hồ sơ BHXH."
        )

        return redirect(
            "social_insurance_employee",
            pk=employee.pk
        )

    except SocialInsurance.DoesNotExist:
        insurance = None

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        insurance = SocialInsurance(

            employee=employee,

            social_insurance_number=request.POST.get(
                "social_insurance_number",
                ""
            ).strip(),

            social_insurance_book=request.POST.get(
                "social_insurance_book",
                ""
            ).strip(),

            health_insurance_number=request.POST.get(
                "health_insurance_number",
                ""
            ).strip(),

            health_insurance_hospital=request.POST.get(
                "health_insurance_hospital",
                ""
            ).strip(),

            insurance_start_date=request.POST.get(
                "insurance_start_date"
            ) or None,

            health_insurance_start=request.POST.get(
                "health_insurance_start"
            ) or None,

            health_insurance_expiry=request.POST.get(
                "health_insurance_expiry"
            ) or None,

            insurance_salary=request.POST.get(
                "insurance_salary"
            ) or None,

            position_allowance=request.POST.get(
                "position_allowance"
            ) or 0,

            other_allowance=request.POST.get(
                "other_allowance"
            ) or 0,

            employee_social_rate=request.POST.get(
                "employee_social_rate"
            ) or 8,

            company_social_rate=request.POST.get(
                "company_social_rate"
            ) or 17.5,

            employee_health_rate=request.POST.get(
                "employee_health_rate"
            ) or 1.5,

            company_health_rate=request.POST.get(
                "company_health_rate"
            ) or 3,

            employee_unemployment_rate=request.POST.get(
                "employee_unemployment_rate"
            ) or 1,

            company_unemployment_rate=request.POST.get(
                "company_unemployment_rate"
            ) or 1,

            status=request.POST.get(
                "insurance_status",
                "active"
            ),

            notes=request.POST.get(
                "insurance_notes",
                ""
            ).strip(),
        )

        insurance.save()

        messages.success(
            request,
            f"Đã tạo hồ sơ BHXH cho {employee.full_name}."
        )

        return redirect(
            "social_insurance_employee",
            pk=employee.pk
        )

    # -----------------------------------------------------
    # FORM
    # -----------------------------------------------------

    context = {
        "employee": employee,
        "insurance": insurance,
    }

    return render(
        request,
        "social_insurance/social_insurance_form.html",
        context
    )


# =========================================================
# SỬA BHXH
# =========================================================

@login_required
def social_insurance_edit(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )

    insurance = get_object_or_404(
        SocialInsurance,
        employee=employee
    )

    if request.method == "POST":

        insurance.social_insurance_number = request.POST.get(
            "social_insurance_number",
            ""
        ).strip()

        insurance.social_insurance_book = request.POST.get(
            "social_insurance_book",
            ""
        ).strip()

        insurance.health_insurance_number = request.POST.get(
            "health_insurance_number",
            ""
        ).strip()

        insurance.health_insurance_hospital = request.POST.get(
            "health_insurance_hospital",
            ""
        ).strip()

        insurance.insurance_start_date = request.POST.get(
            "insurance_start_date"
        ) or None

        insurance.health_insurance_start = request.POST.get(
            "health_insurance_start"
        ) or None

        insurance.health_insurance_expiry = request.POST.get(
            "health_insurance_expiry"
        ) or None

        insurance.insurance_salary = request.POST.get(
            "insurance_salary"
        ) or None

        insurance.position_allowance = request.POST.get(
            "position_allowance"
        ) or 0

        insurance.other_allowance = request.POST.get(
            "other_allowance"
        ) or 0

        insurance.employee_social_rate = request.POST.get(
            "employee_social_rate"
        ) or 8

        insurance.company_social_rate = request.POST.get(
            "company_social_rate"
        ) or 17.5

        insurance.employee_health_rate = request.POST.get(
            "employee_health_rate"
        ) or 1.5

        insurance.company_health_rate = request.POST.get(
            "company_health_rate"
        ) or 3

        insurance.employee_unemployment_rate = request.POST.get(
            "employee_unemployment_rate"
        ) or 1

        insurance.company_unemployment_rate = request.POST.get(
            "company_unemployment_rate"
        ) or 1

        insurance.status = request.POST.get(
            "insurance_status",
            "active"
        )

        insurance.notes = request.POST.get(
            "insurance_notes",
            ""
        ).strip()

        insurance.save()

        messages.success(
            request,
            f"Đã cập nhật hồ sơ BHXH của {employee.full_name}."
        )

        return redirect(
            "social_insurance_employee",
            pk=employee.pk
        )

    context = {
        "employee": employee,
        "insurance": insurance,
    }

    return render(
        request,
        "social_insurance/social_insurance_form.html",
        context
    )


# =========================================================
# XÓA BHXH
# =========================================================

@login_required
def social_insurance_delete(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )

    insurance = get_object_or_404(
        SocialInsurance,
        employee=employee
    )

    if request.method == "POST":

        insurance.delete()

        messages.success(
            request,
            f"Đã xóa hồ sơ BHXH của {employee.full_name}."
        )

        return redirect(
            "social_insurance_employee",
            pk=employee.pk
        )

    return render(
        request,
        "social_insurance/social_insurance_confirm_delete.html",
        {
            "employee": employee,
            "insurance": insurance,
        }
    )


@login_required
def social_insurance(request):

    insurances = (
        SocialInsurance.objects
        .select_related("employee")
        .all()
        .order_by("employee__employee_code")
    )

    context = {
        "insurances": insurances,
    }

    return render(
        request,
        "social_insurance/social_insurance_list.html",
        context
    )


@login_required
def social_insurance_create(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )

    if SocialInsurance.objects.filter(
        employee=employee
    ).exists():

        messages.warning(
            request,
            "Nhân viên này đã có hồ sơ BHXH."
        )

        return redirect(
            "social_insurance_employee",
            pk=employee.pk
        )


    if request.method == "POST":

        insurance = SocialInsurance(

            employee=employee,

            social_insurance_number=request.POST.get(
                "social_insurance_number",
                ""
            ).strip(),

            social_insurance_book=request.POST.get(
                "social_insurance_book",
                ""
            ).strip(),

            health_insurance_number=request.POST.get(
                "health_insurance_number",
                ""
            ).strip(),

            health_insurance_hospital=request.POST.get(
                "health_insurance_hospital",
                ""
            ).strip(),

            insurance_start_date=(
                request.POST.get(
                    "insurance_start_date"
                ) or None
            ),

            health_insurance_start=(
                request.POST.get(
                    "health_insurance_start"
                ) or None
            ),

            health_insurance_expiry=(
                request.POST.get(
                    "health_insurance_expiry"
                ) or None
            ),

            insurance_salary=(
                request.POST.get(
                    "insurance_salary"
                ) or None
            ),

            position_allowance=(
                request.POST.get(
                    "position_allowance"
                ) or 0
            ),

            other_allowance=(
                request.POST.get(
                    "other_allowance"
                ) or 0
            ),

            employee_social_rate=(
                request.POST.get(
                    "employee_social_rate"
                ) or 8
            ),

            company_social_rate=(
                request.POST.get(
                    "company_social_rate"
                ) or 17.5
            ),

            employee_health_rate=(
                request.POST.get(
                    "employee_health_rate"
                ) or 1.5
            ),

            company_health_rate=(
                request.POST.get(
                    "company_health_rate"
                ) or 3
            ),

            employee_unemployment_rate=(
                request.POST.get(
                    "employee_unemployment_rate"
                ) or 1
            ),

            company_unemployment_rate=(
                request.POST.get(
                    "company_unemployment_rate"
                ) or 1
            ),

            status=request.POST.get(
                "insurance_status",
                "active"
            ),

            notes=request.POST.get(
                "insurance_notes",
                ""
            ).strip(),
        )

        insurance.save()

        messages.success(
            request,
            f"Đã tạo hồ sơ BHXH cho {employee.full_name}."
        )

        return redirect(
            "social_insurance_employee",
            pk=employee.pk
        )


    return render(
        request,
        "social_insurance/social_insurance_form.html",
        {
            "employee": employee,
            "insurance": None,
        }
    )
@login_required
def social_insurance_edit(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )

    insurance = get_object_or_404(
        SocialInsurance,
        employee=employee
    )

    # =====================================================
    # LẤY LỊCH SỬ MỨC ĐÓNG HIỆN TẠI
    # =====================================================

    rate_histories = (
        insurance.rate_histories
        .all()
        .order_by("-effective_from", "-created_at")
    )


    if request.method == "POST":

        # =================================================
        # THÔNG TIN HỒ SƠ BHXH
        # =================================================

        insurance.social_insurance_number = request.POST.get(
            "social_insurance_number",
            ""
        ).strip()

        insurance.social_insurance_book = request.POST.get(
            "social_insurance_book",
            ""
        ).strip()

        insurance.health_insurance_number = request.POST.get(
            "health_insurance_number",
            ""
        ).strip()

        insurance.health_insurance_hospital = request.POST.get(
            "health_insurance_hospital",
            ""
        ).strip()

        insurance.insurance_start_date = (
            request.POST.get(
                "insurance_start_date"
            ) or None
        )

        insurance.health_insurance_start = (
            request.POST.get(
                "health_insurance_start"
            ) or None
        )

        insurance.health_insurance_expiry = (
            request.POST.get(
                "health_insurance_expiry"
            ) or None
        )

        insurance.status = request.POST.get(
            "insurance_status",
            "active"
        )

        insurance.notes = request.POST.get(
            "insurance_notes",
            ""
        ).strip()

        insurance.save()

        # =================================================
        # MỨC ĐÓNG BHXH THEO NĂM
        # =================================================

        year = request.POST.get(
            "rate_year"
        )

        if year:

            InsuranceRateHistory.objects.update_or_create(

                social_insurance=insurance,

                year=int(year),

                defaults={

                    "insurance_salary": (
                        request.POST.get(
                            "insurance_salary"
                        ) or 0
                    ),

                    "position_allowance": (
                        request.POST.get(
                            "position_allowance"
                        ) or 0
                    ),

                    "other_allowance": (
                        request.POST.get(
                            "other_allowance"
                        ) or 0
                    ),

                    "employee_social_rate": (
                        request.POST.get(
                            "employee_social_rate"
                        ) or 8
                    ),

                    "company_social_rate": (
                        request.POST.get(
                            "company_social_rate"
                        ) or 17.5
                    ),

                    "employee_health_rate": (
                        request.POST.get(
                            "employee_health_rate"
                        ) or 1.5
                    ),

                    "company_health_rate": (
                        request.POST.get(
                            "company_health_rate"
                        ) or 3
                    ),

                    "employee_unemployment_rate": (
                        request.POST.get(
                            "employee_unemployment_rate"
                        ) or 1
                    ),

                    "company_unemployment_rate": (
                        request.POST.get(
                            "company_unemployment_rate"
                        ) or 1
                    ),

                    "notes": (
                        request.POST.get(
                            "rate_notes",
                            ""
                        ).strip()
                    ),
                }
            )

        messages.success(
            request,
            f"Đã cập nhật hồ sơ BHXH của {employee.full_name}."
        )

        return redirect(
            "social_insurance_employee",
            pk=employee.pk
        )

    # =====================================================
    # FORM
    # =====================================================

    current_rate = rate_histories.first()

    return render(
        request,
        "social_insurance/social_insurance_form.html",
        {
            "employee": employee,
            "insurance": insurance,
            "rate_histories": rate_histories,
            "current_rate": current_rate,
        }
    )


@login_required
def social_insurance_create(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )

    try:

        insurance = employee.social_insurance

        messages.warning(
            request,
            "Nhân viên này đã có hồ sơ BHXH."
        )

        return redirect(
            "social_insurance_employee",
            pk=employee.pk
        )

    except SocialInsurance.DoesNotExist:

        insurance = None

    if request.method == "POST":

        insurance = SocialInsurance(

            employee=employee,

            social_insurance_number=request.POST.get(
                "social_insurance_number",
                ""
            ).strip(),

            social_insurance_book=request.POST.get(
                "social_insurance_book",
                ""
            ).strip(),

            health_insurance_number=request.POST.get(
                "health_insurance_number",
                ""
            ).strip(),

            health_insurance_hospital=request.POST.get(
                "health_insurance_hospital",
                ""
            ).strip(),

            insurance_start_date=request.POST.get(
                "insurance_start_date"
            ) or None,

            health_insurance_start=request.POST.get(
                "health_insurance_start"
            ) or None,

            health_insurance_expiry=request.POST.get(
                "health_insurance_expiry"
            ) or None,

            status=request.POST.get(
                "insurance_status",
                "active"
            ),

            notes=request.POST.get(
                "insurance_notes",
                ""
            ).strip(),
        )

        insurance.save()

        # =================================================
        # LỊCH SỬ MỨC ĐÓNG
        # =================================================

        InsuranceRateHistory.objects.create(

            social_insurance=insurance,

            year=request.POST.get(
                "rate_year"
            ) or 2026,

            insurance_salary=request.POST.get(
                "insurance_salary"
            ) or 0,

            position_allowance=request.POST.get(
                "position_allowance"
            ) or 0,

            other_allowance=request.POST.get(
                "other_allowance"
            ) or 0,

            employee_social_rate=request.POST.get(
                "employee_social_rate"
            ) or 8,

            company_social_rate=request.POST.get(
                "company_social_rate"
            ) or 17.5,

            employee_health_rate=request.POST.get(
                "employee_health_rate"
            ) or 1.5,

            company_health_rate=request.POST.get(
                "company_health_rate"
            ) or 3,

            employee_unemployment_rate=request.POST.get(
                "employee_unemployment_rate"
            ) or 1,

            company_unemployment_rate=request.POST.get(
                "company_unemployment_rate"
            ) or 1,

            notes=request.POST.get(
                "rate_notes",
                ""
            ).strip(),
        )

        messages.success(
            request,
            f"Đã tạo hồ sơ BHXH cho {employee.full_name}."
        )

        return redirect(
            "social_insurance_employee",
            pk=employee.pk
        )

    return render(
        request,
        "social_insurance/social_insurance_form.html",
        {
            "employee": employee,
            "insurance": insurance,
        }
    )
