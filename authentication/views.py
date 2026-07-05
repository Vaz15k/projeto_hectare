from django.contrib.auth import login as auth_login, logout as auth_logout
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from authentication.forms import LoginForm


def client_ip(request: HttpRequest) -> str:
    """Return the client IP supplied by Caddy, with a direct-request fallback."""
    return request.META.get("HTTP_X_REAL_IP") or request.META["REMOTE_ADDR"]


def login_account(_group: str, request: HttpRequest) -> str:
    """Normalize the submitted login before using it as a rate-limit key.

    O form principal envia o campo "login"; o form do Django Admin envia
    "username". Ambos alimentam o mesmo contador por conta.
    """
    login = request.POST.get("login") or request.POST.get("username") or ""
    return login.strip().casefold()


def login_ratelimit(view):
    """Aplica os limites de tentativas de login (por IP e por conta).

    Usado tanto na tela de login principal quanto no login do Django Admin,
    compartilhando os mesmos grupos para que os contadores sejam únicos.
    """
    view = ratelimit(
        group='login_account',
        key='authentication.views.login_account',
        rate='5/m',
        method='POST',
        block=True,
    )(view)
    view = ratelimit(
        group='login_ip',
        key='ip',
        rate='5/m',
        method='POST',
        block=True,
    )(view)
    return view


@login_ratelimit
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


@require_POST
def logout_view(request):
    """View de logout do sistema.

    Aceita apenas POST (com CSRF) para impedir logout forçado por
    requisições GET disparadas por sites externos.
    """
    auth_logout(request)
    return redirect("login")
