from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [

    path("login/", auth_views.LoginView.as_view(
        template_name="accounts/login.html",
        redirect_authenticated_user=True),
        name="login"),

    path("logout/", auth_views.LogoutView.as_view(
        next_page="accounts:login"),
        name="logout"),

    path("dashboard/", views.dashboard, name="dashboard"),

    path("daily-insights/", views.daily_insights, name="daily_insights"),
    path("operational-analytics/", views.operational_analytics, name="operational_analytics"),

    path("ticket/update/<int:ticket_id>/", views.update_ticket_status, name="update_ticket"),
    path("ticket/delete/<int:ticket_id>/", views.delete_ticket, name="delete_ticket"),

    path("audit-logs/", views.audit_logs, name="audit_logs"),

    path("admin-manage/", views.manage_masters, name="admin_manage"),
    path("admin-manage/locations/", views.manage_masters, name="manage_masters"),
    path("admin-manage/users/", views.manage_users, name="manage_users"),
    path("admin-manage/groups/", views.manage_groups, name="manage_groups"),
]