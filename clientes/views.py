from django.shortcuts import render, redirect, get_object_or_404
from clientes.models import Cliente
from clientes.forms import ClienteForm, MaquinaInlineFormSet


def listar_clientes(request):
    clientes = Cliente.objects.all().order_by("nome")
    return render(
        request,
        "listar_generico.html",
        {
            "titulo": "👥 Clientes",
            "url_criar": "criar_cliente",
            "linhas_partial": "partials/linhas_clientes.html",
            "itens": clientes,
            "colunas": ["Nome", "Telefone", "Email", "Documento"],
        },
    )


def criar_cliente(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("home")
    else:
        form = ClienteForm()
    return render(
        request,
        "formulario_generico.html",
        {
            "form": form,
            "titulo": "Novo Cliente",
            "rota_cancelar": "listar_clientes",
            "url_voltar": "listar_clientes",
        },
    )


def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect("listar_clientes")
    else:
        form = ClienteForm(instance=cliente)

    return render(
        request,
        "formulario_generico.html",
        {
            "form": form,
            "titulo": f"Editar Cliente {cliente.nome}",
            "rota_cancelar": "listar_clientes",
            "url_voltar": "listar_clientes",
            "submit_label": "Atualizar",
        },
    )


def maquinas_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        formset_maquinas = MaquinaInlineFormSet(request.POST, request.FILES, instance=cliente)
        if formset_maquinas.is_valid():
            formset_maquinas.save()
            return redirect("listar_clientes")
    else:
        formset_maquinas = MaquinaInlineFormSet(instance=cliente)

    return render(
        request,
        "maquinas_cliente.html",
        {
            "formset_maquinas": formset_maquinas,
            "titulo": f"Máquinas de {cliente.nome}",
            "cliente": cliente,
        },
    )
