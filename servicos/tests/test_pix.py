import binascii
import os
from decimal import Decimal

from django.test import SimpleTestCase
from PIL import Image

from servicos.views import _gerar_payload_pix, _gerar_qrcode_pix, _normalizar_chave_pix


def campos_emv(payload):
    """Leitor independente para verificar os tamanhos emitidos em bytes."""
    dados = payload.encode('utf-8')
    campos = {}
    while dados:
        identificador = dados[:2].decode()
        tamanho = int(dados[2:4])
        valor = dados[4:4 + tamanho]
        if len(valor) != tamanho:
            raise AssertionError('Campo EMV incompleto')
        campos[identificador] = valor.decode()
        dados = dados[4 + tamanho:]
    return campos


class PixTests(SimpleTestCase):
    def test_payload_campos_valor_e_crc_independente(self):
        payload = _gerar_payload_pix('teste@example.org', '  José   Agrícola ', 'Cuiabá', Decimal('123.45'), 'OS0001')
        campos = campos_emv(payload)
        self.assertEqual(campos['00'], '01')
        self.assertEqual(campos['53'], '986')
        self.assertEqual(campos['54'], '123.45')
        self.assertEqual(campos['58'], 'BR')
        self.assertEqual(campos['59'], 'Jose Agricola')
        self.assertEqual(campos['60'], 'Cuiaba')
        self.assertEqual(campos_emv(campos['26'])['01'], 'teste@example.org')
        self.assertEqual(campos_emv(campos['62'])['05'], 'OS0001')
        self.assertEqual(campos['63'], f'{binascii.crc_hqx(payload[:-4].encode(), 0xFFFF):04X}')

    def test_zero_none_e_truncamento(self):
        for valor in (None, Decimal(0)):
            with self.subTest(valor=valor):
                campos = campos_emv(_gerar_payload_pix('chave', 'á' * 30, 'é' * 20, valor))
                self.assertEqual(campos['54'], '0.00')
                self.assertEqual(campos['59'], 'a' * 25)
                self.assertEqual(campos['60'], 'e' * 15)
                self.assertEqual(campos_emv(campos['62'])['05'], '***')

    def test_chave_longa_rejeitada_sem_truncar(self):
        with self.assertRaises(ValueError):
            _gerar_payload_pix('x' * 100, 'Empresa', 'Cidade', 10)

    def test_normalizacao_respeita_tipo_da_chave(self):
        for chave, tipo, esperado in [
            ('123.456.789-01', 'cpf', '12345678901'),
            ('12.345.678/0001-90', 'cnpj', '12345678000190'),
            ('(65) 99999-1234', 'telefone', '+5565999991234'),
            ('+55 65 99999-1234', 'telefone', '+5565999991234'),
            (' teste@example.org ', 'email', 'teste@example.org'),
            (' abc-def ', 'aleatoria', 'abc-def'),
        ]:
            with self.subTest(tipo=tipo, chave=chave):
                self.assertEqual(_normalizar_chave_pix(chave, tipo), esperado)

    def test_qrcode_png_valido_e_arquivos_independentes(self):
        caminhos = []
        try:
            for _ in range(2):
                caminho = _gerar_qrcode_pix('chave', '', '', None)
                caminhos.append(caminho)
                with Image.open(caminho) as imagem:
                    self.assertEqual(imagem.format, 'PNG')
                    self.assertEqual(imagem.width, imagem.height)
                    imagem.verify()
            self.assertNotEqual(*caminhos)
        finally:
            for caminho in caminhos:
                os.remove(caminho)
