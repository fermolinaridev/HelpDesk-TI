"""Relatórios gerenciais escritos em SQL puro.

Ficam em SQL (e não no ORM) de propósito: são consultas analíticas, com CTEs,
ROLLUP, FILTER e window functions, e lê-las como SQL é mais claro.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

# Tempo de resolução = abertura até a ÚLTIMA vez que o chamado foi para "resolvido"
# (se foi reaberto, conta a resolução definitiva). ROLLUP gera a linha de total geral.
# A mediana entra junto com a média porque poucos chamados muito demorados distorcem a média.
TEMPO_RESOLUCAO_SQL = text("""
    WITH resolucao AS (
        SELECT t.id,
               t.category_id,
               MAX(e.criado_em) - t.criado_em AS duracao
        FROM tickets t
        JOIN ticket_events e ON e.ticket_id = t.id AND e.para_status = 'resolvido'
        WHERE t.status IN ('resolvido', 'fechado')
        GROUP BY t.id
    )
    SELECT GROUPING(c.nome) = 1                                       AS total,
           COALESCE(c.nome, 'sem categoria')                          AS categoria,
           COUNT(*)                                                   AS resolvidos,
           ROUND(AVG(EXTRACT(EPOCH FROM r.duracao)) / 3600, 2)        AS horas_media,
           ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP
                     (ORDER BY EXTRACT(EPOCH FROM r.duracao)) / 3600)::numeric, 2)
                                                                      AS horas_mediana,
           ROUND(100.0 * AVG((r.duracao <= c.sla_horas * INTERVAL '1 hour')::int), 1)
                                                                      AS pct_no_sla
    FROM resolucao r
    LEFT JOIN categories c ON c.id = r.category_id
    GROUP BY ROLLUP (c.nome)
    ORDER BY total, horas_media DESC NULLS LAST, categoria
""")

# RANK() deixa equipamentos empatados na mesma posição.
EQUIPAMENTOS_SQL = text("""
    SELECT RANK() OVER (ORDER BY COUNT(t.id) DESC) AS posicao,
           e.id                                    AS equipment_id,
           e.tipo,
           e.patrimonio,
           r.nome                                  AS sala,
           r.bloco,
           COUNT(t.id)                             AS chamados
    FROM equipment e
    JOIN rooms r   ON r.id = e.room_id
    JOIN tickets t ON t.equipment_id = e.id
    GROUP BY e.id, r.id
    ORDER BY posicao, e.patrimonio
    LIMIT :limite
""")

# LEFT JOIN mantém salas sem chamados (com zero). SUM(...) OVER () é o total geral,
# usado para calcular a porcentagem de cada sala.
SALAS_SQL = text("""
    SELECT r.id                                                         AS room_id,
           r.bloco,
           r.nome                                                       AS sala,
           COUNT(t.id)                                                  AS chamados,
           COUNT(t.id) FILTER (WHERE t.status IN ('aberto', 'em_atendimento'))
                                                                        AS em_aberto,
           ROUND(100.0 * COUNT(t.id) / NULLIF(SUM(COUNT(t.id)) OVER (), 0), 1)
                                                                        AS pct_do_total
    FROM rooms r
    LEFT JOIN equipment e ON e.room_id = r.id
    LEFT JOIN tickets t   ON t.equipment_id = e.id
    GROUP BY r.id
    ORDER BY chamados DESC, r.bloco, r.nome
""")

# generate_series preenche os meses sem chamados com zero. O mês é calculado no fuso
# da escola: um chamado aberto às 23h do dia 31 pertence àquele mês, e não ao seguinte (UTC).
MENSAL_SQL = text("""
    WITH por_mes AS (
        SELECT date_trunc('month', criado_em AT TIME ZONE :tz)::date AS mes,
               COUNT(*)                                             AS chamados
        FROM tickets
        GROUP BY 1
    ),
    meses AS (
        SELECT g::date AS mes
        FROM (SELECT MIN(mes) AS inicio, MAX(mes) AS fim FROM por_mes) limites,
             generate_series(limites.inicio, limites.fim, INTERVAL '1 month') AS g
    )
    SELECT to_char(m.mes, 'YYYY-MM')                                          AS mes,
           COALESCE(p.chamados, 0)                                            AS chamados,
           COALESCE(p.chamados, 0) - LAG(COALESCE(p.chamados, 0)) OVER w      AS variacao,
           (SUM(COALESCE(p.chamados, 0)) OVER w)::int                         AS acumulado
    FROM meses m
    LEFT JOIN por_mes p USING (mes)
    WINDOW w AS (ORDER BY m.mes)
    ORDER BY m.mes
