from django.shortcuts import render, get_object_or_404, redirect
from django.forms import modelformset_factory
from django.contrib import messages
from .model_invoice import Invoice, InvoiceItem
from .forms import InvoiceForm, InvoiceItemForm
def edit_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    ItemFormSet = modelformset_factory(InvoiceItem, form=InvoiceItemForm, extra=0, can_delete=False)

    if request.method == "POST":
        form = InvoiceForm(request.POST, instance=invoice)
        formset = ItemFormSet(request.POST, queryset=invoice.items.all())

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "✅ Cập nhật hóa đơn thành công!")
            return redirect('invoice_list')
        else:
            messages.error(request, "⚠️ Có lỗi khi lưu dữ liệu. Vui lòng kiểm tra lại.")
    else:
        form = InvoiceForm(instance=invoice)
        formset = ItemFormSet(queryset=invoice.items.all())
    from datetime import timedelta
    
    ngay_tru_3 = invoice.ngay_hd - timedelta(days=3)
    

    # Tính tổng cộng
    total_thanh_tien = sum([item.thanh_tien for item in invoice.items.all()])
    total_tien_thue = sum([item.tien_thue for item in invoice.items.all()])
    total_thanh_toan = total_thanh_tien + total_tien_thue

    return render(request, "edit_invoice.html", {
        "invoice": invoice,
        "ngay_tru_3":ngay_tru_3,
        "form": form,
        "formset": formset,
        "total_thanh_tien": total_thanh_tien,
        "total_tien_thue": total_tien_thue,
        "total_thanh_toan": total_thanh_toan,
    })


from django.forms import inlineformset_factory
from datetime import timedelta
from decimal import Decimal

def edit_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    ItemFormSet = inlineformset_factory(
        Invoice,
        InvoiceItem,
        form=InvoiceItemForm,
        extra=0,
        can_delete=False
    )

    if request.method == "POST":
        form = InvoiceForm(request.POST, instance=invoice)
        formset = ItemFormSet(request.POST, instance=invoice)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "✅ Cập nhật hóa đơn thành công!")
            return redirect('invoice_export_list')
        else:
            print(formset.errors)  # DEBUG
            messages.error(request, "⚠️ Có lỗi khi lưu dữ liệu.")
    else:
        form = InvoiceForm(instance=invoice)
        formset = ItemFormSet(instance=invoice)

    ngay_tru_3 = invoice.ngay_hd - timedelta(days=3)

    total_thanh_tien = sum(Decimal(i.thanh_tien or 0) for i in invoice.items.all())
    total_tien_thue = sum(Decimal(i.tien_thue or 0) for i in invoice.items.all())

    return render(request, "edit_invoice.html", {
        "invoice": invoice,
        "ngay_tru_3": ngay_tru_3,
        "form": form,
        "formset": formset,
        "total_thanh_tien": total_thanh_tien,
        "total_tien_thue": total_tien_thue,
        "total_thanh_toan": total_thanh_tien + total_tien_thue,
    })
