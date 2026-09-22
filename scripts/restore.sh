#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

BACKUP_ROOT="$PROJECT_DIR/backups"

cd "$PROJECT_DIR"

if [[ ! -f "docker-compose.yaml" ]]; then
    echo "ERRO: docker-compose.yaml não encontrado em:"
    echo "$PROJECT_DIR"
    exit 1
fi

# ---------------------------------------------------------
# Escolha do backup
# ---------------------------------------------------------

if [[ $# -gt 0 ]]; then
    BACKUP_SOURCE="$1"

    if [[ "$BACKUP_SOURCE" != /* ]]; then
        BACKUP_SOURCE="$PROJECT_DIR/$BACKUP_SOURCE"
    fi
else
    if [[ ! -d "$BACKUP_ROOT" ]]; then
        echo "ERRO: nenhum backup encontrado."
        exit 1
    fi

    BACKUP_SOURCE="$(
        find "$BACKUP_ROOT" \
            -mindepth 1 \
            -maxdepth 1 \
            -type f \
            -name '????-??-??_??-??-??.tar.gz' \
            | sort \
            | tail -n 1
    )"
fi

if [[ -z "${BACKUP_SOURCE:-}" || ! -f "$BACKUP_SOURCE" ]]; then
    echo "ERRO: backup não encontrado."
    exit 1
fi

BACKUP_DIR="$(mktemp -d)"
trap 'rm -rf -- "$BACKUP_DIR"' EXIT
echo "Extraindo backup: $BACKUP_SOURCE"
tar -xzf "$BACKUP_SOURCE" -C "$BACKUP_DIR"

echo "========================================"
echo " Project Hectare - Restore"
echo "========================================"
echo
echo "Projeto : $PROJECT_DIR"
echo "Backup  : $BACKUP_SOURCE"
echo

if [[ ! -s "$BACKUP_DIR/database.dump" ]]; then
    echo "ERRO: database.dump não encontrado ou está vazio."
    exit 1
fi

if [[ ! -f "$BACKUP_DIR/media.tar.gz" ]]; then
    echo "ERRO: media.tar.gz não encontrado."
    exit 1
fi

# ---------------------------------------------------------
# .env
# ---------------------------------------------------------

if [[ ! -f ".env" ]]; then
    if [[ -f "$BACKUP_DIR/.env" ]]; then
        echo "Restaurando .env do backup..."

        cp "$BACKUP_DIR/.env" .env
        chmod 600 .env
    else
        echo "ERRO: nenhum .env disponível."
        exit 1
    fi
else
    echo ".env atual encontrado. Mantendo configuração atual."
fi

echo

# ---------------------------------------------------------
# Para serviços que podem alterar dados
# ---------------------------------------------------------

echo "[1/6] Parando aplicação..."

docker compose stop web caddy redis 2>/dev/null || true

# ---------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------

echo "[2/6] Iniciando PostgreSQL..."

docker compose up -d db

echo "Aguardando PostgreSQL..."

until docker compose exec -T db sh -c \
    'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    >/dev/null 2>&1
do
    sleep 2
done

echo "[3/6] Restaurando PostgreSQL..."

docker compose exec -T db sh -c \
    'pg_restore \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges' \
    < "$BACKUP_DIR/database.dump"

# ---------------------------------------------------------
# Media
# ---------------------------------------------------------

echo "[4/6] Restaurando mídias..."

docker compose run \
    --rm \
    --no-deps \
    --entrypoint sh \
    web \
    -c '
        find /app/media -mindepth 1 -delete
        tar xzf - -C /app/media
    ' \
    < "$BACKUP_DIR/media.tar.gz"

# ---------------------------------------------------------
# Caddy
# ---------------------------------------------------------

# if [[ -s "$BACKUP_DIR/caddy-data.tar.gz" ]]; then

#     echo "[5/6] Restaurando dados do Caddy..."

#     docker compose run \
#         --rm \
#         --no-deps \
#         --entrypoint sh \
#         caddy \
#         -c '
#             find /data -mindepth 1 -delete
#             tar xzf - -C /data
#         ' \
#         < "$BACKUP_DIR/caddy-data.tar.gz"

# else
#     echo "[5/6] Backup do Caddy não encontrado. Ignorando."
# fi

## Avaliar a Nescessidade

# ---------------------------------------------------------
# Inicialização
# ---------------------------------------------------------

echo "[6/6] Iniciando Project Hectare..."

docker compose up -d

echo
echo "========================================"
echo " Restore concluído"
echo "========================================"
echo

docker compose ps
