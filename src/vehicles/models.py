from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


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
    SEVERITY = {NO_HISTORY: 3, OVERDUE: 2, DUE_SOON: 1, OK:0}



class Driver(models.Model):
    """Placeholder until the real drive app exists."""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    employee_number = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class VehicleType(models.Model):
    """Types of Vehicles eg. armored, SUV, etc"""
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ServiceType(models.Model):
    """eg.Oil change, Brake inspection, etc"""
    name = models.CharField(max_length=100, unique=True)
    interval_days = models.PositiveIntegerField(
            null=True, 
            blank=True, 
            help_text="Repeant every N days(leave blank if not date based)."
        )
    interval_distance = models.PositiveIntegerField(
            null=True,
            blank=True,
            help_text="Repeat ever N km/miles (leave blank if not distance based)."
        )
    class Meta:
        ordering = ["Name"]

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        IN_SERVICE = "in_service", "In the garage"
        OUT_OF_SERVICE = "Out of service", "Out of service"
        RETIRED = "retired", "Retired"

    class Condition(models.TextChoices):
        EXCELLENT = "excellent", "Excellent"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        POOR = "poor", "Poor"
        UNSAFE = "unsafe", "Unsafe - do not use"
    fleet_number = models.CharField(max_length=30, unique=True)
    plate_number = models.CharField(max_length=20, unique=True)
    vin = models.CharField("VIN/ chassis no.", max_length=30, blank=True)
    make = models.CharField(max_length=50)
    model = model.CharField(max_length=50)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    colour = models.CharField(max_length=30, blank=True)
    vehicle_type = models.ForeignKey(
            VehicleType, 
            on_delete=models.PROTECT, 
            related_name="vehicles"
        )
    is_armored = models.BooleanField(default=False)
    armor_rating = models.CharField(
            max_length=50,
            blank=True,
            help_text="eg. B6, BR7, HG1 only if armored"
        )
    special_equipment = models.TextField(
            blank=True,
            help_text="Safe, Radios, lights, etc"
        )
    odometer = models.PositiveIntegerField(default=0, help_text="current reading")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)
    condition_notes = models.TextField(blank=True)
    condition_updated = models.DateField(null=True, blank=True)
    assigned_driver = models.ForeignkKey(
            Driver,
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="vehicles"
        )
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
        """Most recent service record for each type."""
        latest = {}
        records = self.service_records.select_related("service_type").order_by("performed_on", "id")
        for rec in records:
            latest[rec.service_type_id] = rec
        return list(latest.values())

    def service_items(self):
        """Record and status for each service type this vehicle has a history for"""
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
    reference = models.CharField(max_length=50, blank=True, help_text="Invoice/ job card number.")
    description = models.TextField(blank=True)

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

        # keep the vehicle's odometer from lagging behind it's service history
        if self.odometer_at_service > self.vehicle.odometer:
            Vehicle.objects.filter(pk=self.vehicle_id).update(odometer=self.odometer_at_service)

    def status_for(self, current_odometer):
        """ status for whichever comes first, date or distance."""
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
            if left <=0:
                statuses.append(ServiceStatus.OVERDUE)
            elif left <= DUE_SOON_DISTANCE:
                statuses.append(ServiceStatus.DUE_SOON)
        if not statuses:
            return ServiceStatus.OK
        return max(statuses, key=lambda s: ServiceStatus.SEVERITY[s])

