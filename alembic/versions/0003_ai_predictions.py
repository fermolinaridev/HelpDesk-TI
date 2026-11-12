"""sugestões de triagem da IA (ai_predictions)

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-12

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRIORIDADES_SQL = "('baixa', 'media', 'alta', 'critica')"


def upgrade() -> None:
    op.create_table(
        "ai_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey(
                "tickets.id", name=op.f("fk_ai_predictions_ticket_id_tickets"), ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column("fonte", sa.String(10), nullable=False),
        sa.Column("modelo", sa.String(60), nullable=True),
        sa.Column(
            "categoria_sugerida_id",
            sa.Integer(),
            sa.ForeignKey(
                "categories.id", name=op.f("fk_ai_predictions_categoria_sugerida_id_categories")
            ),
            nullable=True,
        ),
        sa.Column("prioridade_sugerida", sa.String(10), nullable=False),
        sa.Column("justificativa", sa.Text(), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "categoria_final_id",
            sa.Integer(),
            sa.ForeignKey(
                "categories.id", name=op.f("fk_ai_predictions_categoria_final_id_categories")
            ),
            nullable=True,
        ),
        sa.Column("prioridade_final", sa.String(10), nullable=True),
        sa.Column(
            "avaliado_por_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name=op.f("fk_ai_predictions_avaliado_por_id_users")),
            nullable=True,
        ),
        sa.Column("avaliado_em", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("ticket_id", name=op.f("uq_ai_predictions_ticket_id")),
        sa.CheckConstraint(
            "fonte IN ('llm', 'regras')", name=op.f("ck_ai_predictions_fonte_valida")
        ),
        sa.CheckConstraint(
            f"prioridade_sugerida IN {PRIORIDADES_SQL}",
            name=op.f("ck_ai_predictions_prioridade_sugerida_valida"),
        ),
        sa.CheckConstraint(
            f"prioridade_final IS NULL OR prioridade_final IN {PRIORIDADES_SQL}",
            name=op.f("ck_ai_predictions_prioridade_final_valida"),
        ),
    )


def downgrade() -> None:
    op.drop_table("ai_predictions")
