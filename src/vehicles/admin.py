from django.contrib import admin

from .models import ServiceRecord, ServiceType, Vehicle, VehicleType


class ServiceRecordInline(admin.TabularInline):
    model = ServiceRecord
    extra = 0
    fields = ("service_type", "performed_on", "odometer_at_service", "performed_by", "cost", "next_due_date", "next_due_odometer")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("fleet_number", "plate_number", "make", "model", "vehicle_type", "status", "condition", "service_status_label", "current_driver")
    list_filter = ("status", "condition", "vehicle_type", "is_armored")
    search_fields = ("fleet_number", "plate_number", "vin", "make", "model")
    inlines = [ServiceRecordInline]

    @admin.display(description="Service")
    def service_status_label(self, obj):
        return obj.service_status_label

    @admin.display(description="Driver")
    def current_driver(self, obj):
        return obj.current_driver or "-"


@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "service_type", "performed_on", "odometer_at_service", "next_due_date", "next_due_odometer")
    list_filter = ("service_type",)
    search_fields = ("vehicle__fleet_number", "vehicle__plate_number", "reference")


admin.site.register(VehicleType)
admin.site.register(ServiceType)
