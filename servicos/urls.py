from django.urls import path
from servicos import views

urlpatterns = [
    path('', views.listar_servicos, name='listar_servicos'),
    path('criar/', views.criar_servico, name='criar_servico'),
    path('<int:pk>/editar/', views.editar_servico, name='editar_servico'),
    path('<int:pk>/deletar/', views.deletar_servico, name='deletar_servico'),
    path('<int:pk>/', views.detalhar_servico, name='detalhar_servico'),
    path('<int:pk>/pdf/', views.exportar_servico_pdf, name='exportar_servico_pdf'),

    path('tipos/', views.listar_tipos_servico, name='listar_tipos_servico'),
    path('tipos/criar/', views.criar_tipo_servico, name='criar_tipo_servico'),
    path('tipos/<int:pk>/editar/', views.editar_tipo_servico, name='editar_tipo_servico'),
]
