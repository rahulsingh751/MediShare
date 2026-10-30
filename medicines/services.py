from django.utils import timezone

from .models import MedicineListing


def publicly_discoverable_listings():
    return MedicineListing.objects.filter(
        status=MedicineListing.Status.APPROVED,
        expiry_date__gt=timezone.localdate(),
        quantity_available__gt=0,
        prescription_required=False,
        controlled_or_restricted=False,
        original_packaging=True,
        seal_intact=True,
        packaging_opened=False,
        packaging_damaged=False,
        stored_as_instructed=True,
        recall_status_confirmed=True,
        requires_cold_chain=False,
        visible_damage=False,
    )
