from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.deps import AdminUser, CurrentUser, DbSession
from app.models import Category, Equipment, Papel, Status, Ticket, TicketEvent, User
from app.schemas import StatusChange, TicketCreate, TicketEventOut, TicketOut, TicketUpdate
from app.workflow import (
    ComentarioObrigatorio,
    ErroDeFluxo,
    TransicaoInvalida,
    TransicaoNaoPermitida,
    validar_transicao,
)

router = APIRouter(prefix="/tickets", tags=["chamados"])

# O solicitante só corrige o texto do próprio chamado; a triagem é da equipe de TI.
REQUESTER_EDITABLE = {"titulo", "descricao"}

HTTP_STATUS_DO_ERRO: dict[type[ErroDeFluxo], int] = {
    TransicaoInvalida: status.HTTP_409_CONFLICT,
    TransicaoNaoPermitida: status.HTTP_403_FORBIDDEN,
    ComentarioObrigatorio: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def get_visible_ticket(db: Session, ticket_id: int, user: User, *, lock: bool = False) -> Ticket:
    """Busca o chamado respeitando a visibilidade do papel.

    Para o solicitante, chamado de outra pessoa responde 404 (e não 403),
    para não revelar que aquele id existe. Com lock=True a linha fica travada
    (SELECT ... FOR UPDATE) até o fim da transação.
    """
    ticket = db.get(Ticket, ticket_id, with_for_update=lock)
    if ticket is None or (user.papel == Papel.SOLICITANTE and ticket.requester_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chamado não encontrado")
    return ticket


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(data: TicketCreate, user: CurrentUser, db: DbSession) -> Ticket:
    if db.get(Equipment, data.equipment_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Equipamento não encontrado")

    ticket = Ticket(**data.model_dump(), requester_id=user.id)
    ticket.events.append(
        TicketEvent(user_id=user.id, de_status=None, para_status=Status.ABERTO.value)
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)  # carrega criado_em, preenchido pelo banco
    return ticket


@router.get("", response_model=list[TicketOut])
def list_tickets(
    user: CurrentUser,
    db: DbSession,
    status_filter: Annotated[Status | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[Ticket]:
    stmt = select(Ticket).order_by(Ticket.criado_em.desc(), Ticket.id.desc())
    if user.papel == Papel.SOLICITANTE:
        stmt = stmt.where(Ticket.requester_id == user.id)
    if status_filter is not None:
        stmt = stmt.where(Ticket.status == status_filter.value)
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, user: CurrentUser, db: DbSession) -> Ticket:
    return get_visible_ticket(db, ticket_id, user)


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, data: TicketUpdate, user: CurrentUser, db: DbSession) -> Ticket:
    ticket = get_visible_ticket(db, ticket_id, user)
    changes = data.model_dump(exclude_unset=True)

    if user.papel == Papel.SOLICITANTE:
        if changes.keys() - REQUESTER_EDITABLE:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Solicitante só pode editar título e descrição"
            )
        if ticket.status != Status.ABERTO:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Só é possível editar chamados ainda abertos"
            )

    if ticket.status == Status.FECHADO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Chamado fechado não pode ser alterado")

    if changes.get("category_id") is not None and db.get(Category, changes["category_id"]) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Categoria não encontrada")

    if changes.get("assignee_id") is not None:
        assignee = db.get(User, changes["assignee_id"])
        if assignee is None or assignee.papel == Papel.SOLICITANTE:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "O responsável precisa ser um técnico ou admin",
            )

    for field, value in changes.items():
        setattr(ticket, field, value)
    db.commit()
    return ticket


@router.post("/{ticket_id}/status", response_model=TicketOut)
def change_status(ticket_id: int, data: StatusChange, user: CurrentUser, db: DbSession) -> Ticket:
    """Muda o status seguindo o fluxo e registra a mudança no histórico."""
    # Trava a linha: dois técnicos mudando o mesmo chamado ao mesmo tempo não geram
    # um histórico inconsistente.
    ticket = get_visible_ticket(db, ticket_id, user, lock=True)
    de, para = Status(ticket.status), Status(data.status)

    try:
        validar_transicao(de, para, Papel(user.papel), data.comentario)
    except ErroDeFluxo as exc:
        raise HTTPException(HTTP_STATUS_DO_ERRO[type(exc)], str(exc)) from None

    ticket.status = para.value
    # Quem começa a atender um chamado sem responsável assume o chamado.
    if (
        para == Status.EM_ATENDIMENTO
        and ticket.assignee_id is None
        and user.papel != Papel.SOLICITANTE
    ):
        ticket.assignee_id = user.id

    ticket.events.append(
        TicketEvent(
            user_id=user.id,
            de_status=de.value,
            para_status=para.value,
            comentario=data.comentario,
        )
    )
    db.commit()
    return ticket


@router.get("/{ticket_id}/events", response_model=list[TicketEventOut])
def list_events(ticket_id: int, user: CurrentUser, db: DbSession) -> Sequence[TicketEvent]:
    get_visible_ticket(db, ticket_id, user)
    stmt = (
        select(TicketEvent)
        .where(TicketEvent.ticket_id == ticket_id)
        .options(joinedload(TicketEvent.autor))
        .order_by(TicketEvent.criado_em, TicketEvent.id)
    )
    return db.scalars(stmt).all()


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: int, user: AdminUser, db: DbSession) -> Response:
    ticket = get_visible_ticket(db, ticket_id, user)
    db.delete(ticket)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
