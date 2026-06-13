from django.urls import path
from funcionarios import views

urlpatterns = [
    path('', views.listar_empregados, name='listar_empregados'),
    path('criar/', views.criar_empregado, name='criar_empregado'),
    path('<int:pk>/editar/', views.editar_empregado, name='editar_empregado'),
]
