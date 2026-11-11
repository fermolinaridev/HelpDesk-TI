"""Fluxo de status e histórico pela API."""

from app.models import Papel


def _historico(client, auth, chamado, user):
    resp = client.get(f"/tickets/{chamado['id']}/events", headers=auth(user))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _post_status(client, auth, chamado, user, status, comentario=None):
    return client.post(
        f"/tickets/{chamado['id']}/status",
        json={"status": status, "comentario": comentario},
        headers=auth(user),
    )


def test_abrir_chamado_registra_evento_de_abertura(client, auth, abrir_chamado, solicitante):
    chamado = abrir_chamado(solicitante)

    [evento] = _historico(client, auth, chamado, solicitante)
    assert (evento["de_status"], evento["para_status"]) == (None, "aberto")
    assert evento["autor"]["id"] == solicitante.id


def test_ciclo_completo_fica_registrado_no_historico(
    client, auth, abrir_chamado, mudar_status, solicitante, tecnico
):
    chamado = abrir_chamado(solicitante)
    mudar_status(chamado, "em_atendimento", tecnico)
    mudar_status(chamado, "resolvido", tecnico, comentario="Cabo HDMI substituído.")
    final = mudar_status(chamado, "fechado", solicitante)

    assert final["status"] == "fechado"
    eventos = _historico(client, auth, chamado, solicitante)
    assert [(e["de_status"], e["para_status"]) for e in eventos] == [
        (None, "aberto"),
        ("aberto", "em_atendimento"),
        ("em_atendimento", "resolvido"),
        ("resolvido", "fechado"),
    ]
    assert [e["autor"]["id"] for e in eventos] == [
        solicitante.id,
        tecnico.id,
        tecnico.id,
        solicitante.id,
    ]
    assert eventos[2]["comentario"] == "Cabo HDMI substituído."


def test_aberto_direto_para_fechado_retorna_409_e_nada_muda(
    client, auth, abrir_chamado, solicitante, admin
):
    chamado = abrir_chamado(solicitante)

    resp = _post_status(client, auth, chamado, admin, "fechado", "Fechando sem atender")

    assert resp.status_code == 409
    atual = client.get(f"/tickets/{chamado['id']}", headers=auth(admin)).json()
    assert atual["status"] == "aberto"
    assert len(_historico(client, auth, chamado, admin)) == 1


def test_solicitante_nao_inicia_atendimento(client, auth, abrir_chamado, solicitante):
    chamado = abrir_chamado(solicitante)
    resp = _post_status(client, auth, chamado, solicitante, "em_atendimento")
    assert resp.status_code == 403


def test_resolver_sem_comentario_retorna_422(
    client, auth, abrir_chamado, mudar_status, solicitante, tecnico
):
    chamado = abrir_chamado(solicitante)
    mudar_status(chamado, "em_atendimento", tecnico)

    resp = _post_status(client, auth, chamado, tecnico, "resolvido")
    assert resp.status_code == 422


def test_status_desconhecido_retorna_422(client, auth, abrir_chamado, solicitante, tecnico):
    chamado = abrir_chamado(solicitante)
    resp = _post_status(client, auth, chamado, tecnico, "pendente")
    assert resp.status_code == 422


def test_quem_inicia_o_atendimento_vira_responsavel(
    abrir_chamado, mudar_status, solicitante, tecnico
):
    chamado = abrir_chamado(solicitante)
    assert mudar_status(chamado, "em_atendimento", tecnico)["assignee_id"] == tecnico.id


def test_responsavel_ja_definido_e_mantido(
    client, auth, abrir_chamado, mudar_status, make_user, solicitante, admin
):
    chamado = abrir_chamado(solicitante)
    designado = make_user(Papel.TECNICO)
    client.patch(
        f"/tickets/{chamado['id']}", json={"assignee_id": designado.id}, headers=auth(admin)
    )

    assert mudar_status(chamado, "em_atendimento", admin)["assignee_id"] == designado.id


def test_solicitante_reabre_chamado_resolvido(
    client, auth, abrir_chamado, mudar_status, solicitante, tecnico
):
    chamado = abrir_chamado(solicitante)
    mudar_status(chamado, "em_atendimento", tecnico)
    mudar_status(chamado, "resolvido", tecnico, comentario="Driver reinstalado.")

    sem_motivo = _post_status(client, auth, chamado, solicitante, "em_atendimento")
    assert sem_motivo.status_code == 422

    reaberto = mudar_status(
        chamado, "em_atendimento", solicitante, comentario="A impressora voltou a travar."
    )
    assert reaberto["status"] == "em_atendimento"
    assert reaberto["assignee_id"] == tecnico.id


def test_solicitante_nao_ve_historico_de_chamado_alheio(client, auth, abrir_chamado, make_user):
    dono, outro = make_user(Papel.SOLICITANTE), make_user(Papel.SOLICITANTE)
    chamado = abrir_chamado(dono)

    resp = client.get(f"/tickets/{chamado['id']}/events", headers=auth(outro))
    assert resp.status_code == 404


def test_solicitante_nao_muda_status_de_chamado_alheio(
    client, auth, abrir_chamado, mudar_status, make_user, tecnico
):
    dono, outro = make_user(Papel.SOLICITANTE), make_user(Papel.SOLICITANTE)
    chamado = abrir_chamado(dono)
    mudar_status(chamado, "em_atendimento", tecnico)
    mudar_status(chamado, "resolvido", tecnico, comentario="Resolvido.")

    resp = _post_status(client, auth, chamado, outro, "fechado")
    assert resp.status_code == 404
