from django.urls import path
from core import views

urlpatterns = [
    path('', views.editar_configuracoes, name='editar_configuracoes'),
]
