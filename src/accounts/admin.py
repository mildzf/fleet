from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Profile

User = get_user_model()


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
            "user",
            "employee_id",
            "phone_number",
            "must_change_password",
            )
    list_filter = ("must_change_password",)
    search_fields = (
            "user__username",
            "user__first_name",
            "user__last_name",
            "employee_id",
            )
    readonly_fields = ("user",)



admin.site.site_header = "Guardsman St. Lucia Fleet management Administration"
admin.site.site_title = "Guardsman Admin"
admin.site.index_title = "Administration"
