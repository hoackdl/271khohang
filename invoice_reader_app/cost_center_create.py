from django.shortcuts import render, redirect
from django.contrib import messages
from invoice_reader_app.models_purchaseorder import BankPayment, PurchaseOrder, BankPaymentAllocation, CostCenter
from invoice_reader_app.forms import CostCenterForm
from django.db.models import Sum


def cost_center_create(request):

    if request.method == "POST":
        form = CostCenterForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Tạo trung tâm chi phí thành công!")
            return redirect("cost_center_create")

    else:
        form = CostCenterForm()

    cost_centers = CostCenter.objects.all().order_by("code")

    return render(request, "cost_center_create.html", {
        "form": form,
        "cost_centers": cost_centers,
    })



from django.shortcuts import render, get_object_or_404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator


def cost_center_detail(request, pk):

    cost_center = get_object_or_404(
        CostCenter,
        pk=pk
    )


    if request.method == "POST":

        cost_center.code = request.POST.get(
            "code",
            cost_center.code
        )

        cost_center.name = request.POST.get(
            "name",
            cost_center.name
        )

        cost_center.is_active = (
            request.POST.get("is_active") == "on"
        )

        cost_center.save()


        messages.success(
            request,
            "Cập nhật trung tâm chi phí thành công!"
        )


        return redirect(
            "cost_center_detail",
            pk=cost_center.id
        )


    bank_payments_qs = cost_center.bank_payments.prefetch_related(
        "purchase_orders",
        "cost_centers"
    ).order_by(
        "-payment_date",
        "-id"
    )


    # =========================
    # Phân trang
    # =========================
    per_page = request.GET.get(
        "per_page",
        20
    )

    try:
        per_page = int(per_page)
    except:
        per_page = 20


    paginator = Paginator(
        bank_payments_qs,
        per_page
    )


    page_number = request.GET.get(
        "page"
    )


    bank_payments = paginator.get_page(
        page_number
    )


    bank_payment_total = cost_center.bank_payments.aggregate(
        total_debit=Sum("debit"),
        total_credit=Sum("credit")
    )
    return render(
        request,
        "cost_center_detail.html",
        {
            "cost_center": cost_center,
            "bank_payments": bank_payments,

            "total_debit": bank_payment_total["total_debit"] or 0,
            "total_credit": bank_payment_total["total_credit"] or 0,

            "paginator": paginator,
            "per_page": per_page,
            "per_page_options": [
                20,
                50,
                100,
                "all"
            ],
        }
    )

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from invoice_reader_app.models_purchaseorder import CostCenter


def cost_center_edit(request, pk):

    cost_center = get_object_or_404(
        CostCenter,
        pk=pk
    )


    if request.method == "POST":

        cost_center.code = request.POST.get(
            "code"
        )

        cost_center.name = request.POST.get(
            "name"
        )


        cost_center.is_active = (
            request.POST.get("is_active")
            == "on"
        )


        cost_center.save()


        messages.success(
            request,
            "Cập nhật trung tâm chi phí thành công!"
        )


        return redirect(
            "cost_center_create"
        )


    return render(
        request,
        "cost_center_edit.html",
        {
            "cost_center": cost_center
        }
    )