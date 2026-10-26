from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError

class AccountSystem(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)

    fiscal_year = models.ForeignKey("FiscalYear", on_delete=models.CASCADE)

    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.fiscal_year}"



class Account(models.Model):
    system = models.ForeignKey(AccountSystem, on_delete=models.CASCADE, related_name="accounts")

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    group = models.ForeignKey("AccountGroup", on_delete=models.SET_NULL, null=True, blank=True)  # ✅ ADD

    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)

    account_type = models.CharField(max_length=20, choices=[
        ("asset", "Tài sản"),
        ("liability", "Nợ phải trả"),
        ("equity", "Vốn"),
        ("revenue", "Doanh thu"),
        ("expense", "Chi phí"),
    ])

    class Meta:
        unique_together = ("system", "code")  # 🔥 QUAN TRỌNG

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        qs = AccountSystem.objects.filter(
            effective_from__lte=self.effective_to or self.effective_from
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=self.effective_from)
        )

        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if qs.exists():
            raise ValidationError("Khoảng thời gian bị overlap với hệ thống khác")


class JournalEntry(models.Model):
    date = models.DateField()
    description = models.TextField()

    account_system = models.ForeignKey(AccountSystem, on_delete=models.PROTECT)

    created_at = models.DateTimeField(auto_now_add=True)


class JournalEntryLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")

    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)

class AccountGroup(models.Model):
    system = models.ForeignKey(AccountSystem, on_delete=models.CASCADE, related_name="groups")

    code = models.CharField(max_length=10)   # 1, 2, 3, 4, 5
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} - {self.name}"
    


def create_default_account_system():
    system = AccountSystem.objects.create(
        name="VAS Default 2026",
        code="VAS2026",
        effective_from="2026-01-01"
    )

    asset = AccountGroup.objects.create(system=system, code="1", name="Tài sản")
    liability = AccountGroup.objects.create(system=system, code="3", name="Nợ phải trả")
    equity = AccountGroup.objects.create(system=system, code="4", name="Vốn")
    revenue = AccountGroup.objects.create(system=system, code="5", name="Doanh thu")
    expense = AccountGroup.objects.create(system=system, code="6", name="Chi phí")

    Account.objects.bulk_create([
        Account(system=system, group=asset, code="111", name="Tiền mặt", account_type="asset"),
        Account(system=system, group=asset, code="112", name="Tiền ngân hàng", account_type="asset"),
        Account(system=system, group=liability, code="131", name="Phải thu khách hàng", account_type="liability"),
        Account(system=system, group=revenue, code="511", name="Doanh thu bán hàng", account_type="revenue"),
        Account(system=system, group=expense, code="632", name="Giá vốn hàng bán", account_type="expense"),
    ])

    return system