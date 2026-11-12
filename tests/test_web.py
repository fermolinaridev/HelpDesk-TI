"""Deploy em um serviço só: API em /api e o front React em /."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import DEV_JWT_SECRET, Settings, settings
from app.web import criar_site


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id=root></div>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path.parent / "segredo.txt").write_text("não pode vazar", encoding="utf-8")
    return tmp_path


def test_api_fica_em_api(dist):
    client = TestClient(criar_site(dist))
    assert client.get("/api/health").json() == {"status": "ok"}


def test_serve_arquivos_do_build(dist):
    resp = TestClient(criar_site(dist)).get("/assets/app.js")
    assert resp.status_code == 200
    assert resp.text == "console.log(1)"


@pytest.mark.parametrize("rota", ["/", "/chamados/42", "/relatorios"])
def test_rotas_do_react_recebem_o_index(dist, rota):
    resp = TestClient(criar_site(dist)).get(rota)
    assert resp.status_code == 200
    assert "root" in resp.text


def test_nao_serve_arquivo_fora_do_build(dist):
    resp = TestClient(criar_site(dist)).get("/..%2Fsegredo.txt")
    assert "não pode vazar" not in resp.text


def test_nao_sobe_com_a_chave_jwt_de_desenvolvimento(dist, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", DEV_JWT_SECRET)
    with pytest.raises(RuntimeError, match="JWT_SECRET"), TestClient(criar_site(dist)):
        pass


@pytest.mark.parametrize(
    "url",
    [
        "postgres://u:s@host:5432/db",
        "postgresql://u:s@host:5432/db",
        "postgresql+psycopg://u:s@host:5432/db",
    ],
)
def test_url_do_banco_da_plataforma_ganha_o_driver(url):
    assert Settings(database_url=url).database_url == "postgresql+psycopg://u:s@host:5432/db"
