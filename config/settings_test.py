import os

os.environ.setdefault('SECRET_KEY', 'chave-exclusiva-dos-testes-locais')

from .settings import *

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
# LocMem tem incremento atômico no processo de teste, mas não entre processos.
SILENCED_SYSTEM_CHECKS = ['django_ratelimit.E003', 'django_ratelimit.W001']
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
SECURE_SSL_REDIRECT = False
ALLOWED_HOSTS = ['testserver', 'localhost']
