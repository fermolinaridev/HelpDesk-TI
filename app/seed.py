"""Popula o banco com uma escola fictícia para demonstração.

Uso:
    python -m app.seed            # só roda em banco sem chamados
    python -m app.seed --reset    # APAGA todos os dados antes

A senha dos usuários de demonstração vem da variável DEMO_PASSWORD (ou é pedida no terminal).
Todos os nomes, e-mails, salas e patrimônios são inventados.

As sugestões de triagem do seed são geradas pelo classificador por palavras-chave de verdade
(o mesmo da reserva), e a "decisão do técnico" é a categoria e a prioridade corretas de cada
chamado. Assim, a taxa de acerto que aparece nos relatórios é medida, não inventada.
"""

from __future__ import annotations

import argparse
import getpass
import os
import random
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal
from app.models import (
    AIPrediction,
    Category,
    Equipment,
    Papel,
    Prioridade,
    Room,
    Status,
    Ticket,
    TicketEvent,
    User,
)
from app.security import hash_password
from app.triage import Chamado, ClassificadorRegras

DOMINIO = "escola.example.com"  # domínio reservado para exemplos: não é de ninguém
MESES = 6
DIAS_RECENTES = 10
TOTAL_CHAMADOS = 160
ETAPAS = (Status.ABERTO, Status.EM_ATENDIMENTO, Status.RESOLVIDO, Status.FECHADO)

CATEGORIAS = {"projetor": 8, "rede": 4, "impressora": 24, "som": 12, "lousa digital": 12}

SALAS: dict[tuple[str, str], list[str]] = {
    ("A", "Sala 101"): ["Projetor", "Lousa digital"],
    ("A", "Sala 102"): ["Projetor", "Caixa de som"],
    ("A", "Sala 103"): ["Projetor", "Lousa digital"],
    ("A", "Sala 104"): ["Projetor"],
    ("B", "Sala 201"): ["Projetor", "Lousa digital", "Caixa de som"],
    ("B", "Sala 202"): ["Projetor"],
    ("B", "Laboratório de Informática"): ["Roteador Wi-Fi", "Impressora", "Projetor"],
    ("C", "Biblioteca"): ["Impressora", "Roteador Wi-Fi"],
    ("C", "Auditório"): ["Projetor", "Caixa de som", "Mesa de som"],
    ("C", "Sala dos Professores"): ["Impressora", "Roteador Wi-Fi"],
}

EQUIPE = [
    ("Carla Mendes", "tecnico", Papel.TECNICO),
    ("Rafael Torres", "rafael.torres", Papel.TECNICO),
]
PROFESSORES = [
    ("Profa. Ana Ribeiro", "professora"),
    ("Prof. Bruno Costa", "bruno.costa"),
    ("Profa. Juliana Alves", "juliana.alves"),
    ("Prof. Marcos Pereira", "marcos.pereira"),
    ("Profa. Patrícia Gomes", "patricia.gomes"),
    ("Prof. Ricardo Lima", "ricardo.lima"),
    ("Profa. Sofia Martins", "sofia.martins"),
    ("Prof. Tiago Rocha", "tiago.rocha"),
]


@dataclass(frozen=True)
class Modelo:
    """Um tipo de problema: texto do professor + o que a triagem humana decide."""

    titulo: str
    descricao: str
    equipamentos: tuple[str, ...]
    categoria: str
    prioridade: Prioridade


