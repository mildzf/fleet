from django.contrib import admin
from django.utils import timezone

from .models import Driver, VehicleAssignment


class AssignmentInline(admin.TabularInline):
    model = VehicleAssignment
    extra = 0
    autocomplete_fields = ("vehicle",)
    fields = ("vehicle", "start_date", "end_date", "notes")


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("name", "employee_number", "status", "licence_class", "licence_expiry", "licence_status_label", "is_armed_driver", "armed_cert_status_label")
    list_filter = ("status", "is_armed_driver", "licence_class", "authorized_vehicle_types")
    search_fields = ("user__username", "user__first_name", "user__last_name", "employee_number", "licence_number")
    raw_id_fields = ("user",)
    filter_horizontal = ("authorized_vehicle_types",)
    inlines = [AssignmentInline]

    @admin.display(description="Licence")
    def licence_status_label(self, obj):
        return obj.licence_status_label

    @admin.display(description="Armed cert.")
    def armed_cert_status_label(self, obj):
        return obj.armed_cert_status_label


@admin.register(VehicleAssignment)
class VehicleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "driver", "start_date", "end_date", "assigned_by")
    list_filter = ("end_date",)
    search_fields = ("vehicle__fleet_number", "vehicle__plate_number", "driver__user__username", "driver__user__last_name")
    autocomplete_fields = ("vehicle", "driver")
    date_hierarchy = "start_date"
    actions = ["end_today"]

    def save_model(self, request, obj, form, change):
        if not change and not obj.assigned_by_id:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="End selected assignments today")
    def end_today(self, request, queryset):
        today = timezone.localdate()
        updated = 0
        for a in queryset.filter(end_date__isnull=True):
            a.end_date = today
            a.save()
            updated += 1
        self.message_user(request, f"Ended {updated} assignment(s).")
