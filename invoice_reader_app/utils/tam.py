

from django.db.models import Q
from django.core.exceptions import ValidationError
from invoice_reader_app.models.account import AccountSystem, Account,JournalEntry
    
    
    
    
def get_account_system_by_date(date):
        return AccountSystem.objects.filter(
            effective_from__lte=date
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=date)
        ).order_by("-effective_from").first()



def clone_account_system(old_system, new_date):
        new_system = AccountSystem.objects.create(
            name=old_system.name + " v2",
            code=old_system.code + "_v2",
            effective_from=new_date
        )

        for acc in old_system.accounts.all():
            Account.objects.create(
                system=new_system,
                code=acc.code,
                name=acc.name,
                parent=acc.parent,
                account_type=acc.account_type
            )

        return new_system


def create_journal_entry(date, description):
        system = get_account_system_by_date(date)

        if not system:
            raise ValueError("Không có hệ thống tài khoản cho ngày này")

        return JournalEntry.objects.create(
            date=date,
            description=description,
            account_system=system
        )


def clean(self):
        if self.account.system != self.entry.account_system:
            raise ValidationError("Account không thuộc cùng hệ thống với JournalEntry")