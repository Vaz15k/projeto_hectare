from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from clientes.models import renomear_foto_maquina
from core.models import Configuracao, renomear_logo
from utils.file_utils import validar_tamanho_arquivo


class ConfiguracaoTests(TestCase):
    def test_load_cria_configuracao_e_reutiliza_registro(self):
        config = Configuracao.load()
        self.assertEqual(config.pk, 1)
        config.nome_empresa = 'Hectare'
        config.save()
        self.assertEqual(Configuracao.load().nome_empresa, 'Hectare')
        self.assertEqual(Configuracao.objects.count(), 1)

    def test_save_forca_registro_unico(self):
        Configuracao.objects.create(nome_empresa='Antigo')
        config = Configuracao(pk=99, nome_empresa='Novo')
        config.save()
        self.assertEqual(config.pk, 1)
        self.assertEqual(Configuracao.objects.count(), 1)
        self.assertEqual(Configuracao.load().nome_empresa, 'Novo')


class ArquivosTests(SimpleTestCase):
    def test_tamanho_aceita_limite_inclusive(self):
        for tamanho in (0, 1, 10 * 1024 * 1024):
            with self.subTest(tamanho=tamanho):
                validar_tamanho_arquivo(SimpleNamespace(size=tamanho))

    def test_tamanho_rejeita_um_byte_acima(self):
        with self.assertRaisesMessage(ValidationError, 'maior que 10 MB'):
            validar_tamanho_arquivo(SimpleNamespace(size=10 * 1024 * 1024 + 1))

    def test_logo_preserva_extensao_e_descarta_nome_original(self):
        self.assertEqual(renomear_logo(None, 'minha.empresa.png'), 'config/logo.png')

    def test_foto_separa_cliente_e_gera_nomes_distintos(self):
        maquina = SimpleNamespace(cliente=SimpleNamespace(pk=42))
        nomes = [renomear_foto_maquina(maquina, 'foto.jpg') for _ in range(2)]
        for nome in nomes:
            self.assertRegex(nome, r'^maquinas/42/[a-f0-9]{8}\.jpg$')
        self.assertNotEqual(*nomes)
