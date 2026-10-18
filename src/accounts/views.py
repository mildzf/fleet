from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from .forms import MandatoryPasswordChangeForm


class MandatoryPasswordChangeView(PasswordChangeView):
    form_class = MandatoryPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("core:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)

        profile = self.request.user.profile
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password"])

        update_session_auth_hash(
                self.request,
                self.request.user,
                )
        return response


