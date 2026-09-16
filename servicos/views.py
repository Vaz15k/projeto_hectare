import json
import os
import re
import unicodedata
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from xhtml2pdf import pisa

from servicos.models import Servico, TipoServico, GastoExtra, PecaUtilizada
from servicos.forms import (
    ServicoForm, TipoServicoForm,
    GastoExtraFormSet, AnexoServicoFormSet, PecaUtilizadaFormSet, ServicoTipoFormSet,
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
                qs = qs.filter(tipos_servico__pk=int(tipo_servico_id))
            except (ValueError, TypeError):
                pass
        if status and not excluir_status:
            qs = qs.filter(status=status)
        return qs

    return ctx, aplicar


# ---------------------------------------------------------------------------
# Períodos
# ---------------------------------------------------------------------------

def _inicio_do_mes(ano, mes):
    """Meia-noite do dia 1 do mês informado, no fuso configurado no projeto."""
    return timezone.make_aware(datetime(ano, mes, 1))


def _deslocar_mes(referencia, meses):
    """Início do mês deslocado `meses` a partir de `referencia`."""
    total = referencia.year * 12 + referencia.month - 1 + meses
    return _inicio_do_mes(total // 12, total % 12 + 1)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def home(request):
    hoje = timezone.localtime()
    primeiro_dia_mes = _inicio_do_mes(hoje.year, hoje.month)

    filtro_ctx, aplicar_filtro = _build_filtro_ctx(request)
    base = aplicar_filtro(Servico.objects.all())

    mes_ref = primeiro_dia_mes
    if filtro_ctx['mes_selecionado']:
        try:
            y, m = map(int, filtro_ctx['mes_selecionado'].split('-'))
            mes_ref = _inicio_do_mes(y, m)
        except (ValueError, TypeError):
            pass

    servicos_em_andamento = base.filter(status='EM_ANDAMENTO').count()

    # Intervalo em vez de igualdade: `data_competencia` é gravada à meia-noite
    # do fuso local e nunca casava com um instante montado em UTC.
    faturamento_mes = base.filter(
        status='CONCLUIDO',
        data_competencia__gte=mes_ref,
        data_competencia__lt=_deslocar_mes(mes_ref, 1),
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

    months = [_deslocar_mes(mes_ref, -i) for i in range(5, -1, -1)]

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
        'cliente', 'tecnico'
    ).prefetch_related('itens_servico__tipo_servico').order_by('-data_criacao')[:5]

    proximos_agendamentos = base.filter(
        status='AGENDADO', data_inicio__gte=hoje,
    ).select_related('cliente', 'tecnico').prefetch_related('itens_servico__tipo_servico').order_by('data_inicio')[:5]

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

@login_required
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


@login_required
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


@login_required
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

def _salvar_servico_com_relacionamentos(
    form,
    formset,
    formset_pecas,
    formset_anexos,
    formset_tipos,
):
    """Salva o serviço e seus relacionamentos em uma única transação."""
    with transaction.atomic():
        servico = form.save()
        formset_tipos.save()
        formset.save()
        formset_pecas.save()
        formset_anexos.save()
        servico.valor_total = (
            servico.calcular_valor_total()
            + sum(g.valor for g in GastoExtra.objects.filter(servico=servico))
            + sum(p.valor_total for p in PecaUtilizada.objects.filter(servico=servico))
        )
        servico.save(update_fields=["valor_total"])
    return servico


@login_required
def listar_servicos(request):
    from django.core.paginator import Paginator

    filtro_ctx, aplicar_filtro = _build_filtro_ctx(request)
    servicos = aplicar_filtro(
        Servico.objects.select_related('cliente', 'tecnico').prefetch_related('itens_servico__tipo_servico')
    ).order_by('-data_inicio')

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
            'colunas': ['#', 'Tipos', 'Cliente', 'Técnico', 'Status', 'Início', 'Total'],
            'mostrar_filtros': True,
        },
    )


@login_required
def criar_servico(request):
    if request.method == "POST":
        form = ServicoForm(request.POST)
        formset = GastoExtraFormSet(request.POST, instance=form.instance)
        formset_pecas = PecaUtilizadaFormSet(request.POST, instance=form.instance)
        formset_anexos = AnexoServicoFormSet(
            request.POST,
            request.FILES,
            instance=form.instance,
        )
        formset_tipos = ServicoTipoFormSet(request.POST, instance=form.instance)

        form_is_valid = form.is_valid()
        formsets_are_valid = all([
            formset.is_valid(),
            formset_pecas.is_valid(),
            formset_anexos.is_valid(),
            formset_tipos.is_valid(),
        ])
        if form_is_valid and formsets_are_valid:
            _salvar_servico_com_relacionamentos(
                form,
                formset,
                formset_pecas,
                formset_anexos,
                formset_tipos,
            )
            return redirect("home")
    else:
        form = ServicoForm()
        formset = GastoExtraFormSet()
        formset_pecas = PecaUtilizadaFormSet()
        formset_anexos = AnexoServicoFormSet()
        formset_tipos = ServicoTipoFormSet()

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
            "formset_tipos": formset_tipos,
            "maquinas_selecionadas": maquinas_selecionadas,
            "titulo": "Novo Serviço",
            "rota_cancelar": "listar_servicos",
            "url_voltar": "listar_servicos",
        },
    )


