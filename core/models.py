from django.db import models


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

    texto_cabecalho = models.TextField(
        blank=True, verbose_name="Texto do Cabeçalho (PDF)",
        help_text="Texto exibido no cabeçalho do PDF exportado"
    )
    texto_rodape = models.TextField(
        blank=True, verbose_name="Texto do Rodapé (PDF)",
        help_text="Texto exibido no rodapé do PDF exportado"
    )

    chave_pix = models.CharField(max_length=200, blank=True, verbose_name="Chave Pix")
    tipo_chave_pix = models.CharField(
        max_length=10, choices=TIPOS_CHAVE_PIX, blank=True, verbose_name="Tipo da Chave Pix"
    )

    class Meta:
        db_table = 'core_configuracao'
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
