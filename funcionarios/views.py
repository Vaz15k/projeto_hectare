from django.shortcuts import render, redirect, get_object_or_404
from funcionarios.models import Empregado
from funcionarios.forms import EmpregadoForm


def criar_empregado(request):
    if request.method == "POST":
        form = EmpregadoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("listar_empregados")
    else:
        form = EmpregadoForm()
    return render(
        request,
        "formulario_generico.html",
        {
            "form": form,
            "titulo": "Novo Empregado",
            "rota_cancelar": "listar_empregados",
            "url_voltar": "listar_empregados",
        },
    )


def listar_empregados(request):
    empregados = Empregado.objects.all().order_by("nome")
    return render(
        request,
        "listar_generico.html",
        {
            "titulo": "👩‍🔧 Empregados",
            "url_criar": "criar_empregado",
            "linhas_partial": "partials/linhas_empregados.html",
            "itens": empregados,
            "colunas": ["Nome", "CPF", "Cargo"],
        },
    )


def editar_empregado(request, pk):
    empregado = get_object_or_404(Empregado, pk=pk)
    if request.method == "POST":
        form = EmpregadoForm(request.POST, instance=empregado)
        if form.is_valid():
            form.save()
            return redirect("listar_empregados")
    else:
        form = EmpregadoForm(instance=empregado)

    return render(
        request,
        "formulario_generico.html",
        {
            "form": form,
            "titulo": f"Editar Empregado {empregado.nome}",
            "rota_cancelar": "listar_empregados",
            "url_voltar": "listar_empregados",
            "submit_label": "Atualizar",
        },
    )
