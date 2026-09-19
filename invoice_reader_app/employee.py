from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from invoice_reader_app.models_social_insurance import Employee


# =========================================================
# DANH SÁCH NHÂN SỰ
# =========================================================

@login_required
def employee_list(request):

    employees = Employee.objects.all().order_by(
        "employee_code"
    )

    context = {
        "employees": employees,
    }

    return render(
        request,
        "employees/employee_list.html",
        context
    )


# =========================================================
# THÊM NHÂN SỰ
# =========================================================

@login_required
def employee_create(request):

    if request.method == "POST":

        employee_code = request.POST.get(
            "employee_code",
            ""
        ).strip()

        full_name = request.POST.get(
            "full_name",
            ""
        ).strip()

        if not employee_code:

            messages.error(
                request,
                "Vui lòng nhập mã nhân viên."
            )

            return render(
                request,
                "employees/employee_form.html"
            )

        if not full_name:

            messages.error(
                request,
                "Vui lòng nhập họ và tên."
            )

            return render(
                request,
                "employees/employee_form.html"
            )

        if Employee.objects.filter(
            employee_code__iexact=employee_code
        ).exists():

            messages.error(
                request,
                "Mã nhân viên đã tồn tại."
            )

            return render(
                request,
                "employees/employee_form.html"
            )

        employee = Employee()

        employee.employee_code = employee_code
        employee.full_name = full_name

        employee.gender = request.POST.get(
            "gender",
            ""
        ).strip()

        employee.date_of_birth = (
            request.POST.get("date_of_birth")
            or None
        )

        employee.citizen_id = request.POST.get(
            "citizen_id",
            ""
        ).strip()

        employee.phone = request.POST.get(
            "phone",
            ""
        ).strip()

        employee.email = request.POST.get(
            "email",
            ""
        ).strip()

        employee.address = request.POST.get(
            "address",
            ""
        ).strip()

        employee.department = request.POST.get(
            "department",
            ""
        ).strip()

        employee.position = request.POST.get(
            "position",
            ""
        ).strip()

        employee.join_date = (
            request.POST.get("join_date")
            or None
        )

        employee.salary = (
            request.POST.get("salary")
            or None
        )

        employee.status = request.POST.get(
            "status",
            "active"
        )

        employee.notes = request.POST.get(
            "notes",
            ""
        ).strip()

        employee.save()

        messages.success(
            request,
            f"Đã thêm nhân sự {employee.full_name}."
        )

        return redirect("employees")

    return render(
        request,
        "employees/employee_form.html"
    )


# =========================================================
# SỬA NHÂN SỰ
# =========================================================

@login_required
def employee_edit(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )

    if request.method == "POST":

        employee_code = request.POST.get(
            "employee_code",
            ""
        ).strip()

        full_name = request.POST.get(
            "full_name",
            ""
        ).strip()

        if not employee_code:

            messages.error(
                request,
                "Vui lòng nhập mã nhân viên."
            )

            return render(
                request,
                "employees/employee_form.html",
                {
                    "employee": employee
                }
            )

        if not full_name:

            messages.error(
                request,
                "Vui lòng nhập họ và tên."
            )

            return render(
                request,
                "employees/employee_form.html",
                {
                    "employee": employee
                }
            )

        if Employee.objects.filter(
            employee_code__iexact=employee_code
        ).exclude(
            pk=employee.pk
        ).exists():

            messages.error(
                request,
                "Mã nhân viên đã được sử dụng."
            )

            return render(
                request,
                "employees/employee_form.html",
                {
                    "employee": employee
                }
            )

        employee.employee_code = employee_code
        employee.full_name = full_name

        employee.gender = request.POST.get(
            "gender",
            ""
        ).strip()

        employee.date_of_birth = (
            request.POST.get("date_of_birth")
            or None
        )

        employee.citizen_id = request.POST.get(
            "citizen_id",
            ""
        ).strip()

        employee.phone = request.POST.get(
            "phone",
            ""
        ).strip()

        employee.email = request.POST.get(
            "email",
            ""
        ).strip()

        employee.address = request.POST.get(
            "address",
            ""
        ).strip()

        employee.department = request.POST.get(
            "department",
            ""
        ).strip()

        employee.position = request.POST.get(
            "position",
            ""
        ).strip()

        employee.join_date = (
            request.POST.get("join_date")
            or None
        )

        employee.salary = (
            request.POST.get("salary")
            or None
        )

        employee.status = request.POST.get(
            "status",
            "active"
        )

        employee.notes = request.POST.get(
            "notes",
            ""
        ).strip()

        employee.save()

        messages.success(
            request,
            f"Đã cập nhật nhân sự {employee.full_name}."
        )

        return redirect("employees")

    return render(
        request,
        "employees/employee_form.html",
        {
            "employee": employee
        }
    )


# =========================================================
# XÓA NHÂN SỰ
# =========================================================

@login_required
def employee_delete(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )

    if request.method == "POST":

        employee_name = employee.full_name

        employee.delete()

        messages.success(
            request,
            f"Đã xóa nhân sự {employee_name}."
        )

        return redirect("employees")

    return render(
        request,
        "employees/employee_confirm_delete.html",
        {
            "employee": employee
        }
    )
