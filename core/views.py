from django.shortcuts import render
from .models import Servico

def home(request):
    servicos = Servico.objects.all().order_by('-data_inicio')

    context = {
        'lista_servicos': servicos,
    }

    return render(request, 'home.html', context)