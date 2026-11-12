from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Papel(StrEnum):
    SOLICITANTE = "solicitante"
    TECNICO = "tecnico"
    ADMIN = "admin"


class FonteIA(StrEnum):
    LLM = "llm"  # sugestão do modelo de linguagem
    REGRAS = "regras"  # classificador de reserva por palavras-chave


class Status(StrEnum):
    ABERTO = "aberto"
    EM_ATENDIMENTO = "em_atendimento"
    RESOLVIDO = "resolvido"
    FECHADO = "fechado"


class Prioridade(StrEnum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


def _check_in(column: str, enum: type[StrEnum]) -> str:
    values = ", ".join(f"'{member.value}'" for member in enum)
    return f"{column} IN ({values})"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint(_check_in("papel", Papel), name="papel_valido"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    papel: Mapped[str] = mapped_column(String(20), default=Papel.SOLICITANTE.value)


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("bloco", "nome", name="uq_rooms_bloco_nome"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80))
    bloco: Mapped[str] = mapped_column(String(40))

    equipment: Mapped[list["Equipment"]] = relationship(back_populates="room")


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(60))
    patrimonio: Mapped[str] = mapped_column(String(40), unique=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)

    room: Mapped[Room] = relationship(back_populates="equipment")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (CheckConstraint("sla_horas > 0", name="sla_positivo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True)
    sla_horas: Mapped[int]


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(_check_in("status", Status), name="status_valido"),
        CheckConstraint(_check_in("prioridade", Prioridade), name="prioridade_valida"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(150))
    descricao: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=Status.ABERTO.value, index=True)
    prioridade: Mapped[str] = mapped_column(String(10), default=Prioridade.MEDIA.value)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[Category | None] = relationship()
    equipment: Mapped[Equipment] = relationship()
    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    # O banco apaga o histórico junto com o chamado (ON DELETE CASCADE).
    events: Mapped[list["TicketEvent"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True
    )
    prediction: Mapped["AIPrediction | None"] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True
    )


class TicketEvent(Base):
    """Histórico do chamado: cada linha é uma mudança de status (ou a abertura)."""

    __tablename__ = "ticket_events"
    __table_args__ = (
        CheckConstraint(_check_in("para_status", Status), name="para_status_valido"),
        CheckConstraint(
            f"de_status IS NULL OR {_check_in('de_status', Status)}", name="de_status_valido"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    de_status: Mapped[str | None] = mapped_column(String(20))  # NULL = abertura do chamado
    para_status: Mapped[str] = mapped_column(String(20))
    comentario: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped[Ticket] = relationship(back_populates="events")
    autor: Mapped[User] = relationship()


class AIPrediction(Base):
    """Sugestão de triagem da IA para um chamado e o que a equipe de TI decidiu depois.

    A sugestão nunca altera o chamado sozinha: o técnico confirma ou corrige na triagem.
    Comparar o sugerido com o final (categoria_final_id, prioridade_final) dá a taxa de acerto.
    """

    __tablename__ = "ai_predictions"
    __table_args__ = (
        CheckConstraint(_check_in("fonte", FonteIA), name="fonte_valida"),
        CheckConstraint(
            _check_in("prioridade_sugerida", Prioridade), name="prioridade_sugerida_valida"
        ),
        CheckConstraint(
            f"prioridade_final IS NULL OR {_check_in('prioridade_final', Prioridade)}",
            name="prioridade_final_valida",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), unique=True
    )
    fonte: Mapped[str] = mapped_column(String(10))
    modelo: Mapped[str | None] = mapped_column(String(60))
    categoria_sugerida_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    prioridade_sugerida: Mapped[str] = mapped_column(String(10))
    justificativa: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Preenchidos quando a equipe de TI faz a triagem do chamado.
    categoria_final_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    prioridade_final: Mapped[str | None] = mapped_column(String(10))
    avaliado_por_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    avaliado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ticket: Mapped[Ticket] = relationship(back_populates="prediction")
    categoria_sugerida: Mapped[Category | None] = relationship(foreign_keys=[categoria_sugerida_id])
