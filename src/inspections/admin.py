from django.contrib import admin
from django.utils import timezone

from .models import ChecklistItem, DamagePoint, Inspection, InspectionResult


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_critical", "is_active", "sort_order")
    list_editable = ("is_critical", "is_active", "sort_order")
    list_filter = ("category", "is_active", "is_critical", "vehicle_types")
    search_fields = ("name", "category")
    filter_horizontal = ("vehicle_types",)


class ResultInline(admin.TabularInline):
    model = InspectionResult
    extra = 0
    fields = ("category", "item_name", "result", "notes", "is_critical")


class DamageInline(admin.TabularInline):
    model = DamagePoint
    extra = 0
    fields = ("view", "x", "y", "severity", "description", "photo", "status", "repaired_on")


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "inspection_type", "inspected_at", "inspected_by", "overall_condition", "unsafe_to_use")
    list_filter = ("inspection_type", "overall_condition", "unsafe_to_use")
    search_fields = ("vehicle__fleet_number", "vehicle__plate_number", "incident_reference")
    autocomplete_fields = ("vehicle",)
    raw_id_fields = ("driver", "inspected_by")
    date_hierarchy = "inspected_at"
    inlines = [ResultInline, DamageInline]


@admin.register(DamagePoint)
class DamagePointAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "view", "severity", "description", "status", "created", "repaired_on")
    list_filter = ("status", "severity", "view")
    search_fields = ("vehicle__fleet_number", "vehicle__plate_number", "description")
    actions = ["mark_repaired"]

    @admin.action(description="Mark selected damage as repaired today")
    def mark_repaired(self, request, queryset):
        count = queryset.filter(status=DamagePoint.Status.OPEN).update(
            status=DamagePoint.Status.REPAIRED, repaired_on=timezone.localdate()
        )
        self.message_user(request, f"Marked {count} item(s) repaired.")
