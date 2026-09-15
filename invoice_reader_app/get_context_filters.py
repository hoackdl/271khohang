
from invoice_reader_app.models.account import Account, AccountSystem
from invoice_reader_app.models_fiscalyear import FiscalYear



def get_context_filters(request):
    fiscal_years = FiscalYear.objects.all()

    selected_year_id = request.GET.get("fiscal_year")
    selected_system_id = request.GET.get("account_system")

    selected_year = None
    selected_system = None

    if selected_year_id:
        selected_year = FiscalYear.objects.get(id=selected_year_id)
    else:
        selected_year = FiscalYear.objects.filter(is_active=True).first()

    account_systems = AccountSystem.objects.filter(fiscal_year=selected_year)

    if selected_system_id:
        selected_system = account_systems.filter(id=selected_system_id).first()
    else:
        selected_system = account_systems.order_by("-effective_from").first()

    return {
        "fiscal_years": fiscal_years,
        "account_systems": account_systems,
        "selected_year": selected_year.id if selected_year else None,
        "selected_system": selected_system.id if selected_system else None,
        "current_system": selected_system
    }