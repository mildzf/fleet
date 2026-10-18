from django.shortcuts import redirect
from django.urls import reverse


class RequirePasswordChangeMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response


    def __call__(self, request):
        user = request.user 

        if user.is_authenticated and not user.is_superuser:
            try:
                must_change = user.profile.must_change_password
            except AttributeError:
                must_change = True

            if must_change:
                allowed_urls = {
                        reverse("accounts:login"),
                        reverse("accounts:logout"),
                        reverse("accounts:password_change"),
                        }
                if request.path not in allowed_urls:
                    return redirect("accounts:password_change")

        return self.get_response(request)
