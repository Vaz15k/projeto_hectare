from django.shortcuts import render, redirect
from core.models import Configuracao
from core.forms import ConfiguracaoForm


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
