from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),

    path("logout/", views.logout_view, name="logout"),
    path("ai/", views.ai_page, name="ai_page"),
    path("profile_page/", views.profile_page, name="profile_page"),
    path("add-crop/", views.add_crop, name="add_crop"),
    path("logs/crop/<int:crop_id>/", views.crop_activity_log, name="crop_activity_log"),
    path("prices_page/", views.prices_page, name="prices_page"),
]