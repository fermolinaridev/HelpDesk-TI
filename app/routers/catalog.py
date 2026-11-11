"""Cadastros de apoio: salas, equipamentos e categorias.

Qualquer usuário logado pode listar (para abrir chamados); só o admin cadastra.
"""

from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import AdminUser, CurrentUser, DbSession, commit_or_conflict
from app.models import Category, Equipment, Room
from app.schemas import (
    CategoryCreate,
    CategoryOut,
    EquipmentCreate,
    EquipmentOut,
    RoomCreate,
    RoomOut,
)

router = APIRouter(tags=["cadastros"])


@router.get("/rooms", response_model=list[RoomOut])
def list_rooms(_: CurrentUser, db: DbSession) -> Sequence[Room]:
    return db.scalars(select(Room).order_by(Room.bloco, Room.nome)).all()


@router.post("/rooms", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(data: RoomCreate, _: AdminUser, db: DbSession) -> Room:
    room = Room(**data.model_dump())
    db.add(room)
    commit_or_conflict(db, "Já existe uma sala com este nome neste bloco")
    return room


@router.get("/equipment", response_model=list[EquipmentOut])
def list_equipment(
    _: CurrentUser, db: DbSession, room_id: int | None = None
) -> Sequence[Equipment]:
    stmt = select(Equipment).order_by(Equipment.tipo, Equipment.patrimonio)
    if room_id is not None:
        stmt = stmt.where(Equipment.room_id == room_id)
    return db.scalars(stmt).all()


@router.post("/equipment", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
def create_equipment(data: EquipmentCreate, _: AdminUser, db: DbSession) -> Equipment:
    if db.get(Room, data.room_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Sala não encontrada")
    equipment = Equipment(**data.model_dump())
    db.add(equipment)
    commit_or_conflict(db, "Já existe um equipamento com este patrimônio")
    return equipment


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(_: CurrentUser, db: DbSession) -> Sequence[Category]:
    return db.scalars(select(Category).order_by(Category.nome)).all()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, _: AdminUser, db: DbSession) -> Category:
    category = Category(**data.model_dump())
    db.add(category)
    commit_or_conflict(db, "Já existe uma categoria com este nome")
    return category
