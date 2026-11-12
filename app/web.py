"""Ponto de entrada do deploy em um único serviço: API em /api e o front React em /.

No Docker Compose de desenvolvimento quem faz esse papel é o nginx. Em plataformas que rodam
um contêiner só (Render, Railway, Fly), esta app serve o build do front e monta a API sob /api,
mantendo front e API na mesma origem (sem CORS).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.config import DEV_JWT_SECRET, settings
from app.main import app as api


@asynccontextmanager
async def _exigir_configuracao(_: FastAPI) -> AsyncIterator[None]:
    # Em produção, a chave de desenvolvimento deixaria qualquer um forjar um token.
    if settings.jwt_secret == DEV_JWT_SECRET or len(settings.jwt_secret) < 32:
        raise RuntimeError("Defina JWT_SECRET com uma chave aleatória de 32+ caracteres.")
    yield


def criar_site(dist: Path) -> FastAPI:
    site = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=_exigir_configuracao)
    site.mount("/api", api)

    index = dist / "index.html"

    @site.get("/{caminho:path}", include_in_schema=False)
    def front(caminho: str) -> FileResponse:
        arquivo = (dist / caminho).resolve()
        # Arquivo do build (js, css, fontes) existe: serve. Qualquer outra rota é do React
        # Router, então devolve o index.html. resolve() + is_relative_to barra "../".
        if caminho and arquivo.is_relative_to(dist.resolve()) and arquivo.is_file():
            return FileResponse(arquivo)
        if not index.is_file():
            raise HTTPException(404, "Build do front não encontrado")
        return FileResponse(index)

    return site


site = criar_site(Path(settings.frontend_dist))
