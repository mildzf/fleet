from django.urls import path

from . import views

app_name = "vehicles"

urlpatterns = [
    path("", views.VehicleListView.as_view(), name="list"),
    path("<int:pk>/", views.VehicleDetailView.as_view(), name="detail"),
]
