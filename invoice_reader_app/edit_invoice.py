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

    return render(request, "edit_invoice.html", {
        "invoice": invoice,
        "form": form,
        "formset": formset,
    })


