"""Relatórios SQL com dados de tempo controlado.

Os chamados são inseridos direto no banco, com datas fixas, para que médias, SLA e
agrupamentos por mês tenham resultados exatos.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.models import Category, Equipment, Papel, Room, Ticket, TicketEvent

ABERTURA = datetime(2026, 3, 10, 13, 0, tzinfo=UTC)


@pytest.fixture
def criar_chamado(db, solicitante, tecnico):
    def _criar(equipamento, *, criado_em=ABERTURA, categoria=None, historico=()):
        """historico: sequência de (novo_status, horas_após_a_abertura)."""
        ticket = Ticket(
            titulo="Chamado de teste",
            descricao="Descrição do chamado de teste.",
            equipment_id=equipamento.id,
            requester_id=solicitante.id,
            category_id=categoria.id if categoria else None,
            criado_em=criado_em,
        )
        ticket.events.append(
            TicketEvent(
                user_id=solicitante.id, de_status=None, para_status="aberto", criado_em=criado_em
            )
        )
        atual = "aberto"
        for novo, horas in historico:
            ticket.events.append(
                TicketEvent(
                    user_id=tecnico.id,
                    de_status=atual,
                    para_status=novo,
                    criado_em=criado_em + timedelta(hours=horas),
                )
            )
            atual = novo
        ticket.status = atual
        db.add(ticket)
        db.commit()
        return ticket

    return _criar


@pytest.fixture
def cenario(db, criar_chamado):
    """3 salas, 4 equipamentos, 5 chamados.

    | chamado | equipamento | categoria (SLA) | situação                          |
    | 1       | PAT-1       | projetor (8h)   | resolvido em 4h (dentro do SLA)   |
    | 2       | PAT-1       | projetor (8h)   | resolvido em 12h (fora do SLA)    |
    | 3       | PAT-2       | -               | resolvido em 2h e fechado         |
    | 4       | PAT-3       | rede (4h)       | reaberto; resolvido de vez em 5h  |
    | 5       | PAT-1       | projetor (8h)   | ainda em atendimento              |
    """
    a1, b1, c1 = Room(nome="A1", bloco="A"), Room(nome="B1", bloco="B"), Room(nome="C1", bloco="C")
    pat1 = Equipment(tipo="Projetor", patrimonio="PAT-1", room=a1)
    pat2 = Equipment(tipo="Lousa digital", patrimonio="PAT-2", room=a1)
    pat3 = Equipment(tipo="Impressora", patrimonio="PAT-3", room=b1)
    pat4 = Equipment(tipo="Caixa de som", patrimonio="PAT-4", room=c1)
    projetor = Category(nome="projetor", sla_horas=8)
    rede = Category(nome="rede", sla_horas=4)
    db.add_all([a1, b1, c1, pat1, pat2, pat3, pat4, projetor, rede])
    db.commit()

    criar_chamado(pat1, categoria=projetor, historico=[("em_atendimento", 1), ("resolvido", 4)])
    criar_chamado(pat1, categoria=projetor, historico=[("em_atendimento", 1), ("resolvido", 12)])
    criar_chamado(pat2, historico=[("em_atendimento", 1), ("resolvido", 2), ("fechado", 3)])
    criar_chamado(
        pat3,
        categoria=rede,
        historico=[
            ("em_atendimento", 1),
            ("resolvido", 2),
            ("em_atendimento", 3),
            ("resolvido", 5),
        ],
    )
    criar_chamado(pat1, categoria=projetor, historico=[("em_atendimento", 1)])


def test_tempo_de_resolucao_por_categoria(client, auth, tecnico, cenario):
    resp = client.get("/reports/tempo-resolucao", headers=auth(tecnico))
    assert resp.status_code == 200
    body = resp.json()

    assert body["por_categoria"] == [
        {
            "categoria": "projetor",
            "resolvidos": 2,
            "horas_media": 8.0,
            "horas_mediana": 8.0,
            "pct_no_sla": 50.0,
        },
        {
            # Conta a resolução definitiva (5h), e não a primeira (2h).
            "categoria": "rede",
            "resolvidos": 1,
            "horas_media": 5.0,
            "horas_mediana": 5.0,
            "pct_no_sla": 0.0,
        },
        {
            "categoria": "sem categoria",
            "resolvidos": 1,
            "horas_media": 2.0,
            "horas_mediana": 2.0,
            "pct_no_sla": None,
        },
    ]
    assert body["geral"] == {
        "categoria": "todas",
        "resolvidos": 4,
        "horas_media": 5.75,  # (4 + 12 + 2 + 5) / 4
        "horas_mediana": 4.5,  # mediana de [2, 4, 5, 12]
        "pct_no_sla": 33.3,  # 1 de 3 chamados com SLA
    }


def test_ranking_de_equipamentos_com_empate(client, auth, tecnico, cenario):
    resp = client.get("/reports/equipamentos", headers=auth(tecnico))

    assert [(e["posicao"], e["patrimonio"], e["chamados"]) for e in resp.json()] == [
        (1, "PAT-1", 3),
        (2, "PAT-2", 1),
        (2, "PAT-3", 1),
    ]
    assert resp.json()[0]["sala"] == "A1"


def test_ranking_respeita_limite(client, auth, tecnico, cenario):
    resp = client.get("/reports/equipamentos?limite=1", headers=auth(tecnico))
    assert [e["patrimonio"] for e in resp.json()] == ["PAT-1"]


def test_chamados_por_sala_inclui_salas_sem_chamados(client, auth, tecnico, cenario):
    resp = client.get("/reports/salas", headers=auth(tecnico))

    assert [(s["sala"], s["chamados"], s["em_aberto"], s["pct_do_total"]) for s in resp.json()] == [
        ("A1", 4, 1, 80.0),
        ("B1", 1, 0, 20.0),
        ("C1", 0, 0, 0.0),
    ]


def test_chamados_por_mes_preenche_meses_vazios_e_usa_fuso_local(
    client, auth, tecnico, equipamento, criar_chamado
):
    criar_chamado(equipamento, criado_em=datetime(2026, 1, 15, 12, 0, tzinfo=UTC))
    # 02:00 UTC de 1º/fev = 23:00 de 31/jan em São Paulo: conta em janeiro.
    criar_chamado(equipamento, criado_em=datetime(2026, 2, 1, 2, 0, tzinfo=UTC))
    criar_chamado(equipamento, criado_em=datetime(2026, 3, 5, 12, 0, tzinfo=UTC))

    resp = client.get("/reports/mensal", headers=auth(tecnico))

    assert resp.json() == [
        {"mes": "2026-01", "chamados": 2, "variacao": None, "acumulado": 2},
        {"mes": "2026-02", "chamados": 0, "variacao": -2, "acumulado": 2},
        {"mes": "2026-03", "chamados": 1, "variacao": 1, "acumulado": 3},
    ]


def test_relatorios_com_banco_vazio(client, auth, tecnico):
    headers = auth(tecnico)

    geral = client.get("/reports/tempo-resolucao", headers=headers).json()["geral"]
    assert geral["resolvidos"] == 0 and geral["horas_media"] is None
    assert client.get("/reports/equipamentos", headers=headers).json() == []
    assert client.get("/reports/salas", headers=headers).json() == []
    assert client.get("/reports/mensal", headers=headers).json() == []


@pytest.mark.parametrize("rota", ["tempo-resolucao", "equipamentos", "salas", "mensal"])
def test_solicitante_nao_acessa_relatorios(client, auth, make_user, rota):
    resp = client.get(f"/reports/{rota}", headers=auth(make_user(Papel.SOLICITANTE)))
    assert resp.status_code == 403
