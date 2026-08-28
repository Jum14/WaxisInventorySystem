from django.urls import path

from .views import create_user, login_view, logout_view, toggle_user, users

app_name = "accounts"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("users/", users, name="users"),
    path("users/create/", create_user, name="create_user"),
    path("users/<int:user_id>/toggle/", toggle_user, name="toggle_user"),
]
