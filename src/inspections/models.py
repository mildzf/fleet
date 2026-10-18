from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from vehicles.models import Vehicle


class ChecklistItem(models.Model):
    """Editable in the admin. Shown on the inspection form for the vehicle types it applies to."""

    name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, blank=True, help_text="Group heading, e.g. Tyres, Lights, Fluids.")
    is_critical = models.BooleanField(
        default=False, help_text="If this fails, the vehicle is flagged unsafe to use."
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    vehicle_types = models.ManyToManyField(
        "vehicles.VehicleType",
        blank=True,
        related_name="checklist_items",
        help_text="Leave empty to apply to every vehicle type.",
    )

    class Meta:
        ordering = ["category", "sort_order", "name"]

    def __str__(self):
        return self.name


class Inspection(models.Model):
    class Type(models.TextChoices):
        PRE_TRIP = "pre_trip", "Pre-trip / start of shift"
        HANDOVER = "handover", "Handover between drivers"
        PERIODIC = "periodic", "Periodic (weekly / monthly)"
        INCIDENT = "incident", "After an incident or accident"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="inspections")
    inspection_type = models.CharField(max_length=20, choices=Type.choices, default=Type.PRE_TRIP)
    inspected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    driver = models.ForeignKey(
        "drivers.Driver", null=True, blank=True, on_delete=models.SET_NULL, related_name="inspections",
        help_text="Driver in charge of the vehicle at the time.",
    )
    inspected_at = models.DateTimeField(default=timezone.now)
    odometer = models.PositiveIntegerField()
    overall_condition = models.CharField(max_length=20, choices=Vehicle.Condition.choices)
    unsafe_to_use = models.BooleanField(default=False)
    incident_reference = models.CharField(
        max_length=50, blank=True, help_text="Your internal incident report number, if any."
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-inspected_at", "-id"]

    def __str__(self):
        return f"{self.vehicle.fleet_number} - {self.get_inspection_type_display()} ({self.inspected_at:%Y-%m-%d})"

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding:
            self.apply_to_vehicle()

    def apply_to_vehicle(self):
        """Push condition/odometer (and unsafe flag) to the vehicle, only if this is its latest inspection."""
        latest = self.vehicle.inspections.order_by("-inspected_at", "-id").first()
        if latest and latest.pk != self.pk:
            return
        updates = {
            "condition": self.overall_condition,
            "condition_updated": timezone.localtime(self.inspected_at).date(),
        }
        if self.odometer > self.vehicle.odometer:
            updates["odometer"] = self.odometer
        if self.unsafe_to_use and self.vehicle.status == Vehicle.Status.ACTIVE:
            updates["status"] = Vehicle.Status.OUT_OF_SERVICE
        Vehicle.objects.filter(pk=self.vehicle_id).update(**updates)


class InspectionResult(models.Model):
    class Result(models.TextChoices):
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"
        NA = "na", "N/A"

    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name="results")
    item = models.ForeignKey(ChecklistItem, null=True, on_delete=models.SET_NULL, related_name="results")
    # Snapshots, so editing or deleting a checklist item never rewrites history.
    item_name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, blank=True)
    is_critical = models.BooleanField(default=False)
    result = models.CharField(max_length=10, choices=Result.choices)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["category", "id"]

    def __str__(self):
        return f"{self.item_name}: {self.result}"


class DamagePoint(models.Model):
    """A mark on the vehicle body map. Belongs to the vehicle; remembers which inspection first reported it."""

    class View(models.TextChoices):
        LEFT = "left", "Left"
        RIGHT = "right", "Right"
        FRONT = "front", "Front"
        REAR = "rear", "Rear"
        TOP = "top", "Top"

    class Severity(models.TextChoices):
        MINOR = "minor", "Minor"
        MODERATE = "moderate", "Moderate"
        SEVERE = "severe", "Severe"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REPAIRED = "repaired", "Repaired"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="damage_points")
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name="damage_points")
    view = models.CharField(max_length=10, choices=View.choices)
    # Position as a percentage (0-100) across and down the view, so it works at any screen size.
    x = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    y = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MINOR)
    description = models.CharField(max_length=255)
    photo = models.ImageField(upload_to="damage/%Y/%m/", blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    repaired_on = models.DateField(null=True, blank=True)
    repair_notes = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created", "-id"]

    def __str__(self):
        return f"{self.vehicle.fleet_number} {self.get_view_display()}: {self.description}"
