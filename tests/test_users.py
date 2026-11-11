import pytest

from app.models import Papel

NOVO_USUARIO = {
    "nome": "Profa. Ana Teste",
    "email": "Ana.Teste@Escola.example.com",
    "senha": "outra-senha-123",
    "papel": "solicitante",
}


def test_admin_cria_usuario_sem_expor_a_senha(client, admin, auth):
    resp = client.post("/users", json=NOVO_USUARIO, headers=auth(admin))

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "ana.teste@escola.example.com"
    assert body["papel"] == "solicitante"
    assert "senha" not in body and "senha_hash" not in body


def test_usuario_criado_consegue_fazer_login(client, admin, auth):
    client.post("/users", json=NOVO_USUARIO, headers=auth(admin))

    resp = client.post(
        "/auth/login",
        data={"username": NOVO_USUARIO["email"], "password": NOVO_USUARIO["senha"]},
    )
    assert resp.status_code == 200


@pytest.mark.parametrize("papel", [Papel.SOLICITANTE, Papel.TECNICO])
def test_somente_admin_cria_usuario(client, make_user, auth, papel):
    resp = client.post("/users", json=NOVO_USUARIO, headers=auth(make_user(papel)))
    assert resp.status_code == 403


def test_email_duplicado_retorna_409(client, admin, auth):
    client.post("/users", json=NOVO_USUARIO, headers=auth(admin))
    resp = client.post("/users", json=NOVO_USUARIO, headers=auth(admin))
    assert resp.status_code == 409


@pytest.mark.parametrize(
    "campo, valor",
    [("senha", "curta"), ("papel", "diretor"), ("email", "nao-e-email")],
)
def test_dados_invalidos_retornam_422(client, admin, auth, campo, valor):
    resp = client.post("/users", json={**NOVO_USUARIO, campo: valor}, headers=auth(admin))
    assert resp.status_code == 422


def test_admin_lista_usuarios(client, admin, tecnico, auth):
    resp = client.get("/users", headers=auth(admin))
    assert resp.status_code == 200
    assert {u["id"] for u in resp.json()} == {admin.id, tecnico.id}


def test_tecnico_nao_lista_usuarios(client, tecnico, auth):
    assert client.get("/users", headers=auth(tecnico)).status_code == 403
