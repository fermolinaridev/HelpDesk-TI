"""Comandos administrativos.

Uso:
    python -m app.cli create-admin --nome "Admin" --email admin@escola.example

A senha é pedida no terminal (ou lida da variável ADMIN_PASSWORD).
"""

import argparse
import getpass
import os
import sys

from pydantic import ValidationError
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Papel, User
from app.schemas import UserCreate
from app.security import hash_password


def create_admin(nome: str, email: str, senha: str) -> None:
    try:
        data = UserCreate(nome=nome, email=email, senha=senha, papel=Papel.ADMIN)
    except ValidationError as exc:
        sys.exit(f"Dados inválidos:\n{exc}")

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == data.email.lower())):
            sys.exit(f"Já existe um usuário com o e-mail {data.email}")
        db.add(
            User(
                nome=data.nome,
                email=data.email.lower(),
                senha_hash=hash_password(data.senha),
                papel=data.papel,
            )
        )
        db.commit()
    print(f"Admin {data.email} criado.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    admin = sub.add_parser("create-admin", help="cria um usuário com papel admin")
    admin.add_argument("--nome", required=True)
    admin.add_argument("--email", required=True)

    args = parser.parse_args()
    if args.command == "create-admin":
        senha = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Senha do admin: ")
        create_admin(args.nome, args.email, senha)


if __name__ == "__main__":
    main()
