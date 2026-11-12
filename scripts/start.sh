#!/bin/sh
# Sobe o serviço no deploy: migrações, seed fictício (se pedido) e o servidor.
set -e

alembic upgrade head

# Com DEMO_PASSWORD definida, popula a escola fictícia na primeira subida.
# Nas seguintes, o banco já tem chamados e o seed não faz nada.
if [ -n "$DEMO_PASSWORD" ]; then
  python -m app.seed --se-vazio
fi

# PORT é definida pela plataforma (Render, Railway, Fly); 8000 no resto.
exec uvicorn app.web:site --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
