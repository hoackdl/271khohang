# invoice_reader_app/context_processors.py

from datetime import datetime

def current_fiscal_year(request):
    return {
        "current_year": request.session.get(
            "fiscal_year", datetime.now().year
        )
    }
