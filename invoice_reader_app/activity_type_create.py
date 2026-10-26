from django.shortcuts import render, redirect
from django.contrib import messages

from django.shortcuts import render, redirect
from django.contrib import messages

from invoice_reader_app.models_purchaseorder import ActivityType
from invoice_reader_app.forms import ActivityTypeForm

def activity_type_create(request):


    if request.method == "POST":

        form = ActivityTypeForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Tạo loại hình hoạt động thành công!"
            )

            return redirect(
                "activity_type_create"
            )

    else:

        form = ActivityTypeForm()

    activity_types = (
        ActivityType.objects
        .all()
        .order_by("code")
    )

    return render(
        request,
        "activity_type_create.html",
        {
            "form": form,
            "activity_types": activity_types,
        }
    )


from django.shortcuts import (
render,
get_object_or_404,
redirect,
)

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum

from invoice_reader_app.models_purchaseorder import (
ActivityType,
)

def activity_type_detail(request, pk):


    activity_type = get_object_or_404(
        ActivityType,
        pk=pk
    )

    if request.method == "POST":

        activity_type.code = request.POST.get(
            "code",
            activity_type.code
        )

        activity_type.name = request.POST.get(
            "name",
            activity_type.name
        )

        activity_type.is_active = (
            request.POST.get("is_active") == "on"
        )

        activity_type.save()

        messages.success(
            request,
            "Cập nhật loại hình hoạt động thành công!"
        )

        return redirect(
            "activity_type_detail",
            pk=activity_type.id
        )

    allocations_qs = (
        activity_type.payment_allocations
        .select_related(
            "payment",
            "purchase_order",
            "purchase_order__customer",
        )
        .order_by(
            "-payment__payment_date",
            "-id"
        )
    )

    per_page = request.GET.get(
        "per_page",
        "20"
    )

    if per_page == "all":

        per_page_number = (
            allocations_qs.count()
            or 1
        )

    else:

        try:

            per_page_number = int(
                per_page
            )

        except (
            TypeError,
            ValueError
        ):

            per_page_number = 20

    paginator = Paginator(
        allocations_qs,
        per_page_number
    )

    page_number = request.GET.get(
        "page"
    )

    allocations = paginator.get_page(
        page_number
    )

    total = (
        activity_type.payment_allocations
        .aggregate(
            total=Sum(
                "allocated_amount"
            )
        )
    )

    return render(
        request,
        "activity_type_detail.html",
        {
            "activity_type": activity_type,
            "allocations": allocations,
            "total": total["total"] or 0,
            "paginator": paginator,
            "per_page": per_page,
            "per_page_options": [
                20,
                50,
                100,
                "all",
            ],
        }
    )


from django.shortcuts import (
render,
redirect,
get_object_or_404,
)

from django.contrib import messages

from invoice_reader_app.models_purchaseorder import (
ActivityType,
)

def activity_type_edit(request, pk):

  
    activity_type = get_object_or_404(
        ActivityType,
        pk=pk
    )

    if request.method == "POST":

        activity_type.code = request.POST.get(
            "code"
        )

        activity_type.name = request.POST.get(
            "name"
        )

        activity_type.is_active = (
            request.POST.get("is_active") == "on"
        )

        activity_type.save()

        messages.success(
            request,
            "Cập nhật loại hình hoạt động thành công!"
        )

        return redirect(
            "activity_type_create"
        )

    return render(
        request,
        "activity_type_edit.html",
        {
            "activity_type": activity_type,
        }
    )

