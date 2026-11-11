"""histórico de status dos chamados (ticket_events)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-11

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS_SQL = "('aberto', 'em_atendimento', 'resolvido', 'fechado')"


def upgrade() -> None:
    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey(
                "tickets.id",
                name=op.f("fk_ticket_events_ticket_id_tickets"),
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name=op.f("fk_ticket_events_user_id_users")),
            nullable=False,
        ),
        sa.Column("de_status", sa.String(20), nullable=True),
        sa.Column("para_status", sa.String(20), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"para_status IN {STATUS_SQL}", name=op.f("ck_ticket_events_para_status_valido")
        ),
        sa.CheckConstraint(
            f"de_status IS NULL OR de_status IN {STATUS_SQL}",
            name=op.f("ck_ticket_events_de_status_valido"),
        ),
    )
    op.create_index(op.f("ix_ticket_events_ticket_id"), "ticket_events", ["ticket_id"])

    # Chamados criados antes desta migração ganham o evento de abertura,
    # para todo chamado ter pelo menos uma linha de histórico.
    op.execute(
        """
        INSERT INTO ticket_events (ticket_id, user_id, de_status, para_status, criado_em)
        SELECT id, requester_id, NULL, 'aberto', criado_em
        FROM tickets
        """
    )


def downgrade() -> None:
    op.drop_table("ticket_events")
