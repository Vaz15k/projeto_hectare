from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_safe

from core.forms import ConfiguracaoForm
from core.models import Configuracao


@login_required
@require_safe
def protected_media(request, path):
    """Serve arquivos de mídia somente para usuários autenticados."""
    media_root = Path(settings.MEDIA_ROOT).resolve()

    try:
        file_path = (media_root / path).resolve()
        file_path.relative_to(media_root)
        if not file_path.is_file():
            raise Http404("Arquivo não encontrado")
        file_handle = file_path.open("rb")
    except (OSError, RuntimeError, ValueError):
        raise Http404("Arquivo não encontrado") from None

    response = FileResponse(file_handle, as_attachment=False, filename=file_path.name)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


@login_required
def editar_configuracoes(request):
    config = Configuracao.load()
    if request.method == "POST":
        form = ConfiguracaoForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            return redirect("editar_configuracoes")
    else:
        form = ConfiguracaoForm(instance=config)

    return render(
        request,
        "configuracoes.html",
        {
            "form": form,
            "config": config,
            "titulo": "Configurações",
        },
    )
