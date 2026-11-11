import pytest

from app.models import Category, Papel


@pytest.fixture
def abrir_chamado(client, auth, equipamento):
    def _abrir(user, titulo="Projetor não liga"):
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
def categoria(db):
    projetor = Category(nome="projetor", sla_horas=8)
    db.add(projetor)
    db.commit()
    return projetor


# --- Abertura ---


def test_solicitante_abre_chamado_com_valores_iniciais(abrir_chamado, solicitante, equipamento):
    chamado = abrir_chamado(solicitante)

    assert chamado["status"] == "aberto"
    assert chamado["prioridade"] == "media"
    assert chamado["requester_id"] == solicitante.id
    assert chamado["equipment_id"] == equipamento.id
    assert chamado["assignee_id"] is None
    assert chamado["category_id"] is None
    assert chamado["criado_em"]


def test_chamado_com_equipamento_inexistente_retorna_422(client, solicitante, auth):
    resp = client.post(
        "/tickets",
        json={"titulo": "Rede caiu", "descricao": "Sem internet na sala.", "equipment_id": 999},
        headers=auth(solicitante),
    )
    assert resp.status_code == 422


def test_chamado_com_titulo_curto_retorna_422(client, solicitante, equipamento, auth):
    resp = client.post(
        "/tickets",
        json={"titulo": "ok", "descricao": "Descrição longa o suficiente.", "equipment_id": 1},
        headers=auth(solicitante),
    )
    assert resp.status_code == 422


# --- Visibilidade por papel ---


def test_solicitante_nao_enxerga_chamado_de_outro(client, abrir_chamado, make_user, auth):
    dono, outro = make_user(Papel.SOLICITANTE), make_user(Papel.SOLICITANTE)
    chamado = abrir_chamado(dono)

    assert client.get(f"/tickets/{chamado['id']}", headers=auth(outro)).status_code == 404
    assert client.get("/tickets", headers=auth(outro)).json() == []


def test_solicitante_lista_apenas_os_proprios_chamados(client, abrir_chamado, make_user, auth):
    ana, bruno = make_user(Papel.SOLICITANTE), make_user(Papel.SOLICITANTE)
    do_ana = abrir_chamado(ana)
    abrir_chamado(bruno)

    resp = client.get("/tickets", headers=auth(ana))
    assert [t["id"] for t in resp.json()] == [do_ana["id"]]


def test_tecnico_enxerga_todos_os_chamados(client, abrir_chamado, make_user, tecnico, auth):
    abrir_chamado(make_user(Papel.SOLICITANTE))
    abrir_chamado(make_user(Papel.SOLICITANTE))

    assert len(client.get("/tickets", headers=auth(tecnico)).json()) == 2


def test_filtra_chamados_por_status(client, abrir_chamado, solicitante, tecnico, auth):
    primeiro = abrir_chamado(solicitante, titulo="Impressora travada")
    abrir_chamado(solicitante, titulo="Som sem volume")
    client.patch(
        f"/tickets/{primeiro['id']}", json={"status": "em_atendimento"}, headers=auth(tecnico)
    )

    resp = client.get("/tickets?status=em_atendimento", headers=auth(tecnico))
    assert [t["id"] for t in resp.json()] == [primeiro["id"]]


# --- Atualização ---


def test_tecnico_faz_triagem_do_chamado(
    client, abrir_chamado, solicitante, tecnico, categoria, auth
):
    chamado = abrir_chamado(solicitante)

    resp = client.patch(
        f"/tickets/{chamado['id']}",
        json={
            "status": "em_atendimento",
            "prioridade": "alta",
            "category_id": categoria.id,
            "assignee_id": tecnico.id,
        },
        headers=auth(tecnico),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert (body["status"], body["prioridade"]) == ("em_atendimento", "alta")
    assert (body["category_id"], body["assignee_id"]) == (categoria.id, tecnico.id)


def test_responsavel_precisa_ser_da_equipe_de_ti(client, abrir_chamado, solicitante, tecnico, auth):
    chamado = abrir_chamado(solicitante)
    resp = client.patch(
        f"/tickets/{chamado['id']}", json={"assignee_id": solicitante.id}, headers=auth(tecnico)
    )
    assert resp.status_code == 422


def test_categoria_inexistente_retorna_422(client, abrir_chamado, solicitante, tecnico, auth):
    chamado = abrir_chamado(solicitante)
    resp = client.patch(
        f"/tickets/{chamado['id']}", json={"category_id": 999}, headers=auth(tecnico)
    )
    assert resp.status_code == 422


def test_status_nulo_retorna_422(client, abrir_chamado, solicitante, tecnico, auth):
    chamado = abrir_chamado(solicitante)
    resp = client.patch(f"/tickets/{chamado['id']}", json={"status": None}, headers=auth(tecnico))
    assert resp.status_code == 422


def test_solicitante_nao_altera_status(client, abrir_chamado, solicitante, auth):
    chamado = abrir_chamado(solicitante)
    resp = client.patch(
        f"/tickets/{chamado['id']}", json={"status": "resolvido"}, headers=auth(solicitante)
    )
    assert resp.status_code == 403


def test_solicitante_edita_descricao_enquanto_aberto(
    client, abrir_chamado, solicitante, tecnico, auth
):
    chamado = abrir_chamado(solicitante)
    url = f"/tickets/{chamado['id']}"
    nova = {"descricao": "Liga, mas a imagem fica piscando."}

    assert (
        client.patch(url, json=nova, headers=auth(solicitante)).json()["descricao"]
        == (nova["descricao"])
    )

    client.patch(url, json={"status": "em_atendimento"}, headers=auth(tecnico))
    assert client.patch(url, json=nova, headers=auth(solicitante)).status_code == 409


def test_solicitante_nao_edita_chamado_de_outro(client, abrir_chamado, make_user, auth):
    dono, outro = make_user(Papel.SOLICITANTE), make_user(Papel.SOLICITANTE)
    chamado = abrir_chamado(dono)

    resp = client.patch(
        f"/tickets/{chamado['id']}",
        json={"descricao": "Tentando editar o chamado alheio."},
        headers=auth(outro),
    )
    assert resp.status_code == 404


# --- Exclusão ---


def test_admin_exclui_chamado(client, abrir_chamado, solicitante, admin, auth):
    chamado = abrir_chamado(solicitante)
    url = f"/tickets/{chamado['id']}"

    assert client.delete(url, headers=auth(admin)).status_code == 204
    assert client.get(url, headers=auth(admin)).status_code == 404


def test_tecnico_nao_exclui_chamado(client, abrir_chamado, solicitante, tecnico, auth):
    chamado = abrir_chamado(solicitante)
    assert client.delete(f"/tickets/{chamado['id']}", headers=auth(tecnico)).status_code == 403
