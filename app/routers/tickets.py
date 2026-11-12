from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.deps import AdminUser, CurrentUser, DbSession
from app.models import Category, Equipment, Papel, Status, Ticket, TicketEvent, User
from app.schemas import (
    StatusChange,
    TicketCreate,
    TicketDetailOut,
    TicketEventOut,
    TicketOut,
    TicketUpdate,
)
from app.triage import Triagem, get_triagem, triar_em_segundo_plano
from app.workflow import (
    ComentarioObrigatorio,
    ErroDeFluxo,
    TransicaoInvalida,
    TransicaoNaoPermitida,
    transicoes_disponiveis,
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

# Carrega categoria, equipamento (com sala) e pessoas na mesma consulta, evitando N+1.
RELACIONADOS = (
    joinedload(Ticket.category),
    joinedload(Ticket.equipment).joinedload(Equipment.room),
    joinedload(Ticket.requester),
    joinedload(Ticket.assignee),
)


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


def ticket_detail(db: Session, ticket: Ticket, user: User) -> dict:
    """Chamado + as mudanças de status que este usuário pode fazer agora."""
    db.expire(ticket)  # garante relacionamentos atualizados após um commit
    detail = TicketOut.model_validate(ticket).model_dump()
    detail["transicoes"] = [
        {"status": para, "exige_comentario": exige}
        for para, exige in transicoes_disponiveis(Status(ticket.status), Papel(user.papel))
    ]
    if user.papel != Papel.SOLICITANTE:
        detail["sugestao_ia"] = ticket.prediction
    return detail


TRIAGEM_CAMPOS = {"prioridade", "category_id"}


def registrar_avaliacao(db: Session, ticket: Ticket, user: User) -> None:
    """Guarda a decisão da equipe ao lado da sugestão da IA, para medir o acerto.

    Vale a última triagem: se o técnico corrigir de novo, o "final" acompanha.
    """
    prediction = ticket.prediction
    if prediction is None:
        return
    prediction.categoria_final_id = ticket.category_id
    prediction.prioridade_final = ticket.prioridade
    prediction.avaliado_por_id = user.id
    prediction.avaliado_em = func.now()


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    data: TicketCreate,
    user: CurrentUser,
    db: DbSession,
    tarefas: BackgroundTasks,
    triagem: Annotated[Triagem, Depends(get_triagem)],
) -> Ticket:
    if db.get(Equipment, data.equipment_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Equipamento não encontrado")

    ticket = Ticket(**data.model_dump(), requester_id=user.id)
    ticket.events.append(
        TicketEvent(user_id=user.id, de_status=None, para_status=Status.ABERTO.value)
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)  # carrega criado_em, preenchido pelo banco
    # A IA analisa depois da resposta: quem abre o chamado não espera pela API do modelo.
    tarefas.add_task(triar_em_segundo_plano, ticket.id, triagem)
    return ticket


@router.get("", response_model=list[TicketOut])
def list_tickets(
    user: CurrentUser,
    db: DbSession,
    status_filter: Annotated[Status | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[Ticket]:
    stmt = select(Ticket).options(*RELACIONADOS).order_by(Ticket.criado_em.desc(), Ticket.id.desc())
    if user.papel == Papel.SOLICITANTE:
        stmt = stmt.where(Ticket.requester_id == user.id)
    if status_filter is not None:
        stmt = stmt.where(Ticket.status == status_filter.value)
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.get("/{ticket_id}", response_model=TicketDetailOut)
def get_ticket(ticket_id: int, user: CurrentUser, db: DbSession) -> dict:
    return ticket_detail(db, get_visible_ticket(db, ticket_id, user), user)


@router.patch("/{ticket_id}", response_model=TicketDetailOut)
def update_ticket(ticket_id: int, data: TicketUpdate, user: CurrentUser, db: DbSession) -> dict:
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
    if changes.keys() & TRIAGEM_CAMPOS:
        registrar_avaliacao(db, ticket, user)
    db.commit()
    return ticket_detail(db, ticket, user)


@router.post("/{ticket_id}/status", response_model=TicketDetailOut)
def change_status(ticket_id: int, data: StatusChange, user: CurrentUser, db: DbSession) -> dict:
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
    return ticket_detail(db, ticket, user)


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
