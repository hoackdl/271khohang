# invoice_reader_app/views.py

from django.shortcuts import redirect

def set_fiscal_year(request, year):
    request.session["fiscal_year"] = year
    return redirect(request.META.get("HTTP_REFERER", "/"))
