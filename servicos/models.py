from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING
from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.validators import MinValueValidator
from django.utils import timezone

from utils.file_utils import validar_tamanho_arquivo
from clientes.models import Cliente, Maquina
from funcionarios.models import Empregado


class TipoServico(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    valor_padrao = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Valor padrão (R$)',
        help_text='Opcional. Usado como sugestão ao adicionar o tipo a uma OS.',
    )

    class Meta:
        db_table = 'core_tiposervico'

    def __str__(self):
        return self.nome


def calcular_data_competencia(data_inicio):
    """
    Calcula a data de competência como o primeiro dia do mês de `data_inicio`,
    à meia-noite no fuso configurado no projeto.
    Se `data_inicio` for None, usa o mês atual.
    """
    if data_inicio is None:
        data_inicio = timezone.localtime()
    elif isinstance(data_inicio, datetime) and timezone.is_aware(data_inicio):
        # Do banco a data volta em UTC. Sem converter para o fuso local, um
        # serviço iniciado no fim do mês cairia na competência do mês seguinte.
        data_inicio = timezone.localtime(data_inicio)
    return timezone.make_aware(datetime(data_inicio.year, data_inicio.month, 1))


class Servico(models.Model):
    TIPOS_DESCONTO = [
        ('NENHUM', 'Sem desconto'),
        ('PERCENTUAL', 'Porcentagem (%)'),
        ('VALOR', 'Valor fixo (R$)'),
    ]
    STATUS_POS = [
        ('ORCAMENTO', 'Orçamento'),
        ('AGENDADO', 'Agendado'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]

    tecnico = models.ForeignKey(
        Empregado, on_delete=models.PROTECT, related_name='servicos_tecnico'
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name='servicos'
    )
    tipos_servico = models.ManyToManyField(
        TipoServico, through='ServicoTipo', related_name='servicos_tipo'
    )
    maquinas = models.ManyToManyField(
        Maquina, blank=True, related_name='servicos', db_table='core_servico_maquinas'
    )

    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição do Serviço")
    problema_relatado = models.TextField(
        blank=True, null=True, verbose_name="Problema Relatado",
        help_text="O que o cliente relatou como problema"
    )
    diagnostico = models.TextField(
        blank=True, null=True, verbose_name="Diagnóstico",
        help_text="Causa do problema identificada pelo técnico"
    )
    solucao = models.TextField(
        blank=True, null=True, verbose_name="Solução",
        help_text="O que foi feito para resolver"
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_inicio = models.DateTimeField(blank=True, null=True)
    data_conclusao = models.DateTimeField(blank=True, null=True)
    data_competencia = models.DateTimeField(blank=True, null=True)

    km_rodado = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    valor_km = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    hora_trabalhada = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    valor_hora = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tipo_desconto = models.CharField(
        max_length=10, choices=TIPOS_DESCONTO, default='NENHUM',
        verbose_name='Tipo de desconto',
    )
    desconto = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Desconto (%) ou (R$)',
    )

    valor_total = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, editable=False
    )
    status = models.CharField(max_length=20, choices=STATUS_POS, default='ORCAMENTO')

    if TYPE_CHECKING:
        from django.db.models.query import QuerySet
        gastos_extras: QuerySet['GastoExtra']
        anexos: QuerySet['AnexoServico']
        pecas: QuerySet['PecaUtilizada']
        itens_servico: QuerySet['ServicoTipo']

    class Meta:
        db_table = 'core_servico'

    def __str__(self):
        return f"OS #{self.pk} - {self.cliente.nome}"

    def calcular_subtotal(self):
        total = Decimal('0.00')
        if self.km_rodado and self.valor_km:
            total += self.km_rodado * self.valor_km
        if self.hora_trabalhada and self.valor_hora:
            total += self.hora_trabalhada * self.valor_hora
        if self.pk:
            total += sum(item.valor_aplicado for item in self.itens_servico.all())
        return total

    def calcular_desconto(self, subtotal):
        if self.tipo_desconto == 'PERCENTUAL':
            valor = subtotal * self.desconto / Decimal('100')
        elif self.tipo_desconto == 'VALOR':
            valor = self.desconto
        else:
            valor = Decimal('0.00')
        return min(subtotal, valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def calcular_valor_total(self, subtotal=None):
        if subtotal is None:
            subtotal = self.calcular_subtotal()
        return subtotal - self.calcular_desconto(subtotal)

    def save(self, *args, **kwargs):
        if self.data_inicio:
            self.data_competencia = calcular_data_competencia(self.data_inicio)
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'valor_total' not in update_fields:
            self.valor_total = self.calcular_valor_total()
        super().save(*args, **kwargs)


class ServicoTipo(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name='itens_servico')
    tipo_servico = models.ForeignKey(TipoServico, on_delete=models.PROTECT)
    valor_aplicado = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Valor do serviço (R$)',
    )

    if TYPE_CHECKING:
        servico_id: int

    class Meta:
        db_table = 'core_servicotipo'
        constraints = [models.UniqueConstraint(
            fields=['servico', 'tipo_servico'], name='servicotipo_unico_por_os'
        )]

    def __str__(self):
        return f'{self.tipo_servico.nome} - OS #{self.servico_id}'


def renomear_anexo(instance, filename):
    import uuid
    from datetime import datetime

    ext = filename.split('.')[-1]
    nome_arquivo = f"servico_{instance.servico.pk}_{uuid.uuid4().hex[:8]}.{ext}"
    data = datetime.now().strftime("%Y/%m/%d")
    return f"anexos_servicos/{data}/{nome_arquivo}"


class AnexoServico(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(
        upload_to=renomear_anexo, verbose_name="Anexo",
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'mp4', 'mov', 'avi']
            ),
            validar_tamanho_arquivo,
        ]
    )
    descricao = models.TextField(blank=True, null=True)
    data_upload = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_anexoservico'

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

    class Meta:
        db_table = 'core_gastoextra'

    def __str__(self):
        return f"{self.descricao}: R$ {self.valor}"


class PecaUtilizada(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name='pecas')
    nome = models.CharField(max_length=200, verbose_name="Nome da Peça")
    quantidade = models.PositiveIntegerField(default=1, verbose_name="Qtd.")
    valor_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Valor Unitário (R$)"
    )
    valor_total = models.DecimalField(
        max_digits=10, decimal_places=2, editable=False, verbose_name="Valor Total"
    )

    class Meta:
        db_table = 'core_pecautilizada'

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

    class Meta:
        db_table = 'core_notafiscal'

    def __str__(self):
        return f"Nota Fiscal {self.numero_nota_fiscal} - Serviço {self.servico.pk}"
