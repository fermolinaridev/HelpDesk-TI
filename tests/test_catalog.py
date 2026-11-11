def test_admin_cadastra_sala_equipamento_e_categoria(client, admin, auth):
    headers = auth(admin)

    sala = client.post("/rooms", json={"nome": "Laboratório 1", "bloco": "A"}, headers=headers)
    assert sala.status_code == 201

    equipamento = client.post(
        "/equipment",
        json={"tipo": "Lousa digital", "patrimonio": "PAT-1234", "room_id": sala.json()["id"]},
        headers=headers,
    )
    assert equipamento.status_code == 201
    assert equipamento.json()["room_id"] == sala.json()["id"]

    categoria = client.post(
        "/categories", json={"nome": "lousa digital", "sla_horas": 24}, headers=headers
    )
    assert categoria.status_code == 201


def test_solicitante_lista_mas_nao_cadastra(client, solicitante, equipamento, auth):
    headers = auth(solicitante)

    assert client.get("/rooms", headers=headers).status_code == 200
    assert client.get("/equipment", headers=headers).json()[0]["id"] == equipamento.id
    assert (
        client.post("/rooms", json={"nome": "Sala 99", "bloco": "Z"}, headers=headers).status_code
        == 403
    )


def test_filtra_equipamentos_por_sala(client, admin, equipamento, auth):
    outra_sala = client.post("/rooms", json={"nome": "Sala 1", "bloco": "C"}, headers=auth(admin))

    resp = client.get(f"/equipment?room_id={outra_sala.json()['id']}", headers=auth(admin))
    assert resp.json() == []

    resp = client.get(f"/equipment?room_id={equipamento.room_id}", headers=auth(admin))
    assert [e["id"] for e in resp.json()] == [equipamento.id]


def test_equipamento_em_sala_inexistente_retorna_422(client, admin, auth):
    resp = client.post(
        "/equipment",
        json={"tipo": "Projetor", "patrimonio": "PAT-9", "room_id": 999},
        headers=auth(admin),
    )
    assert resp.status_code == 422


def test_patrimonio_duplicado_retorna_409(client, admin, equipamento, auth):
    resp = client.post(
        "/equipment",
        json={"tipo": "Projetor", "patrimonio": equipamento.patrimonio, "room_id": 1},
        headers=auth(admin),
    )
    assert resp.status_code == 409


def test_sala_duplicada_no_mesmo_bloco_retorna_409(client, admin, auth):
    sala = {"nome": "Sala 5", "bloco": "D"}
    client.post("/rooms", json=sala, headers=auth(admin))
    assert client.post("/rooms", json=sala, headers=auth(admin)).status_code == 409
