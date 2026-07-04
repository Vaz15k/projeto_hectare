#!/bin/sh
set -eu

echo "Aplicando migrações do banco de dados..."
python manage.py migrate --noinput

echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "Iniciando aplicação..."
exec "$@"
