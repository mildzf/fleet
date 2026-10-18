from django.urls import path

from . import views

app_name = "drivers"

urlpatterns = [
    path("", views.DriverListView.as_view(), name="list"),
    path("<int:pk>/", views.DriverDetailView.as_view(), name="detail"),
]
