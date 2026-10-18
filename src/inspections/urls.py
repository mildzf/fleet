from django.urls import path

from . import views

app_name = "inspections"

urlpatterns = [
    path("", views.inspection_list, name="list"),
    path("new/", views.start, name="start"),
    path("new/<int:vehicle_pk>/", views.inspection_create, name="new"),
    path("<int:pk>/", views.inspection_detail, name="detail"),
    path("vehicle/<int:vehicle_pk>/", views.vehicle_history, name="vehicle"),
    path("damage/<int:pk>/repaired/", views.damage_repaired, name="damage_repaired"),
]