P = Prioridade
MODELOS = [
    Modelo(
        "Projetor não liga",
        "Apertei o botão várias vezes e o projetor não liga. Tenho aula com slides daqui a pouco.",
        ("Projetor",),
        "projetor",
        P.ALTA,
    ),
    Modelo(
        "Imagem do projetor amarelada",
        "As cores estão amareladas e fracas, os alunos do fundo não conseguem ler.",
        ("Projetor",),
        "projetor",
        P.MEDIA,
    ),
    Modelo(
        "Projetor não reconhece o notebook",
        "Conecto o cabo HDMI e aparece 'sem sinal'. Já testei outro notebook.",
        ("Projetor",),
        "projetor",
        P.ALTA,
    ),
    Modelo(
        "Projetor desliga sozinho",
        "Depois de uns 20 minutos o projetor desliga e pisca uma luz vermelha.",
        ("Projetor",),
        "projetor",
        P.MEDIA,
    ),
    Modelo(
        "Controle do projetor sumiu",
        "Não encontro o controle remoto, quando puder verificar se tem outro.",
        ("Projetor",),
        "projetor",
        P.BAIXA,
    ),
    Modelo(
        "Projetor sem som",
        "O vídeo aparece, mas o som não sai pela caixa ligada ao projetor.",
        ("Projetor",),
        "som",
        P.MEDIA,
    ),
    Modelo(
        "Internet caiu",
        "Sem internet na sala, nenhum aluno consegue acessar a plataforma da prova.",
        ("Roteador Wi-Fi",),
        "rede",
        P.CRITICA,
    ),
    Modelo(
        "Wi-Fi muito lento",
        "A internet está lenta demais, as páginas não carregam.",
        ("Roteador Wi-Fi",),
        "rede",
        P.ALTA,
    ),
    Modelo(
        "Wi-Fi cai às vezes",
        "De vez em quando a conexão cai por alguns minutos e depois volta.",
        ("Roteador Wi-Fi",),
        "rede",
        P.BAIXA,
    ),
    Modelo(
        "Computadores sem rede",
        "Nenhum computador do laboratório conecta, aparece cabo de rede desconectado.",
        ("Roteador Wi-Fi",),
        "rede",
        P.CRITICA,
    ),
    Modelo(
        "Impressora atolando papel",
        "Toda folha que imprimo atola no meio. Preciso imprimir a avaliação de amanhã.",
        ("Impressora",),
        "impressora",
        P.ALTA,
    ),
    Modelo(
        "Toner acabando",
        "A impressão está saindo bem clara, acho que é o toner.",
        ("Impressora",),
        "impressora",
        P.BAIXA,
    ),
    Modelo(
        "Impressora offline",
        "O computador diz que a impressora está offline, mas ela está ligada.",
        ("Impressora",),
        "impressora",
        P.MEDIA,
    ),
    Modelo(
        "Cheiro de queimado na impressora",
        "Saiu um pouco de fumaça da impressora e tem cheiro de queimado. Já desliguei da tomada.",
        ("Impressora",),
        "impressora",
        P.CRITICA,
    ),
    Modelo(
        "Caixa de som chiando",
        "A caixa faz um chiado alto quando ligo o microfone.",
        ("Caixa de som", "Mesa de som"),
        "som",
        P.MEDIA,
    ),
    Modelo(
        "Sem som no auditório",
        "Apresentação dos alunos hoje à tarde e o som do auditório não funciona.",
        ("Mesa de som", "Caixa de som"),
        "som",
        P.ALTA,
    ),
    Modelo(
        "Microfone falhando",
        "O microfone sem fio corta a voz às vezes.",
        ("Mesa de som",),
        "som",
        P.BAIXA,
    ),
    Modelo(
        "Lousa não responde ao toque",
        "A lousa liga, mas não responde ao toque em nenhum canto da tela.",
        ("Lousa digital",),
        "lousa digital",
        P.ALTA,
    ),
    Modelo(
        "Caneta da lousa falhando",
        "A caneta da lousa digital falha de vez em quando no meio do traço.",
        ("Lousa digital",),
        "lousa digital",
        P.BAIXA,
    ),
    Modelo(
        "Toque da lousa desalinhado",
        "O ponto aparece longe de onde eu toco, precisa calibrar.",
        ("Lousa digital",),
        "lousa digital",
        P.MEDIA,
    ),
    Modelo(
        "Lousa sem imagem",
        "A tela da lousa ficou preta, mas o computador está ligado.",
        ("Lousa digital",),
        "lousa digital",
        P.ALTA,
    ),
]


