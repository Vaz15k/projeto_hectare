#!/bin/sh
set -eu

echo "Aplicando migrações do banco de dados..."
python manage.py migrate --noinput

echo "Iniciando aplicação..."
exec "$@"
