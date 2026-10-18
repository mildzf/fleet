from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse 

from .models import Department, Profile

User = get_user_model()


class PasswordChangeSecurityTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
                username="testemployee",
                password="TempPass!483",
                )
        self.profile = self.user.profile



    def test_new_user_must_change_password(self):
        self.assertTrue(self.profile.must_change_password)

    def test_temporary_password_cannot_access_dashboard(self):
        self.client.login(
                username="testemployee",
                password="TempPass!483",
                )
        response = self.client.get(
                reverse("core:dashboard"),
                )
        self.assertRedirects(
                response,
                reverse("accounts:password_change"),
                )

    def test_password_change_page_is_accessible(self):
        self.client.login(
                username="testemployee",
                password="TempPass!483",
                )
        response = self.client.get(
                reverse("accounts:password_change"),
                )
        self.assertEqual(response.status_code, 200)

    def test_password_change_flag_is_cleared_after_change(self):
        self.client.login(
                username="testemployee",
                password="TempPass!483",
                )
        response = self.client.post(
                reverse("accounts:password_change"),
                {
                    "old_password": "TempPass!483",
                    "new_password1": "NewSecurePass!9274",
                    "new_password2": "NewSecurePass!9274",
                },
            )
        self.assertEqual(response.status_code, 302)

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.must_change_password)

    def test_logged_out_user_cannot_access_dashboard(self):
        self.client.logout()
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_can_login_with_new_password_after_change(self):
        self.client.login(username="testemployee", password="TempPass!483")
        self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "TempPass!483",
                "new_password1": "NewSecurePass!9274",
                "new_password2": "NewSecurePass!9274",
            },
        )
        self.client.logout()

        self.assertTrue(
            self.client.login(
                username="testemployee",
                password="NewSecurePass!9274",
            )
        )
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_old_temporary_password_stops_working(self):
        self.client.login(username="testemployee", password="TempPass!483")
        self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "TempPass!483",
                "new_password1": "NewSecurePass!9274",
                "new_password2": "NewSecurePass!9274",
            },
        )
        self.client.logout()

        self.assertFalse(
            self.client.login(
                username="testemployee",
                password="TempPass!483",
            )
        )

    def test_weak_password_is_rejected_and_flag_stays_set(self):
        self.client.login(username="testemployee", password="TempPass!483")
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "TempPass!483",
                "new_password1": "12345678",
                "new_password2": "12345678",
            },
        )
        self.assertEqual(response.status_code, 200)  # form re-rendered
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.must_change_password)

    def test_wrong_old_password_is_rejected(self):
        self.client.login(username="testemployee", password="TempPass!483")
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "WrongPass!000",
                "new_password1": "NewSecurePass!9274",
                "new_password2": "NewSecurePass!9274",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.must_change_password)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        self.assertFalse(
            self.client.login(
                username="testemployee",
                password="TempPass!483",
            )
        )

    def test_public_registration_is_not_available(self):
        for path in ["/register/", "/signup/", "/accounts/register/", "/accounts/signup/"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404, msg=path)


    def test_other_pages_blocked_while_flag_set(self):
        self.client.login(username="testemployee", password="TempPass!483")
        # replace with your real protected URL names
        for name in ["core:dashboard"]:
            response = self.client.get(reverse(name))
            self.assertRedirects(response, reverse("accounts:password_change"))

    def test_user_without_profile_does_not_crash(self):
        self.profile.delete()
        self.client.login(username="testemployee", password="TempPass!483")
        response = self.client.get(reverse("core:dashboard"))
        self.assertIn(response.status_code, (200, 302))


    def test_profile_can_have_department_and_title(self):
        dept = Department.objects.create(name="Duty Office")
        self.profile.department = dept
        self.profile.title = "Duty Officer"
        self.profile.save()

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.department, dept)
        self.assertEqual(self.profile.title, "Duty Officer")

    def test_department_is_optional(self):
        self.assertIsNone(self.profile.department)

    def test_department_in_use_cannot_be_deleted(self):
        from django.db.models import ProtectedError

        dept = Department.objects.create(name="Garage")
        self.profile.department = dept
        self.profile.save()

        with self.assertRaises(ProtectedError):
            dept.delete()

    def test_department_names_are_unique(self):
        from django.db import IntegrityError

        Department.objects.create(name="Accounts")
        with self.assertRaises(IntegrityError):
            Department.objects.create(name="Accounts")
