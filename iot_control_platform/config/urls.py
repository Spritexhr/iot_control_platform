from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .api_views import mqtt_status, dashboard_stats
from .auth_views import register, user_profile, change_password

urlpatterns = [
    path("admin/", admin.site.urls),

    # 用户认证 API
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/register/", register, name="register"),
    path("api/auth/profile/", user_profile, name="user-profile"),
    path("api/auth/change-password/", change_password, name="change-password"),

    # REST API
    path("api/", include("sensors.urls")),
    path("api/", include("devices.urls")),
    path("api/", include("automation.urls")),
    path("api/mqtt/status/", mqtt_status, name="mqtt-status"),
    path("api/dashboard/stats/", dashboard_stats, name="dashboard-stats"),
]
