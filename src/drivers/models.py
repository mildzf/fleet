from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

# Tune these in settings.py if you like.
DUE_SOON_DAYS = getattr(settings, "FLEET_DUE_SOON_DAYS", 30)
DUE_SOON_DISTANCE = getattr(settings, "FLEET_DUE_SOON_DISTANCE", 500)


class ServiceStatus:
    OK = "ok"
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"
    NO_HISTORY = "no_history"

    LABELS = {
        OK: "Up to date",
        DUE_SOON: "Due soon",
        OVERDUE: "Overdue",
        NO_HISTORY: "No service history",
    }
    # Higher = worse, used to pick the worst status across service types
    SEVERITY = {NO_HISTORY: 3, OVERDUE: 2, DUE_SOON: 1, OK: 0}


class VehicleType(models.Model):
    """Admin-editable so the fleet's own categories can be added (armored, CIT, etc.)."""

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ServiceType(models.Model):
    """e.g. Oil change, Brake inspection, Armor integrity check."""

    name = models.CharField(max_length=100, unique=True)
    interval_days = models.PositiveIntegerField(
        null=True, blank=True, help_text="Repeat every N days (leave blank if not date-based)."
    )
    interval_distance = models.PositiveIntegerField(
        null=True, blank=True, help_text="Repeat every N km/miles (leave blank if not distance-based)."
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        IN_SERVICE = "in_service", "In the garage"
        OUT_OF_SERVICE = "out_of_service", "Out of service"
        RETIRED = "retired", "Retired"

    class Condition(models.TextChoices):
        EXCELLENT = "excellent", "Excellent"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        POOR = "poor", "Poor"
        UNSAFE = "unsafe", "Unsafe - do not use"

    fleet_number = models.CharField(max_length=30, unique=True)
    plate_number = models.CharField(max_length=20, unique=True)
    vin = models.CharField("VIN / chassis no.", max_length=30, blank=True)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    colour = models.CharField(max_length=30, blank=True)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.PROTECT, related_name="vehicles")

    is_armored = models.BooleanField(default=False)
    armor_rating = models.CharField(max_length=50, blank=True, help_text="e.g. B6, only if armored.")
    special_equipment = models.TextField(blank=True, help_text="Safe, radios, lights, etc.")

    odometer = models.PositiveIntegerField(default=0, help_text="Current reading (same unit every time).")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)
    condition_notes = models.TextField(blank=True)
    condition_updated = models.DateField(null=True, blank=True)

    registration_expiry = models.DateField(null=True, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["fleet_number"]

    def __str__(self):
        return f"{self.fleet_number} - {self.make} {self.model} ({self.plate_number})"

    def latest_service_records(self):
        """Most recent record for each service type."""
        latest = {}
        records = self.service_records.select_related("service_type").order_by("performed_on", "id")
        for rec in records:
            latest[rec.service_type_id] = rec
        return list(latest.values())

    def service_items(self):
        """[(record, status)] for each service type this vehicle has history for."""
        return [(rec, rec.status_for(self.odometer)) for rec in self.latest_service_records()]

    @property
    def service_status(self):
        items = self.service_items()
        if not items:
            return ServiceStatus.NO_HISTORY
        return max((s for _, s in items), key=lambda s: ServiceStatus.SEVERITY[s])

    @property
    def service_status_label(self):
        return ServiceStatus.LABELS[self.service_status]

    @property
    def service_badge(self):
        """(status, label) computed once, for templates."""
        status = self.service_status
        return status, ServiceStatus.LABELS[status]

    @property
    def current_driver(self):
        """The driver on the open (no end date) assignment, if any. Assignments live in the drivers app."""
        assignment = self.assignments.filter(end_date__isnull=True).select_related("driver__user").first()
        return assignment.driver if assignment else None

    @property
    def last_serviced(self):
        rec = self.service_records.order_by("-performed_on", "-id").first()
        return rec.performed_on if rec else None


class ServiceRecord(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="service_records")
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT, related_name="records")
    performed_on = models.DateField()
    odometer_at_service = models.PositiveIntegerField()
    performed_by = models.CharField(max_length=100, blank=True, help_text="Garage or technician.")
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reference = models.CharField(max_length=50, blank=True, help_text="Invoice / job card number.")
    description = models.TextField(blank=True)

    # Auto-filled from the service type's intervals when left blank; override if needed.
    next_due_date = models.DateField(null=True, blank=True)
    next_due_odometer = models.PositiveIntegerField(null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-performed_on", "-id"]

    def __str__(self):
        return f"{self.vehicle.fleet_number} - {self.service_type} on {self.performed_on}"

    def save(self, *args, **kwargs):
        st = self.service_type
        if self.next_due_date is None and st.interval_days:
            self.next_due_date = self.performed_on + timedelta(days=st.interval_days)
        if self.next_due_odometer is None and st.interval_distance:
            self.next_due_odometer = self.odometer_at_service + st.interval_distance
        super().save(*args, **kwargs)
        # Keep the vehicle's odometer from lagging behind its service history.
        if self.odometer_at_service > self.vehicle.odometer:
            Vehicle.objects.filter(pk=self.vehicle_id).update(odometer=self.odometer_at_service)

    def status_for(self, current_odometer):
        """Whichever comes first, date or distance."""
        today = timezone.localdate()
        statuses = []
        if self.next_due_date:
            days_left = (self.next_due_date - today).days
            if days_left < 0:
                statuses.append(ServiceStatus.OVERDUE)
            elif days_left <= DUE_SOON_DAYS:
                statuses.append(ServiceStatus.DUE_SOON)
        if self.next_due_odometer:
            left = self.next_due_odometer - current_odometer
            if left <= 0:
                statuses.append(ServiceStatus.OVERDUE)
            elif left <= DUE_SOON_DISTANCE:
                statuses.append(ServiceStatus.DUE_SOON)
        if not statuses:
            return ServiceStatus.OK
        return max(statuses, key=lambda s: ServiceStatus.SEVERITY[s])
