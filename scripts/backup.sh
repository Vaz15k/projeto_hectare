#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

# Diretório onde o script está.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Raiz do projeto = diretório pai de scripts/
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

BACKUP_ROOT="$PROJECT_DIR/backups"

DATE="$(date +"%Y-%m-%d_%H-%M-%S")"
ARCHIVE_PATH="$BACKUP_ROOT/$DATE.tar.gz"

cd "$PROJECT_DIR"

if [[ ! -f "docker-compose.yaml" ]]; then
    echo "ERRO: docker-compose.yaml não encontrado em:"
    echo "$PROJECT_DIR"
    exit 1
fi

mkdir -p "$BACKUP_ROOT"

if [[ -e "$ARCHIVE_PATH" ]]; then
    echo "ERRO: backup já existe: $ARCHIVE_PATH" >&2
    exit 1
fi

BACKUP_DIR="$(mktemp -d "$BACKUP_ROOT/.backup-$DATE.XXXXXX")"
ARCHIVE_TMP=""
trap 'rm -rf -- "$BACKUP_DIR"; rm -f -- "$ARCHIVE_TMP"' EXIT
ARCHIVE_TMP="$(mktemp "$BACKUP_ROOT/.archive-$DATE.XXXXXX")"

echo "========================================"
echo " Project Hectare - Backup"
echo "========================================"
echo
echo "Projeto : $PROJECT_DIR"
echo "Destino : $ARCHIVE_PATH"
echo

echo "[1/4] Backup do PostgreSQL..."

docker compose exec -T db sh -c \
    'pg_dump \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -Fc' \
    > "$BACKUP_DIR/database.dump"

if [[ ! -s "$BACKUP_DIR/database.dump" ]]; then
    echo "ERRO: dump do banco ficou vazio."
    exit 1
fi

echo "[2/4] Backup das mídias..."

docker compose exec -T web \
    tar czf - -C /app/media . \
    > "$BACKUP_DIR/media.tar.gz"

echo "[3/4] Backup dos dados do Caddy..."

docker compose exec -T caddy \
    tar czf - -C /data . \
    > "$BACKUP_DIR/caddy-data.tar.gz"

echo "[4/4] Backup das configurações..."

cp .env "$BACKUP_DIR/.env"
chmod 600 "$BACKUP_DIR/.env"

{
    echo "date=$DATE"

    if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "git_commit=$(git rev-parse HEAD)"
        echo "git_branch=$(git branch --show-current)"
    fi
} > "$BACKUP_DIR/metadata.txt"

echo "Compactando backup..."
tar -czf "$ARCHIVE_TMP" -C "$BACKUP_DIR" .
ln -- "$ARCHIVE_TMP" "$ARCHIVE_PATH"
rm -f -- "$ARCHIVE_TMP"

echo
echo "========================================"
echo " Backup concluído"
echo "========================================"
echo

du -sh "$ARCHIVE_PATH"
ls -lah "$ARCHIVE_PATH"