""")

# Acerto da IA: compara o que ela sugeriu com o que a equipe decidiu na triagem.
# Só entram na taxa as sugestões já avaliadas. IS NOT DISTINCT FROM trata "sem categoria"
# dos dois lados como acerto. ROLLUP gera a linha de total, somando as duas fontes.
ACERTO_IA_SQL = text("""
    WITH avaliacao AS (
        SELECT p.fonte,
               p.avaliado_em IS NOT NULL                                      AS avaliada,
               (p.categoria_sugerida_id IS NOT DISTINCT FROM p.categoria_final_id)::int
                                                                              AS acertou_categoria,
               (p.prioridade_sugerida = p.prioridade_final)::int              AS acertou_prioridade
        FROM ai_predictions p
    )
    SELECT GROUPING(fonte) = 1                                                  AS total,
           COALESCE(fonte, 'todas')                                             AS fonte,
           COUNT(*)                                                             AS sugestoes,
           COUNT(*) FILTER (WHERE avaliada)                                     AS avaliadas,
           ROUND(100.0 * AVG(acertou_categoria) FILTER (WHERE avaliada), 1)     AS pct_categoria,
           ROUND(100.0 * AVG(acertou_prioridade) FILTER (WHERE avaliada), 1)    AS pct_prioridade,
           ROUND(100.0 * AVG(acertou_categoria * acertou_prioridade)
                 FILTER (WHERE avaliada), 1)                                    AS pct_ambos
    FROM avaliacao
    GROUP BY ROLLUP (fonte)
    ORDER BY total, fonte
""")

# As trocas de categoria mais comuns na triagem: onde a IA mais erra.
CORRECOES_IA_SQL = text("""
    SELECT COALESCE(cs.nome, 'sem categoria') AS sugerida,
           COALESCE(cf.nome, 'sem categoria') AS final,
           COUNT(*)                           AS vezes
    FROM ai_predictions p
    LEFT JOIN categories cs ON cs.id = p.categoria_sugerida_id
    LEFT JOIN categories cf ON cf.id = p.categoria_final_id
    WHERE p.avaliado_em IS NOT NULL
      AND p.categoria_sugerida_id IS DISTINCT FROM p.categoria_final_id
    GROUP BY cs.nome, cf.nome
    ORDER BY vezes DESC, sugerida, final
    LIMIT :limite
""")


def _rows(db: Session, sql: Any, **params: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(sql, params).mappings()]


def tempo_resolucao(db: Session) -> dict[str, Any]:
    rows = _rows(db, TEMPO_RESOLUCAO_SQL)
    geral = next(r for r in rows if r["total"])  # ROLLUP sempre gera a linha de total
    return {
        "geral": {**geral, "categoria": "todas"},
        "por_categoria": [r for r in rows if not r["total"]],
    }


def equipamentos_mais_chamados(db: Session, limite: int) -> list[dict[str, Any]]:
    return _rows(db, EQUIPAMENTOS_SQL, limite=limite)


def chamados_por_sala(db: Session) -> list[dict[str, Any]]:
    return _rows(db, SALAS_SQL)


def chamados_por_mes(db: Session) -> list[dict[str, Any]]:
    return _rows(db, MENSAL_SQL, tz=settings.timezone)


def acerto_ia(db: Session) -> dict[str, Any]:
    rows = _rows(db, ACERTO_IA_SQL)
    return {
        "geral": next(r for r in rows if r["total"]),
        "por_fonte": [r for r in rows if not r["total"]],
        "correcoes": _rows(db, CORRECOES_IA_SQL, limite=5),
    }