def _momento_de_aula(rng: random.Random, dia: datetime, fuso: ZoneInfo) -> datetime:
    """Horário de aula (7h às 18h) no fuso da escola, convertido para UTC."""
    hora = time(rng.randint(7, 17), rng.randint(0, 59))
    return datetime.combine(dia.date(), hora, tzinfo=fuso).astimezone(UTC)


def _dia_letivo(rng: random.Random, agora: datetime, max_dias: int) -> datetime:
    while True:
        dia = agora - timedelta(days=rng.randint(0, max_dias))
        if dia.weekday() < 5:  # seg a sex
            return dia


def _horas(rng: random.Random, media: float) -> timedelta:
    """Duração com cauda longa: a maioria é rápida, alguns chamados demoram muito."""
    return timedelta(hours=rng.lognormvariate(0, 0.8) * media)


def apagar_tudo(db: Session) -> None:
    tabelas = ", ".join(t.name for t in Base.metadata.sorted_tables)
    db.execute(text(f"TRUNCATE {tabelas} RESTART IDENTITY CASCADE"))
    db.expunge_all()  # os objetos que a sessão conhecia não existem mais


def popular(
    db: Session, senha: str, *, semente: int = 42, agora: datetime | None = None
) -> dict[str, int]:
    rng = random.Random(semente)
    fuso = ZoneInfo(settings.timezone)
    agora = agora or datetime.now(UTC)
    senha_hash = hash_password(senha)

    categorias = {nome: Category(nome=nome, sla_horas=sla) for nome, sla in CATEGORIAS.items()}
    db.add_all(categorias.values())

    por_tipo: dict[str, list[Equipment]] = {}
    for n, ((bloco, nome), tipos) in enumerate(SALAS.items(), start=1):
        sala = Room(nome=nome, bloco=bloco)
        for m, tipo in enumerate(tipos, start=1):
            equip = Equipment(tipo=tipo, patrimonio=f"PAT-{n:02d}{m:02d}", room=sala)
            por_tipo.setdefault(tipo, []).append(equip)
        db.add(sala)

    def usuario(nome: str, login: str, papel: Papel) -> User:
        return User(nome=nome, email=f"{login}@{DOMINIO}", senha_hash=senha_hash, papel=papel)

    equipe = [usuario(nome, login, papel) for nome, login, papel in EQUIPE]
    professores = [usuario(nome, login, Papel.SOLICITANTE) for nome, login in PROFESSORES]
    db.add_all([*equipe, *professores])
    db.flush()

    regras = ClassificadorRegras()
    nomes_categorias = sorted(categorias)

    for _ in range(TOTAL_CHAMADOS):
        modelo = rng.choice(MODELOS)
        tipos = [t for t in modelo.equipamentos if t in por_tipo]
        equipamento = rng.choice(por_tipo[rng.choice(tipos)])
        professor = rng.choice(professores)
        tecnico = rng.choice(equipe)
        # Uma parte dos chamados é recente, para a fila ter trabalho em andamento.
        janela = DIAS_RECENTES if rng.random() < 0.2 else MESES * 30
        aberto_em = _momento_de_aula(rng, _dia_letivo(rng, agora, janela), fuso)
        if aberto_em > agora:
            aberto_em -= timedelta(days=7)

        ticket = Ticket(
            titulo=modelo.titulo,
            descricao=modelo.descricao,
            equipment_id=equipamento.id,
            requester_id=professor.id,
            criado_em=aberto_em,
        )
        ticket.events.append(
            TicketEvent(user_id=professor.id, para_status="aberto", criado_em=aberto_em)
        )

        sugestao = regras.classificar(
            Chamado(modelo.titulo, modelo.descricao, equipamento.tipo), nomes_categorias
        )
        prediction = AIPrediction(
            fonte=sugestao.fonte.value,
            categoria_sugerida_id=(
                categorias[sugestao.categoria].id if sugestao.categoria else None
            ),
            prioridade_sugerida=sugestao.prioridade.value,
            justificativa=sugestao.justificativa,
            criado_em=aberto_em + timedelta(seconds=rng.randint(3, 20)),
        )
        ticket.prediction = prediction

        # Até onde o chamado chegou. Os antigos terminaram; os recentes param no meio.
        recente = agora - aberto_em < timedelta(days=DIAS_RECENTES)
        ate = rng.choices(ETAPAS, weights=(3, 3, 2, 2))[0] if recente else Status.FECHADO
        momento = aberto_em
        status = Status.ABERTO

        inicio = momento + _horas(rng, 1.5)
        if ate != Status.ABERTO and inicio < agora:
            # Triagem e início do atendimento.
            ticket.category_id = categorias[modelo.categoria].id
            ticket.prioridade = modelo.prioridade.value
            ticket.assignee_id = tecnico.id
            prediction.categoria_final_id = ticket.category_id
            prediction.prioridade_final = ticket.prioridade
            prediction.avaliado_por_id = tecnico.id
            prediction.avaliado_em = inicio
            momento, status = inicio, Status.EM_ATENDIMENTO
            ticket.events.append(
                TicketEvent(
                    user_id=tecnico.id,
                    de_status="aberto",
                    para_status=status.value,
                    criado_em=momento,
                )
            )

        sla = CATEGORIAS[modelo.categoria]
        while status == Status.EM_ATENDIMENTO and ate in (Status.RESOLVIDO, Status.FECHADO):
            resolvido = momento + _horas(rng, sla * 0.55)
            if resolvido > agora:
                break
            momento, status = resolvido, Status.RESOLVIDO
            ticket.events.append(
                TicketEvent(
                    user_id=tecnico.id,
                    de_status="em_atendimento",
                    para_status=status.value,
                    criado_em=momento,
                    comentario="Problema resolvido e testado na sala.",
                )
            )
            seguinte = momento + _horas(rng, 10)
            if ate != Status.FECHADO or seguinte > agora:
                break
            if rng.random() < 0.08:  # o professor reabre: voltou a acontecer
                momento, status = seguinte, Status.EM_ATENDIMENTO
                ticket.events.append(
                    TicketEvent(
                        user_id=professor.id,
                        de_status="resolvido",
                        para_status=status.value,
                        criado_em=momento,
                        comentario="Voltou a acontecer na aula seguinte.",
                    )
                )
            else:
                momento, status = seguinte, Status.FECHADO
                ticket.events.append(
                    TicketEvent(
                        user_id=professor.id,
                        de_status="resolvido",
                        para_status=status.value,
                        criado_em=momento,
                    )
                )

        ticket.status = status.value
        db.add(ticket)

    db.flush()
    return {
        "usuarios": len(equipe) + len(professores),
        "salas": len(SALAS),
        "chamados": TOTAL_CHAMADOS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.seed", description=__doc__.split("\n")[0])
    parser.add_argument("--reset", action="store_true", help="apaga TODOS os dados antes")
    parser.add_argument(
        "--se-vazio",
        action="store_true",
        help="não faz nada (e não dá erro) se o banco já tiver chamados; útil no deploy",
    )
    args = parser.parse_args()

    senha = os.environ.get("DEMO_PASSWORD") or getpass.getpass("Senha dos usuários demo: ")
    if len(senha) < 8:
        sys.exit("A senha precisa ter pelo menos 8 caracteres.")

    with SessionLocal() as db:
        if args.reset:
            apagar_tudo(db)
        elif db.scalar(select(func.count()).select_from(Ticket)):
            if args.se_vazio:
                print("O banco já tem chamados; seed ignorado.")
                return
            sys.exit("O banco já tem chamados. Use --reset para apagar tudo e popular de novo.")
        resumo = popular(db, senha)
        db.commit()

    print(
        f"Seed criado: {resumo['chamados']} chamados, {resumo['salas']} salas e "
        f"{resumo['usuarios']} usuários (dados fictícios).\n"
        f"Técnica: tecnico@{DOMINIO}  |  Professora: professora@{DOMINIO}"
    )


if __name__ == "__main__":
    main()
