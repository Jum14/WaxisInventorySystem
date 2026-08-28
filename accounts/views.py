from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .decorators import role_required
from .forms import UserCreateForm
from .models import Profile


def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            if not user.is_active:
                messages.error(request, "This account is inactive.")
                return render(request, "accounts/login.html")

            login(request, user)
            return redirect_by_role(user)

        messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login.html")


def redirect_by_role(user):
    try:
        role = user.profile.role
    except Profile.DoesNotExist:
        return redirect("accounts:login")

    if role in {
        Profile.Role.DEVELOPER,
        Profile.Role.OWNER,
        Profile.Role.MANAGER,
        Profile.Role.CREW,
    }:
        return redirect("dashboard:home")

    return redirect("accounts:login")


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER)
def users(request):
    all_users = Profile.objects.select_related("user").order_by("user__username")

    return render(
        request,
        "accounts/users.html",
        {"users": [profile.user for profile in all_users]},
    )


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER)
def create_user(request):
    form = UserCreateForm(request.POST or None, actor=request.user)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(
            request,
            f"User '{user.username}' was created successfully.",
        )
        return redirect("accounts:users")

    return render(request, "accounts/user_form.html", {"form": form})


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER)
def toggle_user(request, user_id):
    from django.contrib.auth.models import User
    from django.shortcuts import get_object_or_404

    user = get_object_or_404(User, pk=user_id)

    if user == request.user:
        messages.error(request, "You cannot disable your own account.")
        return redirect("accounts:users")

    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])

    status = "activated" if user.is_active else "disabled"
    messages.success(request, f"User '{user.username}' has been {status}.")

    return redirect("accounts:users")
