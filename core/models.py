from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

# Create your models here.
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

class TipoServico(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome

class Servico(models.Model):
    STATUS_POS = [
        ('ORCAMENTO', 'Orçamento'), # REVISAR SE PRECISAR SALVAR O ORÇAMENTO
        ('AGENDADO', 'Agendado'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]

    tecnico = models.ForeignKey(User, on_delete=models.PROTECT, related_name='servico_realizado')

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='servicos')
    tipo_servico = models.ForeignKey(TipoServico, on_delete=models.PROTECT, related_name='servicos_tipo')
    descricao = models.TextField(blank=True, null=True)
    pecas_utilizadas = models.TextField(blank=True, null=True, verbose_name="Peças Utilizadas(Registro)")

    data_inicio = models.DateTimeField(auto_now_add=True)
    data_conclusao = models.DateTimeField(blank=True, null=True)
    data_competencia = models.DateTimeField(blank=True, null=True)

    km_rodado = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    valor_km = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    hora_trabalhada = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    valor_hora = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    valor_servico = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_POS, default='ORCAMENTO')

    def __str__(self):
        return f"{self.tipo_servico.nome} - {self.cliente.nome}"

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


class NotaFiscal(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.PROTECT, related_name='notas_fiscais')

    numero_nota_fiscal = models.CharField(max_length=50, unique=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    descricao_nota = models.TextField(blank=True, null=True)
    data_emissao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Nota Fiscal {self.numero_nota_fiscal} - Serviço {self.servico.pk}"