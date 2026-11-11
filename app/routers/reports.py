from typing import Annotated, Any

from fastapi import APIRouter, Query

from app import reports
from app.deps import DbSession, StaffUser
from app.schemas import ChamadosPorMes, ChamadosPorSala, EquipamentoRanking, TempoResolucaoOut

router = APIRouter(prefix="/reports", tags=["relatórios"])


@router.get("/tempo-resolucao", response_model=TempoResolucaoOut)
def tempo_resolucao(_: StaffUser, db: DbSession) -> dict[str, Any]:
    """Tempo médio e mediano de resolução e % dentro do SLA, por categoria."""
    return reports.tempo_resolucao(db)


@router.get("/equipamentos", response_model=list[EquipamentoRanking])
def equipamentos(
    _: StaffUser, db: DbSession, limite: Annotated[int, Query(ge=1, le=100)] = 10
) -> list[dict[str, Any]]:
    """Ranking dos equipamentos com mais chamados."""
    return reports.equipamentos_mais_chamados(db, limite)


@router.get("/salas", response_model=list[ChamadosPorSala])
def salas(_: StaffUser, db: DbSession) -> list[dict[str, Any]]:
    """Chamados por sala, com quantos ainda estão em aberto e a % do total."""
    return reports.chamados_por_sala(db)


@router.get("/mensal", response_model=list[ChamadosPorMes])
def mensal(_: StaffUser, db: DbSession) -> list[dict[str, Any]]:
    """Chamados abertos por mês, com variação e acumulado."""
    return reports.chamados_por_mes(db)
