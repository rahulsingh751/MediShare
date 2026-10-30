from django import forms

from .models import MedicineRequest, Notification


class MedicineRequestForm(forms.ModelForm):
    quantity = forms.IntegerField(
        min_value=1, widget=forms.NumberInput(attrs={"min": "1"})
    )

    class Meta:
        model = MedicineRequest
        fields = ("quantity", "note")
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 1}),
            "note": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Optional information for the authorized reviewer",
                }
            ),
        }


class ListingReportForm(forms.Form):
    REASONS = (
        ("expired", "Possibly expired or recalled"),
        ("unsafe", "Unsafe or damaged packaging"),
        ("misleading", "Incorrect or misleading information"),
        ("suspicious", "Suspicious activity"),
        ("other", "Other safety concern"),
    )
    reason = forms.ChoiceField(choices=REASONS)
    details = forms.CharField(max_length=1000, widget=forms.Textarea(attrs={"rows": 4}))
