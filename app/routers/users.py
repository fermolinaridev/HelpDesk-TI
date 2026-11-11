from collections.abc import Sequence

from fastapi import APIRouter, status
from sqlalchemy import select

from app.deps import AdminUser, DbSession, commit_or_conflict
from app.models import User
from app.schemas import UserCreate, UserOut
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["usuários"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, _: AdminUser, db: DbSession) -> User:
    user = User(
        nome=data.nome.strip(),
        email=data.email.lower(),
        senha_hash=hash_password(data.senha),
        papel=data.papel,
    )
    db.add(user)
    commit_or_conflict(db, "Já existe um usuário com este e-mail")
    return user


@router.get("", response_model=list[UserOut])
def list_users(_: AdminUser, db: DbSession) -> Sequence[User]:
    return db.scalars(select(User).order_by(User.nome)).all()
