from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

from .models import Driver


class DriverListView(LoginRequiredMixin, ListView):
    model = Driver
    template_name = "drivers/driver_list.html"
    context_object_name = "drivers"

    def get_queryset(self):
        return Driver.objects.select_related("user")


class DriverDetailView(LoginRequiredMixin, DetailView):
    model = Driver
    template_name = "drivers/driver_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["history"] = self.object.assignments.select_related("vehicle")
        ctx["authorized_types"] = self.object.authorized_vehicle_types.all()
        return ctx
