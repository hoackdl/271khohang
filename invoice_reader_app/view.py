# invoice_reader_app/views.py

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render



def set_fiscal_year(request, year):
    request.session["fiscal_year"] = year
    return redirect(request.META.get("HTTP_REFERER", "/"))





@login_required
def home(request):
    context = {
        "total_products": 0,
        "total_suppliers": 0,
        "total_customers": 0,
        "total_invoices": 0,

        "recent_activities": [],

        "chart_import": 0,
        "chart_export": 0,
    }

    return render(request, "home.html", context)