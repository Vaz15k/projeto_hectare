from decimal import Decimal
from typing import TYPE_CHECKING
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

# Create your models here.

class Empregado(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, unique=True)
    cargo = models.CharField(max_length=100)

    def __str__(self):
        return (f"{self.nome} - {self.cargo}")

class Cliente(models.Model):
    nome = models.CharField(max_length=100)

    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    documento = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="CPF ou CNPJ")

    endereco = models.CharField(max_length=200, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


def renomear_foto_maquina(instance, filename):
    import uuid
    ext = filename.split('.')[-1]
    return f"maquinas/{instance.cliente.pk}/{uuid.uuid4().hex[:8]}.{ext}"


class Maquina(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='maquinas')
    nome = models.CharField(max_length=200, verbose_name="Nome da Máquina")
    marca = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    modelo = models.CharField(max_length=100, blank=True, null=True)
    numero_serie = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nº de Série")
    ano = models.IntegerField(blank=True, null=True)
    foto = models.ImageField(upload_to=renomear_foto_maquina, blank=True, null=True, verbose_name="Foto da Máquina")
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

class TipoServico(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome


def calcular_data_competencia(data_inicio):
    """
    Calcula a data de competência como o primeiro dia do mês de `data_inicio`.
    Se `data_inicio` for None, retorna o primeiro dia do mês atual.
    """
    from datetime import datetime
    if data_inicio is None:
        return datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if isinstance(data_inicio, datetime):
        return data_inicio.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return datetime(data_inicio.year, data_inicio.month, 1)

class Servico(models.Model):
    STATUS_POS = [
        ('ORCAMENTO', 'Orçamento'), # REVISAR SE PRECISAR SALVAR O ORÇAMENTO
        ('AGENDADO', 'Agendado'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]

    tecnico = models.ForeignKey(Empregado, on_delete=models.PROTECT, related_name='servicos_tecnico')

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='servicos')
    tipo_servico = models.ForeignKey(TipoServico, on_delete=models.PROTECT, related_name='servicos_tipo')
    maquinas = models.ManyToManyField('Maquina', blank=True, related_name='servicos')

    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição do Serviço")

    problema_relatado = models.TextField(blank=True, null=True, verbose_name="Problema Relatado", help_text="O que o cliente relatou como problema")
    diagnostico = models.TextField(blank=True, null=True, verbose_name="Diagnóstico", help_text="Causa do problema identificada pelo técnico")
    solucao = models.TextField(blank=True, null=True, verbose_name="Solução", help_text="O que foi feito para resolver")

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_inicio = models.DateTimeField(blank=True, null=True)
    data_conclusao = models.DateTimeField(blank=True, null=True)
    data_competencia = models.DateTimeField(blank=True, null=True)

    km_rodado = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    valor_km = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    hora_trabalhada = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    valor_hora = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    valor_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=False)

    status = models.CharField(max_length=20, choices=STATUS_POS, default='ORCAMENTO')

    if TYPE_CHECKING:
        from django.db.models.query import QuerySet
        gastos_extras: QuerySet['GastoExtra']
        anexos: QuerySet['AnexoServico']
        pecas: QuerySet['PecaUtilizada']

    def __str__(self):
        return f"{self.tipo_servico.nome} - {self.cliente.nome}"

    def calcular_valor_total(self):
        total = Decimal('0.00')
        if self.km_rodado and self.valor_km:
            total += self.km_rodado * self.valor_km
        if self.hora_trabalhada and self.valor_hora:
            total += self.hora_trabalhada * self.valor_hora
        return total

    def save(self, *args, **kwargs):
        if self.data_inicio and not self.data_competencia:
            self.data_competencia = calcular_data_competencia(self.data_inicio)
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'valor_total' not in update_fields:
            self.valor_total = self.calcular_valor_total()
        super().save(*args, **kwargs)


def renomear_anexo(instance, filename):
    import uuid
    from datetime import datetime

    ext = filename.split('.')[-1]
    nome_arquivo = f"servico_{instance.servico.pk}_{uuid.uuid4().hex[:8]}.{ext}"

    data = datetime.now().strftime("%Y/%m/%d")
    return f"anexos_servicos/{data}/{nome_arquivo}"

class AnexoServico(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name='anexos')

    arquivo = models.FileField(upload_to=renomear_anexo, verbose_name="Anexo", validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'mp4', 'mov', 'avi'])])
    descricao = models.TextField(blank=True, null=True)
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Anexo do Serviço {self.servico.pk} - {self.arquivo.name}"

    def is_image(self):
        name = self.arquivo.name.lower()
        return name.endswith(('.jpg', '.jpeg', '.png'))

    def is_video(self):
        name = self.arquivo.name.lower()
        return name.endswith(('.mp4', '.mov', '.avi'))


class GastoExtra(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name='gastos_extras')
    descricao = models.CharField(max_length=200, verbose_name="Descrição do gasto")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor (R$)")

    def __str__(self):
        return f"{self.descricao}: R$ {self.valor}"


class PecaUtilizada(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name='pecas')
    nome = models.CharField(max_length=200, verbose_name="Nome da Peça")
    quantidade = models.PositiveIntegerField(default=1, verbose_name="Qtd.")
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Unitário (R$)")
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False, verbose_name="Valor Total")

    def save(self, *args, **kwargs):
        self.valor_total = self.quantidade * self.valor_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} x{self.quantidade} — R$ {self.valor_total}"


class NotaFiscal(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.PROTECT, related_name='notas_fiscais')

    numero_nota_fiscal = models.CharField(max_length=50, unique=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    descricao_nota = models.TextField(blank=True, null=True)
    data_emissao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Nota Fiscal {self.numero_nota_fiscal} - Serviço {self.servico.pk}"


def renomear_logo(instance, filename):
    ext = filename.split('.')[-1]
    return f"config/logo.{ext}"


class Configuracao(models.Model):
    TIPOS_CHAVE_PIX = [
        ('cpf', 'CPF'),
        ('cnpj', 'CNPJ'),
        ('email', 'E-mail'),
        ('telefone', 'Telefone'),
        ('aleatoria', 'Chave Aleatória'),
    ]

    nome_empresa = models.CharField(max_length=200, blank=True, verbose_name="Nome da Empresa")
    cnpj = models.CharField(max_length=20, blank=True, verbose_name="CNPJ")
    endereco = models.CharField(max_length=300, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    logo = models.ImageField(upload_to=renomear_logo, blank=True, verbose_name="Logo")

    texto_cabecalho = models.TextField(blank=True, verbose_name="Texto do Cabeçalho (PDF)", help_text="Texto exibido no cabeçalho do PDF exportado")
    texto_rodape = models.TextField(blank=True, verbose_name="Texto do Rodapé (PDF)", help_text="Texto exibido no rodapé do PDF exportado")

    chave_pix = models.CharField(max_length=200, blank=True, verbose_name="Chave Pix")
    tipo_chave_pix = models.CharField(max_length=10, choices=TIPOS_CHAVE_PIX, blank=True, verbose_name="Tipo da Chave Pix")

    class Meta:
        verbose_name = "Configuração"
        verbose_name_plural = "Configurações"

    def __str__(self):
        return self.nome_empresa or "Configurações do Sistema"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj