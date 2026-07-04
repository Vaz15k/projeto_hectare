from django.contrib.auth import login as auth_login, logout as auth_logout
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django_ratelimit.decorators import ratelimit

from authentication.forms import LoginForm


def client_ip(request: HttpRequest) -> str:
    """Return the client IP supplied by Caddy, with a direct-request fallback."""
    return request.META.get("HTTP_X_REAL_IP") or request.META["REMOTE_ADDR"]


def login_account(_group: str, request: HttpRequest) -> str:
    """Normalize the submitted login before using it as a rate-limit key."""
    return request.POST.get("login", "").strip().casefold()


@ratelimit(
    group='login_ip',
    key='ip',
    rate='5/m',
    method='POST',
    block=True,
)
@ratelimit(
    group='login_account',
    key='authentication.views.login_account',
    rate='5/m',
    method='POST',
    block=True,
)
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
            if not url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                next_url = "home"
            return redirect(next_url)

    return render(request, "login.html", {"form": form})


def ratelimited_view(request, exception):
    """View amigável quando o rate-limit é atingido."""
    return render(
        request,
        "login.html",
        {
            "form": LoginForm(request=request),
            "ratelimited": True,
            "ratelimit_msg": (
                "Muitas tentativas de login. Por segurança, aguarde 1 minuto "
                "antes de tentar novamente."
            ),
        },
        status=429,
    )


def logout_view(request):
    """View de logout do sistema."""
    auth_logout(request)
    return redirect("login")
