from datetime import datetime
from django.db.models import Max

def sync_fiscal_year(request, model):
    session_year = request.session.get("fiscal_year")

    if (
        not session_year
        or not model.objects.filter(fiscal_year=session_year).exists()
    ):
        latest_year = model.objects.aggregate(
            max_year=Max("fiscal_year")
        )["max_year"]

        request.session["fiscal_year"] = latest_year or datetime.now().year

    return request.session["fiscal_year"]
