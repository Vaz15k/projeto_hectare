from django.shortcuts import render, redirect, get_object_or_404
from .models import Servico, Cliente, Empregado, TipoServico
from .forms import ClienteForm, ServicoForm, EmpregadoForm, TipoServicoForm, GastoExtraFormSet


def home(request):
    servicos = Servico.objects.all().order_by("-data_inicio")
    return render(
        request,
        "listar_generico.html",
        {
            "titulo": "🛠️ Ordens de Serviço",
            "url_criar": "criar_servico",
            "botao_novo": "+ Nova OS",
            "linhas_partial": "partials/linhas_servicos.html",
            "itens": servicos,
            "colunas": ["#", "Tipo", "Cliente", "Técnico", "Status", "Início", "Total"],
        },
    )


def criar_tipo_servico(request):
    if request.method == "POST":
        form = TipoServicoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("listar_tipos_servico")
    else:
        form = TipoServicoForm()
    return render(
        request,
        "formulario_generico.html",
        {
            "form": form,
            "titulo": "Novo Tipo de Serviço",
            "rota_cancelar": "listar_tipos_servico",
            "url_voltar": "listar_tipos_servico",
        },
    )


def listar_tipos_servico(request):
    from .models import TipoServico

    tipos_servico = TipoServico.objects.all().order_by("nome")
    return render(
        request,
        "listar_generico.html",
        {
            "titulo": "📝 Tipos de Serviço",
            "url_criar": "criar_tipo_servico",
            "linhas_partial": "partials/linhas_tipos_servico.html",
            "itens": tipos_servico,
            "colunas": ["Nome", "Descrição"],
        },
    )


def editar_tipo_servico(request, pk):
    tipo_servico = get_object_or_404(TipoServico, pk=pk)
    if request.method == "POST":
        form = TipoServicoForm(request.POST, instance=tipo_servico)
        if form.is_valid():
            form.save()
            return redirect("listar_tipos_servico")
    else:
        form = TipoServicoForm(instance=tipo_servico)

    return render(
        request,
        "formulario_generico.html",
        {
            "form": form,
            "titulo": f"Editar Tipo de Serviço {tipo_servico.nome}",
            "rota_cancelar": "listar_tipos_servico",
            "url_voltar": "listar_tipos_servico",
            "submit_label": "Atualizar",
        },
    )


# --------- Empregado Views ---------


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


# --------- Servico Views ---------


def listar_servicos(request):
    servicos = Servico.objects.all().order_by("-data_inicio")
    return render(
        request,
        "listar_generico.html",
        {
            "titulo": "🛠️ Serviços",
            "url_criar": "criar_servico",
            "linhas_partial": "partials/linhas_servicos.html",
            "itens": servicos,
            "colunas": ["#", "Tipo", "Cliente", "Técnico", "Status", "Início", "Total"],
        },
    )


def criar_servico(request):
    if request.method == "POST":
        form = ServicoForm(request.POST)
        formset = GastoExtraFormSet(request.POST)
        if form.is_valid():
            servico = form.save()
            formset = GastoExtraFormSet(request.POST, instance=servico)
            if formset.is_valid():
                formset.save()
                servico.valor_total = servico.calcular_valor_total() + sum(g.valor for g in servico.gastos_extras.all())
                servico.save(update_fields=["valor_total"])
            return redirect("home")
    else:
        form = ServicoForm()
        formset = GastoExtraFormSet()
    return render(
        request,
        "formulario_servico.html",
        {
            "form": form,
            "formset": formset,
            "titulo": "Novo Serviço",
            "rota_cancelar": "listar_servicos",
            "url_voltar": "listar_servicos",
            "container_style": "max-width: 900px;",
        },
    )


def editar_servico(request, pk):
    servico = get_object_or_404(Servico, pk=pk)
    if request.method == "POST":
        form = ServicoForm(request.POST, instance=servico)
        formset = GastoExtraFormSet(request.POST, instance=servico)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            servico.valor_total = servico.calcular_valor_total() + sum(g.valor for g in servico.gastos_extras.all())
            servico.save(update_fields=["valor_total"])
            return redirect("listar_servicos")
    else:
        form = ServicoForm(instance=servico)
        formset = GastoExtraFormSet(instance=servico)

    return render(
        request,
        "formulario_servico.html",
        {
            "form": form,
            "formset": formset,
            "titulo": f"Editar Serviço #{servico.pk}",
            "rota_cancelar": "listar_servicos",
            "url_voltar": "listar_servicos",
            "container_style": "max-width: 900px;",
            "submit_label": "Atualizar",
        },
    )


def deletar_servico(request, pk):
    """Exibe confirmação e remove o serviço após POST."""
    servico = get_object_or_404(Servico, pk=pk)
    if request.method == "POST":
        servico.delete()
        return redirect("listar_servicos")

    return render(
        request,
        "confirm_delete.html",
        {
            "obj": servico,
            "titulo": f"Deletar Serviço #{servico.pk}",
            "cancel_url": "listar_servicos",
        },
    )


# --------- Cliente Views ---------


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
