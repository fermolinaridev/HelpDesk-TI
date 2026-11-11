from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings
from app.models import Papel


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_login_retorna_token_que_identifica_o_usuario(client, make_user, senha):
    user = make_user(Papel.TECNICO)

    resp = client.post("/auth/login", data={"username": user.email, "password": senha})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json() == {"id": user.id, "nome": user.nome, "email": user.email, "papel": "tecnico"}


def test_login_ignora_maiusculas_no_email(client, solicitante, senha):
    resp = client.post(
        "/auth/login", data={"username": solicitante.email.upper(), "password": senha}
    )
    assert resp.status_code == 200


def test_login_com_senha_errada_retorna_401(client, solicitante):
    resp = client.post(
        "/auth/login", data={"username": solicitante.email, "password": "senha-errada"}
    )
    assert resp.status_code == 401


def test_login_com_email_inexistente_retorna_401(client, senha):
    resp = client.post(
        "/auth/login", data={"username": "ninguem@escola.example.com", "password": senha}
    )
    assert resp.status_code == 401


def test_rota_protegida_sem_token_retorna_401(client):
    assert client.get("/tickets").status_code == 401


def test_token_invalido_retorna_401(client):
    resp = client.get("/tickets", headers={"Authorization": "Bearer token-falso"})
    assert resp.status_code == 401


def test_token_expirado_retorna_401(client, solicitante):
    expirado = jwt.encode(
        {"sub": str(solicitante.id), "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    resp = client.get("/tickets", headers={"Authorization": f"Bearer {expirado}"})
    assert resp.status_code == 401


def test_token_assinado_com_outra_chave_retorna_401(client, solicitante):
    forjado = jwt.encode(
        {"sub": str(solicitante.id), "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "chave-de-um-atacante-com-mais-de-32-bytes",
        algorithm="HS256",
    )
    resp = client.get("/tickets", headers={"Authorization": f"Bearer {forjado}"})
    assert resp.status_code == 401
