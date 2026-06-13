from django.contrib.auth import login as auth_login, logout as auth_logout
from django.shortcuts import render, redirect
from authentication.forms import LoginForm


def login_view(request):
    """
    View de login do sistema.
    Redireciona para home se o usuário já estiver autenticado.
    """
    if request.user.is_authenticated:
        return redirect("home")

    form = LoginForm(request=request)
    if request.method == "POST":
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            auth_login(request, form.get_user())
            next_url = request.GET.get("next", "home")
            return redirect(next_url)

    return render(request, "login.html", {"form": form})


def logout_view(request):
    """View de logout do sistema."""
    auth_logout(request)
    return redirect("login")
