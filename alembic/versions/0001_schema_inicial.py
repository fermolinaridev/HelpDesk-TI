"""schema inicial: users, rooms, equipment, categories, tickets

Revision ID: 0001
Revises:
Create Date: 2026-11-11

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("papel", sa.String(20), nullable=False),
        sa.CheckConstraint(
            "papel IN ('solicitante', 'tecnico', 'admin')", name=op.f("ck_users_papel_valido")
        ),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("bloco", sa.String(40), nullable=False),
        sa.UniqueConstraint("bloco", "nome", name="uq_rooms_bloco_nome"),
    )

    op.create_table(
        "equipment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(60), nullable=False),
        sa.Column("patrimonio", sa.String(40), nullable=False),
        sa.Column(
            "room_id",
            sa.Integer(),
            sa.ForeignKey("rooms.id", name=op.f("fk_equipment_room_id_rooms")),
            nullable=False,
        ),
        sa.UniqueConstraint("patrimonio", name=op.f("uq_equipment_patrimonio")),
    )
    op.create_index(op.f("ix_equipment_room_id"), "equipment", ["room_id"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(60), nullable=False),
        sa.Column("sla_horas", sa.Integer(), nullable=False),
        sa.CheckConstraint("sla_horas > 0", name=op.f("ck_categories_sla_positivo")),
        sa.UniqueConstraint("nome", name=op.f("uq_categories_nome")),
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("titulo", sa.String(150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("prioridade", sa.String(10), nullable=False),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", name=op.f("fk_tickets_category_id_categories")),
            nullable=True,
        ),
        sa.Column(
            "equipment_id",
            sa.Integer(),
            sa.ForeignKey("equipment.id", name=op.f("fk_tickets_equipment_id_equipment")),
            nullable=False,
        ),
        sa.Column(
            "requester_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name=op.f("fk_tickets_requester_id_users")),
            nullable=False,
        ),
        sa.Column(
            "assignee_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name=op.f("fk_tickets_assignee_id_users")),
            nullable=True,
        ),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('aberto', 'em_atendimento', 'resolvido', 'fechado')",
            name=op.f("ck_tickets_status_valido"),
        ),
        sa.CheckConstraint(
            "prioridade IN ('baixa', 'media', 'alta', 'critica')",
            name=op.f("ck_tickets_prioridade_valida"),
        ),
    )
    for column in ("status", "category_id", "equipment_id", "requester_id", "assignee_id"):
        op.create_index(op.f(f"ix_tickets_{column}"), "tickets", [column])


def downgrade() -> None:
    op.drop_table("tickets")
    op.drop_table("categories")
    op.drop_table("equipment")
    op.drop_table("rooms")
    op.drop_table("users")
