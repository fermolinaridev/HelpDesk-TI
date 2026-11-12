"""Fixtures dos testes de integração.

Os testes rodam contra um Postgres real (banco helpdesk_test), nunca contra o banco de
desenvolvimento. O schema é criado pelas migrações do Alembic, então os testes também
garantem que as migrações funcionam.
"""

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://helpdesk:helpdesk@localhost:5432/helpdesk_test",
)

import itertools
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import command
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Category, Equipment, Papel, Room, User
from app.security import create_access_token, hash_password
from app.triage import Triagem, get_triagem

ROOT = Path(__file__).resolve().parent.parent
SENHA_PADRAO = "senha-segura-123"
_SENHA_HASH = hash_password(SENHA_PADRAO)  # bcrypt é lento de propósito: calcula uma vez só


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.attributes["configure_logger"] = False
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    yield
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
def _sem_api_de_ia() -> Iterator[None]:
    """Nenhum teste chama a API do modelo de verdade: por padrão, só as regras de reserva.

    Os testes de triagem trocam este dublê pelo deles.
    """
    app.dependency_overrides[get_triagem] = lambda: Triagem(llm=None)
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def senha() -> str:
    return SENHA_PADRAO


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    counter = itertools.count(1)

    def _make(papel: Papel = Papel.SOLICITANTE) -> User:
        n = next(counter)
        user = User(
            nome=f"{papel.value.title()} {n}",
            email=f"{papel.value}{n}@escola.example.com",
            senha_hash=_SENHA_HASH,
            papel=papel.value,
        )
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def auth() -> Callable[[User], dict[str, str]]:
    def _headers(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}

    return _headers


@pytest.fixture
def solicitante(make_user: Callable[..., User]) -> User:
    return make_user(Papel.SOLICITANTE)


@pytest.fixture
def tecnico(make_user: Callable[..., User]) -> User:
    return make_user(Papel.TECNICO)


@pytest.fixture
def admin(make_user: Callable[..., User]) -> User:
    return make_user(Papel.ADMIN)


@pytest.fixture
def equipamento(db: Session) -> Equipment:
    sala = Room(nome="Sala 12", bloco="B")
    projetor = Equipment(tipo="Projetor", patrimonio="PAT-0001", room=sala)
    db.add_all([sala, projetor])
    db.commit()
    return projetor


@pytest.fixture
def categoria(db: Session) -> Category:
    projetor = Category(nome="projetor", sla_horas=8)
    db.add(projetor)
    db.commit()
    return projetor


@pytest.fixture
def abrir_chamado(client, auth, equipamento) -> Callable[..., dict]:
    """Abre um chamado pela API e devolve o JSON da resposta."""

    def _abrir(user: User, titulo: str = "Projetor não liga") -> dict:
        resp = client.post(
            "/tickets",
            json={
                "titulo": titulo,
                "descricao": "O projetor da sala não liga desde a manhã.",
                "equipment_id": equipamento.id,
            },
            headers=auth(user),
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _abrir


@pytest.fixture
def mudar_status(client, auth) -> Callable[..., dict]:
    """Muda o status pela API e exige sucesso (para preparar o cenário do teste)."""

    def _mudar(chamado: dict, status: str, user: User, comentario: str | None = None) -> dict:
        resp = client.post(
            f"/tickets/{chamado['id']}/status",
            json={"status": status, "comentario": comentario},
            headers=auth(user),
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _mudar
