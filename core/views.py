import json
from datetime import timedelta

from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Servico, Cliente, Empregado, TipoServico, GastoExtra
from .forms import ClienteForm, ServicoForm, EmpregadoForm, TipoServicoForm, GastoExtraFormSet, AnexoServicoFormSet


def home(request):
    hoje = timezone.now()
    primeiro_dia_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    servicos_em_andamento = Servico.objects.filter(status='EM_ANDAMENTO').count()

    faturamento_mes = Servico.objects.filter(
        status='CONCLUIDO',
        data_competencia=primeiro_dia_mes,
    ).aggregate(total=Sum('valor_total'))['total'] or 0

    total_clientes = Cliente.objects.filter(ativo=True).count()
    km_total = Servico.objects.aggregate(total=Sum('km_rodado'))['total'] or 0

    status_map = dict(Servico.STATUS_POS)
    color_map = {
        'ORCAMENTO': '#0d6efd', 'AGENDADO': '#6f42c1',
        'EM_ANDAMENTO': '#fd7e14', 'CONCLUIDO': '#198754', 'CANCELADO': '#dc3545',
    }
    status_counts = dict(Servico.objects.values_list('status').annotate(count=Count('id')))
    status_labels = [status_map[k] for k, _ in Servico.STATUS_POS]
    status_values = [status_counts.get(k, 0) for k, _ in Servico.STATUS_POS]
    status_colors = [color_map[k] for k, _ in Servico.STATUS_POS]

    months = []
    for i in range(5, -1, -1):
        month_start = (primeiro_dia_mes - timedelta(days=i * 32)).replace(day=1)
        months.append(month_start)

    revenue_data = Servico.objects.filter(
        status='CONCLUIDO',
        data_competencia__gte=months[0],
    ).annotate(month=TruncMonth('data_competencia')).values('month').annotate(
        total=Sum('valor_total')
    ).order_by('month')

    revenue_by_month = {}
    for entry in revenue_data:
        em = entry['month']
        revenue_by_month[(em.year, em.month)] = float(entry['total'] or 0)

    month_labels = [m.strftime('%m/%Y') for m in months]
    month_values = [revenue_by_month.get((m.year, m.month), 0) for m in months]

    ultimos_servicos = Servico.objects.select_related(
        'cliente', 'tecnico', 'tipo_servico'
    ).order_by('-data_criacao')[:5]

    proximos_agendamentos = Servico.objects.filter(
        status='AGENDADO', data_inicio__gte=hoje,
    ).select_related('cliente', 'tecnico', 'tipo_servico').order_by('data_inicio')[:5]

    return render(request, 'dashboard.html', {
        'servicos_em_andamento': servicos_em_andamento,
        'faturamento_mes': faturamento_mes,
        'total_clientes': total_clientes,
        'km_total': km_total,
        'status_labels_json': json.dumps(status_labels),
        'status_values_json': json.dumps(status_values),
        'status_colors_json': json.dumps(status_colors),
        'month_labels_json': json.dumps(month_labels),
        'month_values_json': json.dumps(month_values),
        'ultimos_servicos': ultimos_servicos,
        'proximos_agendamentos': proximos_agendamentos,
    })


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
        formset_anexos = AnexoServicoFormSet(request.POST, request.FILES)
        if form.is_valid():
            servico = form.save()
            formset = GastoExtraFormSet(request.POST, instance=servico)
            formset_anexos = AnexoServicoFormSet(request.POST, request.FILES, instance=servico)
            if formset.is_valid() and formset_anexos.is_valid():
                formset.save()
                formset_anexos.save()
                servico.valor_total = servico.calcular_valor_total() + sum(g.valor for g in GastoExtra.objects.filter(servico=servico))
                servico.save(update_fields=["valor_total"])
            return redirect("home")
    else:
        form = ServicoForm()
        formset = GastoExtraFormSet()
        formset_anexos = AnexoServicoFormSet()
    return render(
        request,
        "formulario_servico.html",
        {
            "form": form,
            "formset": formset,
            "formset_anexos": formset_anexos,
            "titulo": "Novo Serviço",
            "rota_cancelar": "listar_servicos",
            "url_voltar": "listar_servicos",
        },
    )


def editar_servico(request, pk):
    servico = get_object_or_404(Servico, pk=pk)
    if request.method == "POST":
        form = ServicoForm(request.POST, instance=servico)
        formset = GastoExtraFormSet(request.POST, instance=servico)
        formset_anexos = AnexoServicoFormSet(request.POST, request.FILES, instance=servico)
        if form.is_valid() and formset.is_valid() and formset_anexos.is_valid():
            form.save()
            formset.save()
            formset_anexos.save()
            servico.valor_total = servico.calcular_valor_total() + sum(g.valor for g in GastoExtra.objects.filter(servico=servico))
            servico.save(update_fields=["valor_total"])
            return redirect("listar_servicos")
    else:
        form = ServicoForm(instance=servico)
        formset = GastoExtraFormSet(instance=servico)
        formset_anexos = AnexoServicoFormSet(instance=servico)

    return render(
        request,
        "formulario_servico.html",
        {
            "form": form,
            "formset": formset,
            "formset_anexos": formset_anexos,
            "titulo": f"Editar Serviço #{servico.pk}",
            "rota_cancelar": "listar_servicos",
            "url_voltar": "listar_servicos",
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


def detalhar_servico(request, pk):
    servico = get_object_or_404(Servico, pk=pk)
    gastos = servico.gastos_extras.all()
    anexos = servico.anexos.all()
    return render(
        request,
        "detalhar_servico.html",
        {
            "servico": servico,
            "gastos": gastos,
            "anexos": anexos,
            "titulo": f"Serviço #{servico.pk}",
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
