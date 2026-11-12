"""O seed gera uma escola fictícia coerente com as regras do sistema."""

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models import AIPrediction, Status, Ticket
from app.seed import TOTAL_CHAMADOS, apagar_tudo, popular
from app.workflow import TRANSICOES

AGORA = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)


def test_seed_respeita_o_fluxo_de_status(db):
    popular(db, "senha-de-teste-123")
    db.commit()

    tickets = db.scalars(select(Ticket)).all()
    assert len(tickets) == TOTAL_CHAMADOS

    for ticket in tickets:
        eventos = sorted(ticket.events, key=lambda e: (e.criado_em, e.id))
        assert eventos[0].de_status is None and eventos[0].para_status == "aberto"
        assert eventos[0].criado_em == ticket.criado_em
        # Cada mudança é uma transição permitida, na ordem do tempo.
        for anterior, atual in zip(eventos, eventos[1:], strict=False):
            assert atual.de_status == anterior.para_status
            assert Status(atual.para_status) in TRANSICOES[Status(atual.de_status)]
            assert atual.criado_em >= anterior.criado_em
        assert ticket.status == eventos[-1].para_status
        # Resolver e reabrir sempre têm comentário, como a API exige.
        for evento in eventos:
            if (evento.de_status, evento.para_status) in {
                ("em_atendimento", "resolvido"),
                ("resolvido", "em_atendimento"),
            }:
                assert evento.comentario


def test_seed_tem_chamados_em_todas_as_etapas(db):
    popular(db, "senha-de-teste-123", agora=AGORA)
    db.commit()
    contagem = dict(db.execute(select(Ticket.status, func.count()).group_by(Ticket.status)).all())
    assert set(contagem) == {s.value for s in Status}


def test_seed_tem_sugestao_para_todo_chamado_e_parte_avaliada(db):
    popular(db, "senha-de-teste-123")
    db.commit()

    assert db.scalar(select(func.count()).select_from(AIPrediction)) == TOTAL_CHAMADOS
    avaliadas = db.scalars(select(AIPrediction).where(AIPrediction.avaliado_em.is_not(None))).all()
    assert 0 < len(avaliadas) < TOTAL_CHAMADOS
    # Chamado triado tem a decisão gravada igual ao que ficou no chamado.
    for p in avaliadas:
        assert p.categoria_final_id == p.ticket.category_id
        assert p.prioridade_final == p.ticket.prioridade


def test_seed_e_deterministico(db):
    """Mesma semente, mesma escola: a demo é reproduzível."""

    def gerar() -> list[tuple[str, str]]:
        apagar_tudo(db)
        popular(db, "senha-de-teste-123", semente=7, agora=AGORA)
        db.commit()
        return db.execute(select(Ticket.titulo, Ticket.status).order_by(Ticket.id)).all()

    assert gerar() == gerar()
