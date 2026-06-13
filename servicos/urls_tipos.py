from django.urls import path
from servicos import views

urlpatterns = [
    path('', views.listar_tipos_servico, name='listar_tipos_servico'),
    path('criar/', views.criar_tipo_servico, name='criar_tipo_servico'),
    path('<int:pk>/editar/', views.editar_tipo_servico, name='editar_tipo_servico'),
]
