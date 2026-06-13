from django.urls import path
from clientes import views

urlpatterns = [
    path('', views.listar_clientes, name='listar_clientes'),
    path('criar/', views.criar_cliente, name='criar_cliente'),
    path('<int:pk>/editar/', views.editar_cliente, name='editar_cliente'),
    path('<int:pk>/maquinas/', views.maquinas_cliente, name='maquinas_cliente'),
]
