
from django.shortcuts import render, redirect
from django.contrib import messages

from invoice_reader_app.model_invoice import ProductGroup


def product_group_create(request):

    if request.method == "POST":

        code = request.POST.get("code", "").strip()
        name = request.POST.get("name", "").strip()
        is_active = request.POST.get("is_active") == "1"

        # Kiểm tra bắt buộc
        if not code:
            messages.error(
                request,
                "Vui lòng nhập mã nhóm hàng."
            )
            return render(
                request,
                "product_group_create.html"
            )

        if not name:
            messages.error(
                request,
                "Vui lòng nhập tên nhóm hàng."
            )
            return render(
                request,
                "product_group_create.html"
            )

        # Kiểm tra trùng mã
        if ProductGroup.objects.filter(
            code__iexact=code
        ).exists():

            messages.error(
                request,
                f"Mã nhóm hàng '{code}' đã tồn tại."
            )

            return render(
                request,
                "product_group_create.html",
                {
                    "code": code,
                    "name": name,
                }
            )

        # Kiểm tra trùng tên
        if ProductGroup.objects.filter(
            name__iexact=name
        ).exists():

            messages.error(
                request,
                f"Tên nhóm hàng '{name}' đã tồn tại."
            )

            return render(
                request,
                "product_group_create.html",
                {
                    "code": code,
                    "name": name,
                }
            )

        # Tạo nhóm hàng
        group = ProductGroup.objects.create(
            code=code,
            name=name,
            is_active=is_active,
        )

        messages.success(
            request,
            f"Đã tạo nhóm hàng '{group.name}' thành công."
        )

        return redirect("product_dmhh")

    return render(
        request,
        "product_group_create.html"
    )
