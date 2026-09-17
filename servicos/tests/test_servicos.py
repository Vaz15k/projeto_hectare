import os
from datetime import datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from clientes.models import Cliente, Maquina
from core.models import Configuracao
from funcionarios.models import Empregado
from servicos.forms import (
    AnexoServicoFormSet,
    GastoExtraFormSet,
    PecaUtilizadaFormSet,
    ServicoForm,
    ServicoTipoFormSet,
)
from servicos.models import (
    AnexoServico,
    GastoExtra,
    PecaUtilizada,
    Servico,
    ServicoTipo,
    TipoServico,
    calcular_data_competencia,
)
from servicos.views import (
    _build_filtro_ctx,
    _gerar_qrcode_pix,
    _salvar_servico_com_relacionamentos,
)


class ServicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username='tecnico')
        cls.cliente = Cliente.objects.create(nome='Cliente Teste')
        cls.tecnico = Empregado.objects.create(nome='Tecnico', cpf='12345678901', cargo='Tecnico')
        cls.tipo = TipoServico.objects.create(nome='Manutencao')
        cls.maquina = Maquina.objects.create(cliente=cls.cliente, nome='Trator')
        cls.servico = Servico.objects.create(
            cliente=cls.cliente, tecnico=cls.tecnico,
            data_inicio=datetime(2026, 1, 31, 23, tzinfo=timezone.get_current_timezone()),
            km_rodado=Decimal(10), valor_km=Decimal('2.50'),
            hora_trabalhada=Decimal(2), valor_hora=Decimal(100),
        )
        ServicoTipo.objects.create(servico=cls.servico, tipo_servico=cls.tipo)

    def setUp(self):
        self.client.force_login(self.usuario)

    def url(self, nome, pk=None):
        return reverse(nome, args=[pk or self.servico.pk])

    def formularios(self):
        dados = {
            'cliente': self.cliente.pk, 'tecnico': self.tecnico.pk,
            'status': 'ORCAMENTO',
            'maquinas': [self.maquina.pk], 'km_rodado': '10', 'valor_km': '2.50',
            'hora_trabalhada': '2', 'valor_hora': '100',
            'gastos_extras-TOTAL_FORMS': '1', 'gastos_extras-INITIAL_FORMS': '0',
            'gastos_extras-0-descricao': 'Frete', 'gastos_extras-0-valor': '15.50',
            'pecas-TOTAL_FORMS': '1', 'pecas-INITIAL_FORMS': '0',
            'pecas-0-nome': 'Filtro', 'pecas-0-quantidade': '3', 'pecas-0-valor_unitario': '12.30',
            'anexos-TOTAL_FORMS': '0', 'anexos-INITIAL_FORMS': '0',
            'itens_servico-TOTAL_FORMS': '1', 'itens_servico-INITIAL_FORMS': '0',
            'itens_servico-0-tipo_servico': self.tipo.pk,
        }
        form = ServicoForm(dados)
        forms = [form] + [classe(dados, instance=form.instance) for classe in
                          (GastoExtraFormSet, PecaUtilizadaFormSet, AnexoServicoFormSet, ServicoTipoFormSet)]
        for formulario in forms:
            self.assertTrue(formulario.is_valid(), formulario.errors)
        return forms

    def test_total_base_decimal(self):
        self.assertEqual(self.servico.valor_total, Decimal('225.00'))
        self.assertEqual(Servico().calcular_valor_total(), Decimal(0))

    def test_competencia_considera_fuso_na_virada_do_mes(self):
        instante = datetime(2026, 2, 1, 2, tzinfo=dt_timezone.utc)
        self.assertEqual(calcular_data_competencia(instante), datetime(2026, 1, 1, tzinfo=timezone.get_current_timezone()))

    def test_salva_formularios_reais_maquinas_e_total_com_relacionamentos(self):
        servico = _salvar_servico_com_relacionamentos(*self.formularios())
        servico.refresh_from_db()
        self.assertEqual(servico.valor_total, Decimal('277.40'))
        self.assertEqual(list(servico.maquinas.all()), [self.maquina])
        self.assertEqual(servico.pecas.get().valor_total, Decimal('36.90'))
        self.assertEqual(servico.gastos_extras.get().valor, Decimal('15.50'))
        self.assertEqual(list(servico.tipos_servico.all()), [self.tipo])

    def test_desconto_percentual_e_fixo_incluem_todos_os_itens(self):
        dados = dict(self.formularios()[0].data)
        dados.update({'tipo_desconto': 'PERCENTUAL', 'desconto': '10'})
        resposta = self.client.post(reverse('criar_servico'), dados)
        self.assertRedirects(resposta, reverse('home'))
        criado = Servico.objects.latest('pk')
        self.assertEqual(criado.valor_total, Decimal('249.66'))
        self.assertEqual(criado.calcular_desconto(Decimal('277.40')), Decimal('27.74'))
        self.assertContains(self.client.get(self.url('detalhar_servico', criado.pk)), '249,66')

        itens = criado.itens_servico.get()
        gasto = criado.gastos_extras.get()
        peca = criado.pecas.get()
        dados.update({
            'tipo_desconto': 'VALOR', 'desconto': '30.00',
            'itens_servico-INITIAL_FORMS': '1', 'itens_servico-0-id': itens.pk,
            'gastos_extras-INITIAL_FORMS': '1', 'gastos_extras-0-id': gasto.pk,
            'pecas-INITIAL_FORMS': '1', 'pecas-0-id': peca.pk,
        })
        self.assertRedirects(self.client.post(self.url('editar_servico', criado.pk), dados),
                             reverse('listar_servicos'))
        criado.refresh_from_db()
        self.assertEqual(criado.valor_total, Decimal('247.40'))
        self.assertEqual(criado.tipo_desconto, 'VALOR')

    def test_descontos_invalidos_sao_rejeitados_sem_criar_os(self):
        base = dict(self.formularios()[0].data)
        for tipo, valor in [('PERCENTUAL', '101'), ('VALOR', '278'),
                            ('VALOR', '-1'), ('NENHUM', '10')]:
            with self.subTest(tipo=tipo, valor=valor):
                resposta = self.client.post(reverse('criar_servico'), {
                    **base, 'tipo_desconto': tipo, 'desconto': valor,
                })
                self.assertEqual(resposta.status_code, 200)
                self.assertIn('desconto', resposta.context['form'].errors)
                self.assertEqual(Servico.objects.count(), 1)

    def test_cria_os_com_dois_tipos_valores_padrao_e_ajuste(self):
        self.tipo.valor_padrao = Decimal('40.00')
        self.tipo.save()
        segundo = TipoServico.objects.create(nome='Revisao', valor_padrao=Decimal('60.00'))
        tela_criacao = self.client.get(reverse('criar_servico'))
        self.assertContains(tela_criacao, "['%s', '40.00']" % self.tipo.pk)
        self.assertEqual(tela_criacao.context['formset_tipos'].total_form_count(), 1)
        dados = {
            'cliente': self.cliente.pk, 'tecnico': self.tecnico.pk, 'status': 'ORCAMENTO',
            'itens_servico-TOTAL_FORMS': '2', 'itens_servico-INITIAL_FORMS': '0',
            'itens_servico-0-tipo_servico': self.tipo.pk,
            'itens_servico-1-tipo_servico': segundo.pk,
            'itens_servico-1-valor_aplicado': '55.00',
            'gastos_extras-TOTAL_FORMS': '0', 'gastos_extras-INITIAL_FORMS': '0',
            'pecas-TOTAL_FORMS': '0', 'pecas-INITIAL_FORMS': '0',
            'anexos-TOTAL_FORMS': '0', 'anexos-INITIAL_FORMS': '0',
        }
        response = self.client.post(reverse('criar_servico'), dados)
        self.assertRedirects(response, reverse('home'))
        criado = Servico.objects.latest('pk')
        tela_edicao = self.client.get(self.url('editar_servico', criado.pk))
        self.assertContains(tela_edicao, 'Revisao')
        self.assertEqual(tela_edicao.context['formset_tipos'].total_form_count(), 2)
        self.assertEqual(criado.valor_total, Decimal('95.00'))
        self.assertEqual(list(criado.itens_servico.order_by('pk').values_list('valor_aplicado', flat=True)),
                         [Decimal('40.00'), Decimal('55.00')])
        self.assertContains(self.client.get(self.url('detalhar_servico', criado.pk)), 'Revisao')
        self.assertContains(self.client.get(reverse('listar_servicos')), 'Manutencao, Revisao')

        filtro = _build_filtro_ctx(RequestFactory().get('/', {'tipo_servico': segundo.pk}))[1]
        self.assertIn(criado, filtro(Servico.objects.all()))

        itens = list(criado.itens_servico.order_by('pk'))
        edicao = dados.copy()
        edicao.update({
            'itens_servico-INITIAL_FORMS': '2',
            'itens_servico-0-id': itens[0].pk,
            'itens_servico-0-valor_aplicado': '40.00',
            'itens_servico-1-id': itens[1].pk,
            'itens_servico-1-valor_aplicado': '50.00',
        })
        self.assertRedirects(self.client.post(self.url('editar_servico', criado.pk), edicao),
                             reverse('listar_servicos'))
        criado.refresh_from_db()
        self.assertEqual(criado.valor_total, Decimal('90.00'))

        segundo.valor_padrao = Decimal('80.00')
        segundo.save()
        criado.refresh_from_db()
        self.assertEqual(criado.valor_total, Decimal('90.00'))
        self.assertEqual(criado.itens_servico.get(tipo_servico=segundo).valor_aplicado, Decimal('50.00'))

    def test_edicao_nao_mostra_linha_vazia_antes_de_adicionar(self):
        response = self.client.get(self.url('editar_servico'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['formset_tipos'].total_form_count(), 1)
        self.assertEqual(len(response.context['formset_tipos'].forms), 1)

    def test_tipos_duplicados_ou_ausentes_sao_rejeitados(self):
        base = {
            'itens_servico-TOTAL_FORMS': '2', 'itens_servico-INITIAL_FORMS': '0',
            'itens_servico-0-tipo_servico': self.tipo.pk,
            'itens_servico-1-tipo_servico': self.tipo.pk,
        }
        duplicado = ServicoTipoFormSet(base, instance=Servico())
        self.assertFalse(duplicado.is_valid())
        self.assertIn('duplicados', str(duplicado.errors))
        vazio = ServicoTipoFormSet({
            'itens_servico-TOTAL_FORMS': '1', 'itens_servico-INITIAL_FORMS': '0',
        }, instance=Servico())
        self.assertFalse(vazio.is_valid())
        self.assertIn('Adicione ao menos um tipo', str(vazio.non_form_errors()))

    def test_falha_em_cada_etapa_reverte_servico_e_relacionamentos(self):
        for etapa in (1, 2, 3, 4):
            with self.subTest(etapa=etapa):
                forms = self.formularios()
                with (
                    patch.object(forms[etapa], 'save', side_effect=RuntimeError('falha simulada')),
                    self.assertRaisesMessage(RuntimeError, 'falha simulada'),
                ):
                    _salvar_servico_com_relacionamentos(*forms)
                self.assertEqual(Servico.objects.count(), 1)
                self.assertFalse(GastoExtra.objects.exists())
                self.assertFalse(PecaUtilizada.objects.exists())
                self.assertFalse(Servico.maquinas.through.objects.exists())
                self.assertEqual(ServicoTipo.objects.count(), 1)

    def test_falha_ao_editar_restaura_valores_e_gastos_excluidos(self):
        gasto = GastoExtra.objects.create(servico=self.servico, descricao='Frete', valor=10)
        forms = self.formularios()
        dados = dict(forms[0].data)
        dados['descricao'] = 'Alteracao que deve ser revertida'
        dados['gastos_extras-INITIAL_FORMS'] = '1'
        dados['gastos_extras-0-id'] = gasto.pk
        dados['gastos_extras-0-DELETE'] = 'on'
        dados['itens_servico-INITIAL_FORMS'] = '1'
        dados['itens_servico-0-id'] = self.servico.itens_servico.get().pk
        form = ServicoForm(dados, instance=self.servico)
        forms = [form] + [classe(dados, instance=form.instance) for classe in
                          (GastoExtraFormSet, PecaUtilizadaFormSet, AnexoServicoFormSet, ServicoTipoFormSet)]
        for formulario in forms:
            self.assertTrue(formulario.is_valid(), formulario.errors)
        with (
            patch.object(forms[3], 'save', side_effect=RuntimeError('falha ao editar')),
            self.assertRaises(RuntimeError),
        ):
            _salvar_servico_com_relacionamentos(*forms)
        self.servico.refresh_from_db()
        self.assertIsNone(self.servico.descricao)
        self.assertEqual(self.servico.valor_total, Decimal('225.00'))
        self.assertTrue(GastoExtra.objects.filter(pk=gasto.pk).exists())
        self.assertFalse(PecaUtilizada.objects.exists())
        self.assertFalse(self.servico.maquinas.exists())

    def test_maquina_de_outro_cliente_rejeitada(self):
        outro = Cliente.objects.create(nome='Outro')
        form = ServicoForm({'cliente': outro.pk, 'tecnico': self.tecnico.pk,
                            'status': 'ORCAMENTO', 'maquinas': [self.maquina.pk]})
        self.assertFalse(form.is_valid())
        self.assertIn('maquinas', form.errors)

    def test_rotas_exigem_login(self):
        self.client.logout()
        for rota in ('deletar_servico', 'detalhar_servico', 'exportar_servico_pdf'):
            with self.subTest(rota=rota):
                response = self.client.get(self.url(rota))
                self.assertRedirects(response, reverse('login') + '?next=' + self.url(rota), fetch_redirect_response=False)
        self.assertEqual(self.client.post(self.url('deletar_servico')).status_code, 302)
        self.assertTrue(Servico.objects.filter(pk=self.servico.pk).exists())

    def test_rotas_retornam_404(self):
        for rota in ('deletar_servico', 'detalhar_servico', 'exportar_servico_pdf'):
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(self.url(rota, 99999)).status_code, 404)

    def test_detalhe_renderiza_relacionamentos(self):
        gasto = GastoExtra.objects.create(servico=self.servico, descricao='Frete', valor=10)
        peca = PecaUtilizada.objects.create(servico=self.servico, nome='Filtro', quantidade=2, valor_unitario=Decimal(5))
        anexo = AnexoServico.objects.create(servico=self.servico, arquivo='anexos/exemplo.png')
        response = self.client.get(self.url('detalhar_servico'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'detalhar_servico.html')
        self.assertEqual(list(response.context['gastos']), [gasto])
        self.assertEqual(list(response.context['pecas']), [peca])
        self.assertEqual(list(response.context['anexos']), [anexo])

    def test_delete_get_confirma_post_remove_dependentes(self):
        GastoExtra.objects.create(servico=self.servico, descricao='Frete', valor=10)
        PecaUtilizada.objects.create(servico=self.servico, nome='Filtro', valor_unitario=Decimal(5))
        AnexoServico.objects.create(servico=self.servico, arquivo='anexos/exemplo.png')
        self.servico.maquinas.add(self.maquina)
        self.assertEqual(self.client.get(self.url('deletar_servico')).status_code, 200)
        self.assertTrue(Servico.objects.filter(pk=self.servico.pk).exists())
        response = self.client.post(self.url('deletar_servico'))
        self.assertRedirects(response, reverse('listar_servicos'))
        for model in (Servico, GastoExtra, PecaUtilizada, AnexoServico, Servico.maquinas.through):
            self.assertFalse(model.objects.exists())
        self.assertTrue(Cliente.objects.exists())
        self.assertTrue(Maquina.objects.exists())

    def test_delete_exige_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        self.assertEqual(client.post(self.url('deletar_servico')).status_code, 403)
        self.assertTrue(Servico.objects.filter(pk=self.servico.pk).exists())

    def test_filtros_combinados_e_exclusoes(self):
        outro = Servico.objects.create(cliente=self.cliente, tecnico=self.tecnico,
                                       status='CONCLUIDO', data_inicio=datetime(2026, 2, 2, tzinfo=timezone.get_current_timezone()))
        ServicoTipo.objects.create(servico=outro, tipo_servico=self.tipo)
        request = RequestFactory().get('/', {'mes': '2026-01', 'status': 'ORCAMENTO', 'tipo_servico': self.tipo.pk, 'page': 2})
        ctx, aplicar = _build_filtro_ctx(request)
        self.assertTrue(ctx['tem_filtros'])
        self.assertNotIn('page=', ctx['query_string'])
        self.assertEqual(list(aplicar(Servico.objects.all())), [self.servico])
        self.assertCountEqual(aplicar(Servico.objects.all(), excluir_mes=True, excluir_status=True), [self.servico, outro])

    def test_filtros_malformados_ignorados(self):
        _, aplicar = _build_filtro_ctx(RequestFactory().get('/', {'mes': 'invalido', 'tipo_servico': 'abc'}))
        self.assertEqual(list(aplicar(Servico.objects.all())), [self.servico])

    def test_pdf_real_com_e_sem_pix_remove_temporario(self):
        for chave in ('', 'teste@example.org'):
            with self.subTest(chave=chave):
                config = Configuracao.load()
                config.nome_empresa = 'Hectare'
                config.chave_pix = chave
                config.tipo_chave_pix = 'email'
                config.save()
                caminhos = []
                def gerar(*args, caminhos=caminhos, **kwargs):
                    caminho = _gerar_qrcode_pix(*args, **kwargs)
                    caminhos.append(caminho)
                    return caminho
                try:
                    with patch('servicos.views._gerar_qrcode_pix', side_effect=gerar):
                        response = self.client.get(self.url('exportar_servico_pdf'))
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response['Content-Type'], 'application/pdf')
                    self.assertIn('OS_Cliente_Teste.pdf', response['Content-Disposition'])
                    self.assertTrue(response.content.startswith(b'%PDF-'))
                    self.assertEqual(len(caminhos), int(bool(chave)))
                    for caminho in caminhos:
                        self.assertFalse(os.path.exists(caminho))
                finally:
                    for caminho in caminhos:
                        if os.path.exists(caminho):
                            os.remove(caminho)

    def test_pix_do_pdf_usa_total_com_desconto(self):
        self.servico.tipo_desconto = 'VALOR'
        self.servico.desconto = Decimal('10.00')
        self.servico.save()
        config = Configuracao.load()
        config.chave_pix = 'teste@example.org'
        config.tipo_chave_pix = 'email'
        config.save()
        with patch('servicos.views._gerar_qrcode_pix', wraps=_gerar_qrcode_pix) as gerar:
            resposta = self.client.get(self.url('exportar_servico_pdf'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(gerar.call_args.args[3], Decimal('215.00'))

    def test_pdf_remove_qrcode_quando_renderizacao_falha(self):
        Configuracao.objects.create(chave_pix='teste@example.org')
        caminho = _gerar_qrcode_pix('chave', 'Empresa', 'Cidade', 10)
        try:
            with (
                patch('servicos.views._gerar_qrcode_pix', return_value=caminho),
                patch('servicos.views.pisa.CreatePDF', side_effect=RuntimeError('falha PDF')),
                self.assertRaisesMessage(RuntimeError, 'falha PDF'),
            ):
                self.client.get(self.url('exportar_servico_pdf'))
            self.assertFalse(os.path.exists(caminho))
        finally:
            if os.path.exists(caminho):
                os.remove(caminho)
