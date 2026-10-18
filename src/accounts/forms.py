from django import forms
from django.contrib.auth.forms import PasswordChangeForm


class MandatoryPasswordChangeForm(PasswordChangeForm):
    def clean_new_password(self):
        password = self.cleaned_data["new_password1"]

        if password == self.cleaned_data.get("old_password"):
            raise forms.ValidationError(
                    "Your new password must differ from your temporary password."
                    )
        return password
