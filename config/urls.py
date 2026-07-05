"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from authentication.views import login_ratelimit
from core.views import protected_media
from servicos.views import home

# O login do admin autentica contra a mesma base de usuários que a tela de
# login principal; sem isto ele contornaria o rate limit de tentativas.
admin.site.login = login_ratelimit(admin.site.login)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
    path('media/<path:path>', protected_media, name='protected_media'),

    path('', home, name='home'),
    path('servicos/', include('servicos.urls')),
    path('clientes/', include('clientes.urls')),
    path('empregados/', include('funcionarios.urls')),
    path('configuracoes/', include('core.urls')),
]
