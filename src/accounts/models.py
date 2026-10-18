from django.db import models
from django.conf import settings


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name



class Profile(models.Model):
    user = models.OneToOneField(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name="profile",
            )
    must_change_password = models.BooleanField(default=True)
    department = models.ForeignKey(
            Department,
            on_delete=models.PROTECT,
            null=True,
            blank=True,
            related_name="profiles",
        )
    title = models.CharField(max_length=100, blank=True)
    employee_id = models.CharField(
            max_length=30,
            blank=True,
            )
    phone_number = models.CharField(
            max_length=30,
            blank=True,
            )

    def __str__(self):
        return f"Profile: {self.username}"
