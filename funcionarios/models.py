from django.db import models


class Empregado(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, unique=True)
    cargo = models.CharField(max_length=100)

    class Meta:
        db_table = 'core_empregado'

    def __str__(self):
        return f"{self.nome} - {self.cargo}"
