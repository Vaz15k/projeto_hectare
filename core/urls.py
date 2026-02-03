from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('tipos_servico/criar/', views.criar_tipo_servico, name='criar_tipo_servico'),
    path('tipos_servico/', views.listar_tipos_servico, name='listar_tipos_servico'),
    path('tipos_servico/<int:pk>/editar/', views.editar_tipo_servico, name='editar_tipo_servico'),

    path('servicos/', views.listar_servicos, name='listar_servicos'),
    path('servicos/criar/', views.criar_servico, name='criar_servico'),
    path('servicos/<int:pk>/editar/', views.editar_servico, name='editar_servico'),
    path('servicos/<int:pk>/deletar/', views.deletar_servico, name='deletar_servico'),

    path('clientes/', views.listar_clientes, name='listar_clientes'),
    path('clientes/criar/', views.criar_cliente, name='criar_cliente'),
    path('clientes/<int:pk>/editar/', views.editar_cliente, name='editar_cliente'),

    path('empregados/', views.listar_empregados, name='listar_empregados'),
    path('empregados/criar/', views.criar_empregado, name='criar_empregado'),
    path('empregados/<int:pk>/editar/', views.editar_empregado, name='editar_empregado'),
]