

from django.db import models
from django.db.models import Sum
from decimal import Decimal




class FiscalYear(models.Model):
    year = models.IntegerField(unique=True)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
