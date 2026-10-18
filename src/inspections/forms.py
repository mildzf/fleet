from django import forms
from django.db.models import Q
from django.forms import modelformset_factory

from drivers.models import Driver
from vehicles.models import Vehicle

from .models import ChecklistItem, DamagePoint, Inspection, InspectionResult


class InspectionForm(forms.ModelForm):
    class Meta:
        model = Inspection
        fields = ["inspection_type", "driver", "odometer", "overall_condition", "incident_reference", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, vehicle, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehicle = vehicle
        self.fields["driver"].queryset = Driver.objects.filter(status=Driver.Status.ACTIVE).select_related("user")
        self.fields["driver"].required = False
        self.fields["odometer"].widget.attrs["inputmode"] = "numeric"
        if not self.is_bound:
            self.initial["odometer"] = vehicle.odometer
            self.initial["driver"] = vehicle.current_driver
            self.initial["overall_condition"] = vehicle.condition

        self.items = list(
            ChecklistItem.objects.filter(is_active=True)
            .filter(Q(vehicle_types__isnull=True) | Q(vehicle_types=vehicle.vehicle_type_id))
            .distinct()
            .order_by("category", "sort_order", "name")
        )
        for item in self.items:
            self.fields[f"item_{item.pk}"] = forms.ChoiceField(
                label=item.name, choices=InspectionResult.Result.choices, widget=forms.RadioSelect
            )
            self.fields[f"note_{item.pk}"] = forms.CharField(
                label="What's wrong?", required=False, max_length=255
            )

    def checklist_rows(self):
        return [
            {"item": item, "result": self[f"item_{item.pk}"], "note": self[f"note_{item.pk}"]}
            for item in self.items
        ]

    def clean(self):
        data = super().clean()
        odo = data.get("odometer")
        if odo is not None and odo < self.vehicle.odometer:
            self.add_error("odometer", f"Can't be lower than the recorded odometer ({self.vehicle.odometer}).")
        for item in self.items:
            if data.get(f"item_{item.pk}") == "fail" and not data.get(f"note_{item.pk}"):
                self.add_error(f"note_{item.pk}", "Please say what's wrong.")
        return data

    def unsafe_flag(self):
        if self.cleaned_data.get("overall_condition") == Vehicle.Condition.UNSAFE:
            return True
        return any(
            item.is_critical and self.cleaned_data.get(f"item_{item.pk}") == "fail" for item in self.items
        )

    def save_results(self, inspection):
        InspectionResult.objects.bulk_create(
            InspectionResult(
                inspection=inspection,
                item=item,
                item_name=item.name,
                category=item.category,
                is_critical=item.is_critical,
                result=self.cleaned_data[f"item_{item.pk}"],
                notes=self.cleaned_data.get(f"note_{item.pk}", ""),
            )
            for item in self.items
        )


class DamageForm(forms.ModelForm):
    class Meta:
        model = DamagePoint
        fields = ["view", "x", "y", "severity", "description", "photo"]
        widgets = {
            "view": forms.HiddenInput,
            "x": forms.HiddenInput,
            "y": forms.HiddenInput,
            "description": forms.TextInput(attrs={"placeholder": "e.g. Scratch on rear door"}),
            "photo": forms.FileInput(attrs={"accept": "image/*"}),
        }


DamageFormSet = modelformset_factory(DamagePoint, form=DamageForm, extra=0)
