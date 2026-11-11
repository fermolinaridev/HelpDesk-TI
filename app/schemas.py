from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import Papel, Prioridade, Status


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class InputModel(BaseModel):
    # Enums viram strings simples ao chegar no banco ('aberto', não Status.ABERTO).
    # extra="forbid": campo desconhecido (ou proibido, como status no PATCH) vira 422, e não
    # é ignorado em silêncio.
    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True, extra="forbid")


# --- Auth / usuários ---


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(InputModel):
    model_config = ConfigDict(str_strip_whitespace=False)  # não altera a senha digitada

    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    # bcrypt só considera os primeiros 72 bytes da senha.
    senha: str = Field(min_length=8, max_length=64)
    papel: Papel = Papel.SOLICITANTE


class UserOut(ORMModel):
    id: int
    nome: str
    email: EmailStr
    papel: Papel


# --- Salas, equipamentos e categorias ---


class RoomCreate(InputModel):
    nome: str = Field(min_length=1, max_length=80)
    bloco: str = Field(min_length=1, max_length=40)


class RoomOut(ORMModel):
    id: int
    nome: str
    bloco: str


class EquipmentCreate(InputModel):
    tipo: str = Field(min_length=2, max_length=60)
    patrimonio: str = Field(min_length=1, max_length=40)
    room_id: int


class EquipmentOut(ORMModel):
    id: int
    tipo: str
    patrimonio: str
    room_id: int


class CategoryCreate(InputModel):
    nome: str = Field(min_length=2, max_length=60)
    sla_horas: int = Field(gt=0, le=720)


class CategoryOut(ORMModel):
    id: int
    nome: str
    sla_horas: int


# --- Chamados ---


class TicketCreate(InputModel):
    titulo: str = Field(min_length=5, max_length=150)
    descricao: str = Field(min_length=10, max_length=5000)
    equipment_id: int


class TicketUpdate(InputModel):
    """Campos opcionais: só o que vier no corpo é alterado.

    O status não muda por aqui, e sim em POST /tickets/{id}/status, que valida o fluxo
    e grava o histórico.
    """

    titulo: str | None = Field(default=None, min_length=5, max_length=150)
    descricao: str | None = Field(default=None, min_length=10, max_length=5000)
    prioridade: Prioridade | None = None
    category_id: int | None = None
    assignee_id: int | None = None

    @model_validator(mode="after")
    def _campos_obrigatorios_nao_nulos(self) -> Self:
        # category_id e assignee_id aceitam null (remover categoria/responsável); os demais não.
        for campo in ("titulo", "descricao", "prioridade"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"'{campo}' não pode ser nulo")
        return self


class TicketOut(ORMModel):
    id: int
    titulo: str
    descricao: str
    status: Status
    prioridade: Prioridade
    category_id: int | None
    equipment_id: int
    requester_id: int
    assignee_id: int | None
    criado_em: datetime


class StatusChange(InputModel):
    status: Status
    comentario: str | None = Field(default=None, max_length=2000)


class UserBrief(ORMModel):
    id: int
    nome: str
    papel: Papel


class TicketEventOut(ORMModel):
    id: int
    de_status: Status | None
    para_status: Status
    comentario: str | None
    criado_em: datetime
    autor: UserBrief


# --- Relatórios ---


class TempoResolucao(BaseModel):
    categoria: str
    resolvidos: int
    horas_media: float | None
    horas_mediana: float | None
    pct_no_sla: float | None


class TempoResolucaoOut(BaseModel):
    geral: TempoResolucao
    por_categoria: list[TempoResolucao]


class EquipamentoRanking(BaseModel):
    posicao: int
    equipment_id: int
    tipo: str
    patrimonio: str
    sala: str
    bloco: str
    chamados: int


class ChamadosPorSala(BaseModel):
    room_id: int
    bloco: str
    sala: str
    chamados: int
    em_aberto: int
    pct_do_total: float | None


class ChamadosPorMes(BaseModel):
    mes: str  # AAAA-MM
    chamados: int
    variacao: int | None  # diferença para o mês anterior
    acumulado: int
