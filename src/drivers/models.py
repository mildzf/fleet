from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

# Days before a licence/certification expires that it shows as "expiring".
EXPIRY_WARN_DAYS = getattr(settings, "FLEET_EXPIRY_WARN_DAYS", 60)


class ExpiryStatus:
    VALID = "valid"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    MISSING = "missing"

    LABELS = {
        VALID: "Valid",
        EXPIRING: "Expiring soon",
        EXPIRED: "Expired",
        MISSING: "Not recorded",
    }


def expiry_status(expiry):
    if not expiry:
        return ExpiryStatus.MISSING
    days_left = (expiry - timezone.localdate()).days
    if days_left < 0:
        return ExpiryStatus.EXPIRED
    if days_left <= EXPIRY_WARN_DAYS:
        return ExpiryStatus.EXPIRING
    return ExpiryStatus.VALID


class Driver(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        INACTIVE = "inactive", "Inactive"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="driver_profile"
    )
    employee_number = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    licence_number = models.CharField(max_length=50)
    licence_class = models.CharField(max_length=30, help_text="Licence class/category as shown on the licence.")
    licence_expiry = models.DateField()

    is_armed_driver = models.BooleanField(default=False)
    armed_cert_number = models.CharField("armed-driver cert. number", max_length=50, blank=True)
    armed_cert_expiry = models.DateField("armed-driver cert. expiry", null=True, blank=True)

    authorized_vehicle_types = models.ManyToManyField(
        "vehicles.VehicleType", blank=True, related_name="authorized_drivers"
    )
    notes = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name", "user__username"]

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.user.get_full_name() or self.user.get_username()

    @property
    def licence_status(self):
        return expiry_status(self.licence_expiry)

    @property
    def licence_status_label(self):
        return ExpiryStatus.LABELS[self.licence_status]

    @property
    def armed_cert_status(self):
        if not self.is_armed_driver:
            return None
        return expiry_status(self.armed_cert_expiry)

    @property
    def armed_cert_status_label(self):
        status = self.armed_cert_status
        return ExpiryStatus.LABELS[status] if status else "n/a"

    def clean(self):
        if self.is_armed_driver and not self.armed_cert_expiry:
            raise ValidationError({"armed_cert_expiry": "Required for armed drivers."})

    def drive_blockers(self, vehicle):
        """Reasons this driver should not be assigned to `vehicle` (empty list = fine)."""
        reasons = []
        if self.status != self.Status.ACTIVE:
            reasons.append(f"Driver is {self.get_status_display().lower()}.")
        if self.licence_status in (ExpiryStatus.EXPIRED, ExpiryStatus.MISSING):
            reasons.append("Driver's licence is expired or not recorded.")
        if not self.authorized_vehicle_types.filter(pk=vehicle.vehicle_type_id).exists():
            reasons.append(f"Driver is not authorized for vehicle type: {vehicle.vehicle_type}.")
        return reasons

    @property
    def current_assignments(self):
        return self.assignments.filter(end_date__isnull=True).select_related("vehicle")


class VehicleAssignment(models.Model):
    """One row per stretch of time a driver has a vehicle. No end date = current."""

    vehicle = models.ForeignKey("vehicles.Vehicle", on_delete=models.PROTECT, related_name="assignments")
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name="assignments")
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank while the assignment is current.")
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-start_date", "-id"]

    def __str__(self):
        return f"{self.vehicle.fleet_number} -> {self.driver} ({self.start_date})"

    @property
    def is_current(self):
        return self.end_date is None

    def clean(self):
        if not (self.vehicle_id and self.driver_id):
            return
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before the start date."})

        # A vehicle can only have one driver at a time.
        overlapping = (
            VehicleAssignment.objects.filter(vehicle_id=self.vehicle_id)
            .exclude(pk=self.pk)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=self.start_date))
        )
        if self.end_date:
            overlapping = overlapping.filter(start_date__lte=self.end_date)
        if overlapping.exists():
            raise ValidationError("This vehicle already has an assignment that overlaps these dates.")

        # Eligibility is only enforced for current assignments, so old history can be entered freely.
        if self.end_date is None:
            blockers = self.driver.drive_blockers(self.vehicle)
            if self.vehicle.status == "retired":
                blockers.append("Vehicle is retired.")
            if blockers:
                raise ValidationError(blockers)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


