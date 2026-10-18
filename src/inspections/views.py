from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from vehicles.models import Vehicle

from .forms import DamageFormSet, InspectionForm
from .models import DamagePoint, Inspection


def damage_payload(queryset):
    """Damage points as plain dicts for the body-map JavaScript."""
    return [
        {
            "view": d.view,
            "x": d.x,
            "y": d.y,
            "severity": d.get_severity_display(),
            "description": d.description,
            "status": d.status,
        }
        for d in queryset
    ]


@login_required
def inspection_list(request):
    inspections = Inspection.objects.select_related("vehicle", "inspected_by", "driver__user")[:100]
    return render(request, "inspections/inspection_list.html", {"inspections": inspections})


@login_required
def start(request):
    """Pick a vehicle to inspect."""
    vehicles = Vehicle.objects.exclude(status=Vehicle.Status.RETIRED).select_related("vehicle_type")
    return render(request, "inspections/start.html", {"vehicles": vehicles})


@login_required
def inspection_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle.objects.select_related("vehicle_type"), pk=vehicle_pk)

    if request.method == "POST":
        form = InspectionForm(request.POST, vehicle=vehicle)
        formset = DamageFormSet(
            request.POST, request.FILES, queryset=DamagePoint.objects.none(), prefix="damage"
        )
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                inspection = form.save(commit=False)
                inspection.vehicle = vehicle
                inspection.inspected_by = request.user
                inspection.unsafe_to_use = form.unsafe_flag()
                inspection.save()
                form.save_results(inspection)
                for point in formset.save(commit=False):
                    point.vehicle = vehicle
                    point.inspection = inspection
                    point.save()
            return redirect("inspections:detail", pk=inspection.pk)
    else:
        form = InspectionForm(vehicle=vehicle)
        formset = DamageFormSet(queryset=DamagePoint.objects.none(), prefix="damage")

    open_damage = vehicle.damage_points.filter(status=DamagePoint.Status.OPEN)
    return render(
        request,
        "inspections/inspection_form.html",
        {
            "vehicle": vehicle,
            "form": form,
            "formset": formset,
            "rows": form.checklist_rows(),
            "damage_json": damage_payload(open_damage),
        },
    )


@login_required
def inspection_detail(request, pk):
    inspection = get_object_or_404(
        Inspection.objects.select_related("vehicle", "driver__user", "inspected_by"), pk=pk
    )
    damage = inspection.damage_points.all()
    return render(
        request,
        "inspections/inspection_detail.html",
        {
            "inspection": inspection,
            "results": inspection.results.all(),
            "damage": damage,
            "damage_json": damage_payload(damage),
        },
    )


@login_required
def vehicle_history(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    damage = vehicle.damage_points.select_related("inspection")
    open_damage = damage.filter(status=DamagePoint.Status.OPEN)
    return render(
        request,
        "inspections/vehicle_history.html",
        {
            "vehicle": vehicle,
            "damage": damage,
            "open_count": open_damage.count(),
            "damage_json": damage_payload(open_damage),
            "inspections": vehicle.inspections.select_related("inspected_by", "driver__user")[:50],
        },
    )


@require_POST
@permission_required("inspections.change_damagepoint", raise_exception=True)
def damage_repaired(request, pk):
    point = get_object_or_404(DamagePoint, pk=pk)
    point.status = DamagePoint.Status.REPAIRED
    point.repaired_on = timezone.localdate()
    point.save(update_fields=["status", "repaired_on"])
    return redirect("inspections:vehicle", vehicle_pk=point.vehicle_id)