@login_required
def editar_servico(request, pk):
    servico = get_object_or_404(Servico, pk=pk)
    if request.method == "POST":
        form = ServicoForm(request.POST, instance=servico)
        formset = GastoExtraFormSet(request.POST, instance=servico)
        formset_pecas = PecaUtilizadaFormSet(request.POST, instance=servico)
        formset_anexos = AnexoServicoFormSet(request.POST, request.FILES, instance=servico)
        formset_tipos = ServicoTipoFormSet(request.POST, instance=servico)

        form_is_valid = form.is_valid()
        formsets_are_valid = all([
            formset.is_valid(),
            formset_pecas.is_valid(),
            formset_anexos.is_valid(),
            formset_tipos.is_valid(),
        ])
        if form_is_valid and formsets_are_valid:
            _salvar_servico_com_relacionamentos(
                form,
                formset,
                formset_pecas,
                formset_anexos,
                formset_tipos,
            )
            return redirect("listar_servicos")
    else:
        form = ServicoForm(instance=servico)
        formset = GastoExtraFormSet(instance=servico)
        formset_pecas = PecaUtilizadaFormSet(instance=servico)
        formset_anexos = AnexoServicoFormSet(instance=servico)
        formset_tipos = ServicoTipoFormSet(instance=servico)

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
            "formset_tipos": formset_tipos,
            "maquinas_selecionadas": maquinas_selecionadas,
            "titulo": f"Editar Serviço #{servico.pk}",
            "rota_cancelar": "listar_servicos",
            "url_voltar": "listar_servicos",
            "submit_label": "Atualizar",
        },
    )


@login_required
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


@login_required
def detalhar_servico(request, pk):
    servico = get_object_or_404(
        Servico.objects.prefetch_related('itens_servico__tipo_servico'), pk=pk
    )
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


def _normalizar_chave_pix(chave, tipo):
    """Formata a chave conforme o tipo cadastrado nas configurações.

    O tipo não pode ser deduzido do tamanho: CPF e celular com DDD têm ambos
    11 dígitos, e tratar um CPF como telefone gera uma chave inexistente.
    """
    chave = chave.strip()
    digitos = re.sub(r'\D', '', chave)

    if tipo in ('cpf', 'cnpj'):
        return digitos
    if tipo == 'telefone':
        # 10/11 dígitos é número nacional (DDD + linha) e precisa do DDI.
        if len(digitos) in (10, 11):
            digitos = f"55{digitos}"
        return f"+{digitos}"
    return chave


def _campo_emv(identificador, valor):
    """Monta um campo do BR Code no formato EMV: id + tamanho + valor.

    O tamanho é contado em bytes porque é assim que o app do banco lê o
    payload, e sempre sobre o valor que realmente será emitido.
    """
    tamanho = len(valor.encode('utf-8'))
    if tamanho > 99:
        raise ValueError(
            f"Campo {identificador} do Pix excede 99 bytes ({tamanho})."
        )
    return f"{identificador}{tamanho:02d}{valor}"


def _texto_br_code(valor, limite):
    """Prepara nome/cidade para o BR Code: sem acento, sem espaço duplicado.

    Acento ocuparia mais de um byte e faria o tamanho declarado divergir do
    conteúdo. O truncamento vem antes da medição, nunca depois.
    """
    ascii_puro = (
        unicodedata.normalize('NFKD', valor)
        .encode('ascii', 'ignore')
        .decode('ascii')
    )
    return ' '.join(ascii_puro.split())[:limite]


def _gerar_payload_pix(chave_pix, nome_beneficiario, cidade, valor, txid='***'):
    import crcmod

    valor_formatado = f"{float(valor):.2f}" if valor else "0.00"

    merchant_info = "0014BR.GOV.BCB.PIX" + _campo_emv("01", chave_pix)

    payload = "000201"
    payload += _campo_emv("26", merchant_info)
    payload += "52040000"
    payload += "5303986"
    payload += _campo_emv("54", valor_formatado)
    payload += "5802BR"
    payload += _campo_emv("59", _texto_br_code(nome_beneficiario, 25))
    payload += _campo_emv("60", _texto_br_code(cidade, 15))
    payload += _campo_emv("62", _campo_emv("05", txid))

    payload_com_crc = payload + "6304"

    crc16 = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
    crc_calculado = hex(crc16(payload_com_crc.encode('utf-8')))[2:].upper().zfill(4)

    return payload_com_crc + crc_calculado


def _gerar_qrcode_pix(chave_pix, nome_empresa, cidade, valor, txid='***'):
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H
    import tempfile

    payload = _gerar_payload_pix(chave_pix, nome_empresa, cidade, valor, txid)

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=20,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Nome aleatório: o anterior era derivado da OS, então dois downloads
    # simultâneos do mesmo serviço escreviam e apagavam o mesmo arquivo.
    with tempfile.NamedTemporaryFile(
        prefix='qrcode_pix_', suffix='.png', delete=False
    ) as arquivo:
        img.save(arquivo, 'PNG')
        return arquivo.name


@login_required
def exportar_servico_pdf(request, pk):
    servico = get_object_or_404(
        Servico.objects.select_related('cliente', 'tecnico')
        .prefetch_related('maquinas', 'itens_servico__tipo_servico'),
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
            _normalizar_chave_pix(config.chave_pix, config.tipo_chave_pix),
            config.nome_empresa or '***',
            cidade,
            servico.valor_total,
            txid=f'OS{servico.pk:04d}'
        )

    response = HttpResponse(content_type='application/pdf')
    filename = f"OS_{servico.cliente.nome.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # O QR fica num arquivo temporário só para o xhtml2pdf conseguir lê-lo, e
    # precisa sumir mesmo se a renderização estourar no meio.
    try:
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
            'data_geracao': timezone.localtime().strftime('%d/%m/%Y às %H:%M'),
            'logo_url': logo_url,
            'qrcode_path': qrcode_path,
        })

        pisa.CreatePDF(html_string, dest=response, link_callback=_link_callback)
    finally:
        if qrcode_path and os.path.exists(qrcode_path):
            os.remove(qrcode_path)

    return response
