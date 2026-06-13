import json
import os
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.template.loader import render_to_string
from django.http import HttpResponse

from xhtml2pdf import pisa

from servicos.models import Servico, TipoServico, GastoExtra, PecaUtilizada
from servicos.forms import (
    ServicoForm, TipoServicoForm,
    GastoExtraFormSet, AnexoServicoFormSet, PecaUtilizadaFormSet,
)
from clientes.models import Cliente, Maquina
from core.models import Configuracao


# ---------------------------------------------------------------------------
# Filtro compartilhado
# ---------------------------------------------------------------------------

def _build_filtro_ctx(request):
    mes = request.GET.get('mes', '')
    tipo_servico_id = request.GET.get('tipo_servico', '')
    status = request.GET.get('status', '')

    meses_disponiveis = Servico.objects.dates('data_competencia', 'month', order='DESC')
    tipos_servico = TipoServico.objects.all()

    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()

    ctx = {
        'mes_selecionado': mes,
        'tipo_servico_selecionado': str(tipo_servico_id) if tipo_servico_id else '',
        'status_selecionado': status,
        'meses_disponiveis': [
            {'value': m.strftime('%Y-%m'), 'label': m.strftime('%m/%Y')}
            for m in meses_disponiveis
        ],
        'tipos_servico': tipos_servico,
        'status_opcoes': Servico.STATUS_POS,
        'tem_filtros': bool(mes or tipo_servico_id or status),
        'query_string': query_string,
    }

    def aplicar(qs, excluir_mes=False, excluir_status=False):
        if mes and not excluir_mes:
            try:
                y, m = map(int, mes.split('-'))
                qs = qs.filter(data_competencia__year=y, data_competencia__month=m)
            except (ValueError, TypeError):
                pass
        if tipo_servico_id:
            try:
                qs = qs.filter(tipo_servico_id=int(tipo_servico_id))
            except (ValueError, TypeError):
                pass
        if status and not excluir_status:
            qs = qs.filter(status=status)
        return qs

    return ctx, aplicar


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def home(request):
    hoje = timezone.now()
    primeiro_dia_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    filtro_ctx, aplicar_filtro = _build_filtro_ctx(request)
    base = aplicar_filtro(Servico.objects.all())

    mes_ref = primeiro_dia_mes
    if filtro_ctx['mes_selecionado']:
        try:
            y, m = map(int, filtro_ctx['mes_selecionado'].split('-'))
            mes_ref = datetime(y, m, 1, tzinfo=primeiro_dia_mes.tzinfo)
        except (ValueError, TypeError):
            pass

    servicos_em_andamento = base.filter(status='EM_ANDAMENTO').count()

    faturamento_mes = base.filter(
        status='CONCLUIDO',
        data_competencia=mes_ref,
    ).aggregate(total=Sum('valor_total'))['total'] or 0

    clientes_base = Cliente.objects.all()
    total_clientes = clientes_base.filter(ativo=True).count()
    km_total = base.aggregate(total=Sum('km_rodado'))['total'] or 0

    status_map = dict(Servico.STATUS_POS)
    color_map = {
        'ORCAMENTO': '#0d6efd', 'AGENDADO': '#6f42c1',
        'EM_ANDAMENTO': '#fd7e14', 'CONCLUIDO': '#198754', 'CANCELADO': '#dc3545',
    }

    status_qs = aplicar_filtro(Servico.objects.all(), excluir_status=True)
    status_counts = dict(status_qs.values_list('status').annotate(count=Count('id')))
    status_labels = [status_map[k] for k, _ in Servico.STATUS_POS]
    status_values = [status_counts.get(k, 0) for k, _ in Servico.STATUS_POS]
    status_colors = [color_map[k] for k, _ in Servico.STATUS_POS]

    months = []
    for i in range(5, -1, -1):
        months.append((mes_ref - timedelta(days=i * 32)).replace(day=1))

    revenue_qs = aplicar_filtro(Servico.objects.all(), excluir_mes=True)
    revenue_data = revenue_qs.filter(
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

    ultimos_servicos = base.select_related(
        'cliente', 'tecnico', 'tipo_servico'
    ).order_by('-data_criacao')[:5]

    proximos_agendamentos = base.filter(
        status='AGENDADO', data_inicio__gte=hoje,
    ).select_related('cliente', 'tecnico', 'tipo_servico').order_by('data_inicio')[:5]

    return render(request, 'dashboard.html', {
        **filtro_ctx,
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


# ---------------------------------------------------------------------------
# Tipo de Serviço
# ---------------------------------------------------------------------------

def criar_tipo_servico(request):
    if request.method == "POST":
        form = TipoServicoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("listar_tipos_servico")
    else:
        form = TipoServicoForm()
    return render(
        request, "formulario_generico.html",
        {
            "form": form,
            "titulo": "Novo Tipo de Serviço",
            "rota_cancelar": "listar_tipos_servico",
            "url_voltar": "listar_tipos_servico",
        },
    )


def listar_tipos_servico(request):
    tipos_servico = TipoServico.objects.all().order_by("nome")
    return render(
        request, "listar_generico.html",
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
        request, "formulario_generico.html",
        {
            "form": form,
            "titulo": f"Editar Tipo de Serviço {tipo_servico.nome}",
            "rota_cancelar": "listar_tipos_servico",
            "url_voltar": "listar_tipos_servico",
            "submit_label": "Atualizar",
        },
    )


# ---------------------------------------------------------------------------
# Serviço CRUD
# ---------------------------------------------------------------------------

def listar_servicos(request):
    from django.core.paginator import Paginator

    filtro_ctx, aplicar_filtro = _build_filtro_ctx(request)
    servicos = aplicar_filtro(Servico.objects.all()).order_by('-data_inicio')

    paginator = Paginator(servicos, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(
        request, 'listar_generico.html',
        {
            **filtro_ctx,
            'titulo': 'Serviços',
            'url_criar': 'criar_servico',
            'linhas_partial': 'partials/linhas_servicos.html',
            'itens': page_obj,
            'colunas': ['#', 'Tipo', 'Cliente', 'Técnico', 'Status', 'Início', 'Total'],
            'mostrar_filtros': True,
        },
    )


def criar_servico(request):
    if request.method == "POST":
        form = ServicoForm(request.POST)
        formset = GastoExtraFormSet(request.POST)
        formset_pecas = PecaUtilizadaFormSet(request.POST)
        formset_anexos = AnexoServicoFormSet(request.POST, request.FILES)
        if form.is_valid():
            servico = form.save()
            formset = GastoExtraFormSet(request.POST, instance=servico)
            formset_pecas = PecaUtilizadaFormSet(request.POST, instance=servico)
            formset_anexos = AnexoServicoFormSet(request.POST, request.FILES, instance=servico)
            if formset.is_valid() and formset_pecas.is_valid() and formset_anexos.is_valid():
                formset.save()
                formset_pecas.save()
                formset_anexos.save()
                servico.valor_total = (
                    servico.calcular_valor_total()
                    + sum(g.valor for g in GastoExtra.objects.filter(servico=servico))
                    + sum(p.valor_total for p in PecaUtilizada.objects.filter(servico=servico))
                )
                servico.save(update_fields=["valor_total"])
            return redirect("home")
    else:
        form = ServicoForm()
        formset = GastoExtraFormSet()
        formset_pecas = PecaUtilizadaFormSet()
        formset_anexos = AnexoServicoFormSet()

    if request.method == "POST":
        maquinas_selecionadas = set(int(pk) for pk in request.POST.getlist("maquinas") if pk)
    else:
        maquinas_selecionadas = set(
            form.initial.get("maquinas", Maquina.objects.none()).values_list("pk", flat=True)
        )

    return render(
        request, "formulario_servico.html",
        {
            "form": form,
            "formset": formset,
            "formset_pecas": formset_pecas,
            "formset_anexos": formset_anexos,
            "maquinas_selecionadas": maquinas_selecionadas,
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
        formset_pecas = PecaUtilizadaFormSet(request.POST, instance=servico)
        formset_anexos = AnexoServicoFormSet(request.POST, request.FILES, instance=servico)
        if form.is_valid() and formset.is_valid() and formset_pecas.is_valid() and formset_anexos.is_valid():
            form.save()
            formset.save()
            formset_pecas.save()
            formset_anexos.save()
            servico.valor_total = (
                servico.calcular_valor_total()
                + sum(g.valor for g in GastoExtra.objects.filter(servico=servico))
                + sum(p.valor_total for p in PecaUtilizada.objects.filter(servico=servico))
            )
            servico.save(update_fields=["valor_total"])
            return redirect("listar_servicos")
    else:
        form = ServicoForm(instance=servico)
        formset = GastoExtraFormSet(instance=servico)
        formset_pecas = PecaUtilizadaFormSet(instance=servico)
        formset_anexos = AnexoServicoFormSet(instance=servico)

    if request.method == "POST":
        maquinas_selecionadas = set(int(pk) for pk in request.POST.getlist("maquinas") if pk)
    else:
        maquinas_selecionadas = set(servico.maquinas.values_list("pk", flat=True))

    return render(
        request, "formulario_servico.html",
        {
            "form": form,
            "formset": formset,
            "formset_pecas": formset_pecas,
            "formset_anexos": formset_anexos,
            "maquinas_selecionadas": maquinas_selecionadas,
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
        request, "confirm_delete.html",
        {
            "obj": servico,
            "titulo": f"Deletar Serviço #{servico.pk}",
            "cancel_url": "listar_servicos",
        },
    )


def detalhar_servico(request, pk):
    servico = get_object_or_404(Servico, pk=pk)
    gastos = servico.gastos_extras.all()
    pecas = servico.pecas.all()
    anexos = servico.anexos.all()
    return render(
        request, "detalhar_servico.html",
        {
            "servico": servico,
            "gastos": gastos,
            "pecas": pecas,
            "anexos": anexos,
            "titulo": f"Serviço #{servico.pk}",
        },
    )


# ---------------------------------------------------------------------------
# Exportar PDF
# ---------------------------------------------------------------------------

def _link_callback(uri, rel):
    from django.conf import settings

    if os.path.isfile(uri):
        return uri

    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ''))
    elif uri.startswith(settings.STATIC_URL):
        path = os.path.join(
            settings.STATIC_ROOT or os.path.join(settings.BASE_DIR, 'static'),
            uri.replace(settings.STATIC_URL, '')
        )
    elif uri.startswith('/'):
        path = os.path.join(settings.MEDIA_ROOT, uri.lstrip('/'))
    else:
        return uri

    if not os.path.isfile(path):
        return uri

    return path


def _gerar_payload_pix(chave_pix, nome_beneficiario, cidade, valor, txid='***'):
    import crcmod

    valor_formatado = f"{float(valor):.2f}" if valor else "0.00"

    if chave_pix.isdigit() and len(chave_pix) == 11:
        chave_pix = f"+55{chave_pix}"
    elif chave_pix.isdigit() and len(chave_pix) == 10:
        chave_pix = f"+55{chave_pix}"

    payload = "000201"

    gui = "0014BR.GOV.BCB.PIX"
    chave = f"01{len(chave_pix):02d}{chave_pix}"
    merchant_info = gui + chave
    payload += f"26{len(merchant_info):02d}{merchant_info}"

    payload += "52040000"
    payload += "5303986"
    payload += f"54{len(valor_formatado):02d}{valor_formatado}"
    payload += "5802BR"
    payload += f"59{len(nome_beneficiario):02d}{nome_beneficiario[:25]}"
    payload += f"60{len(cidade):02d}{cidade[:15]}"

    txid_block = f"05{len(txid):02d}{txid}"
    payload += f"62{len(txid_block):02d}{txid_block}"

    payload_com_crc = payload + "6304"

    crc16 = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
    crc_calculado = hex(crc16(payload_com_crc.encode('utf-8')))[2:].upper().zfill(4)

    return payload_com_crc + crc_calculado


def _gerar_qrcode_pix(chave_pix, nome_empresa, cidade, valor, txid='***'):
    import qrcode
    import tempfile

    payload = _gerar_payload_pix(chave_pix, nome_empresa, cidade, valor, txid)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=20,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    temp_path = os.path.join(tempfile.gettempdir(), f'qrcode_pix_{txid}.png')
    img.save(temp_path, 'PNG')

    return temp_path


def exportar_servico_pdf(request, pk):
    servico = get_object_or_404(
        Servico.objects.select_related('cliente', 'tecnico', 'tipo_servico')
        .prefetch_related('maquinas'),
        pk=pk
    )
    gastos = servico.gastos_extras.all()
    pecas = servico.pecas.all()
    maquinas = servico.maquinas.all()
    config = Configuracao.load()

    valor_km_total = Decimal('0.00')
    valor_hora_total = Decimal('0.00')
    if servico.km_rodado and servico.valor_km:
        valor_km_total = servico.km_rodado * servico.valor_km
    if servico.hora_trabalhada and servico.valor_hora:
        valor_hora_total = servico.hora_trabalhada * servico.valor_hora

    valor_pecas_total = sum(p.valor_total for p in pecas)
    valor_gastos_total = sum(g.valor for g in gastos)

    logo_url = None
    if config.logo:
        logo_url = config.logo.url

    qrcode_path = None
    if config.chave_pix:
        cidade = config.endereco.split(',')[-1].strip() if config.endereco else '***'
        qrcode_path = _gerar_qrcode_pix(
            config.chave_pix,
            config.nome_empresa or '***',
            cidade,
            servico.valor_total,
            txid=f'OS{servico.pk:04d}'
        )

    html_string = render_to_string('pdf/servico.html', {
        'servico': servico,
        'gastos': gastos,
        'pecas': pecas,
        'maquinas': maquinas,
        'config': config,
        'valor_km_total': valor_km_total,
        'valor_hora_total': valor_hora_total,
        'valor_pecas_total': valor_pecas_total,
        'valor_gastos_total': valor_gastos_total,
        'data_geracao': timezone.now().strftime('%d/%m/%Y às %H:%M'),
        'logo_url': logo_url,
        'qrcode_path': qrcode_path,
    })

    response = HttpResponse(content_type='application/pdf')
    filename = f"OS_{servico.cliente.nome.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    pisa.CreatePDF(html_string, dest=response, link_callback=_link_callback)

    if qrcode_path and os.path.exists(qrcode_path):
        os.remove(qrcode_path)

    return response
