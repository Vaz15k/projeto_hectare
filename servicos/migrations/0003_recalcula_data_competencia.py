from datetime import datetime

from django.db import migrations
from django.utils import timezone


def recalcular_competencia(apps, schema_editor):
    """Regrava a competência a partir da data de início, no fuso local.

    Os registros existentes foram gravados com fusos diferentes conforme o
    caminho que os criou, então o dashboard não conseguia agrupá-los. A regra
    é redundante com `calcular_data_competencia`, mas fica congelada aqui para
    a migração não depender do modelo atual.
    """
    Servico = apps.get_model('servicos', 'Servico')

    atualizados = []
    for servico in Servico.objects.exclude(data_inicio=None).iterator():
        inicio = timezone.localtime(servico.data_inicio)
        competencia = timezone.make_aware(datetime(inicio.year, inicio.month, 1))
        if servico.data_competencia != competencia:
            servico.data_competencia = competencia
            atualizados.append(servico)

    Servico.objects.bulk_update(atualizados, ['data_competencia'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('servicos', '0002_alter_anexoservico_arquivo'),
    ]

    operations = [
        migrations.RunPython(recalcular_competencia, migrations.RunPython.noop),
    ]
