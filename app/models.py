from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Papel(StrEnum):
    SOLICITANTE = "solicitante"
    TECNICO = "tecnico"
    ADMIN = "admin"


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
