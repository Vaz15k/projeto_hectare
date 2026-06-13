from django.db import models


class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    documento = models.CharField(
        max_length=20, unique=True, blank=True, null=True, help_text="CPF ou CNPJ"
    )
    endereco = models.CharField(max_length=200, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'core_cliente'

    def __str__(self):
        return self.nome


def renomear_foto_maquina(instance, filename):
    import uuid
    ext = filename.split('.')[-1]
    return f"maquinas/{instance.cliente.pk}/{uuid.uuid4().hex[:8]}.{ext}"


class Maquina(models.Model):
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, related_name='maquinas'
    )
    nome = models.CharField(max_length=200, verbose_name="Nome da Máquina")
    marca = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    modelo = models.CharField(max_length=100, blank=True, null=True)
    numero_serie = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Nº de Série"
    )
    ano = models.IntegerField(blank=True, null=True)
    foto = models.ImageField(
        upload_to=renomear_foto_maquina, blank=True, null=True, verbose_name="Foto da Máquina"
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'core_maquina'

    def __str__(self):
        return self.nome
