"""Regras do fluxo de status de um chamado.

    aberto ──► em_atendimento ──► resolvido ──► fechado
                     ▲                │
                     └── reaberto ────┘

Fica separado das rotas para que a regra de negócio seja testada sem HTTP nem banco.
"""

from app.models import Papel, Status

EQUIPE = frozenset({Papel.TECNICO, Papel.ADMIN})
TODOS = EQUIPE | {Papel.SOLICITANTE}

# status atual -> {próximo status: papéis que podem fazer a mudança}
TRANSICOES: dict[Status, dict[Status, frozenset[Papel]]] = {
    Status.ABERTO: {Status.EM_ATENDIMENTO: EQUIPE},
    Status.EM_ATENDIMENTO: {Status.RESOLVIDO: EQUIPE},
    Status.RESOLVIDO: {
        Status.FECHADO: TODOS,  # o solicitante confirma que foi resolvido
        Status.EM_ATENDIMENTO: TODOS,  # reabertura: a solução não funcionou
    },
    Status.FECHADO: {},  # estado final
}

# Mudanças que precisam de explicação no histórico.
EXIGE_COMENTARIO = {
    (Status.EM_ATENDIMENTO, Status.RESOLVIDO): "Descreva a solução aplicada",
    (Status.RESOLVIDO, Status.EM_ATENDIMENTO): "Explique por que o chamado está sendo reaberto",
}


class ErroDeFluxo(Exception):
    """Base dos erros de transição de status."""


class TransicaoInvalida(ErroDeFluxo):
    """A mudança não existe no fluxo (ex.: aberto -> fechado)."""


class TransicaoNaoPermitida(ErroDeFluxo):
    """A mudança existe, mas o papel do usuário não pode fazê-la."""


class ComentarioObrigatorio(ErroDeFluxo):
    """A mudança exige um comentário."""


def transicoes_disponiveis(de: Status, papel: Papel) -> list[tuple[Status, bool]]:
    """Próximos status que o papel pode escolher, e se cada um exige comentário."""
    return [
        (para, (de, para) in EXIGE_COMENTARIO)
        for para, papeis in TRANSICOES[de].items()
        if papel in papeis
    ]


def validar_transicao(de: Status, para: Status, papel: Papel, comentario: str | None) -> None:
    permitidos = TRANSICOES[de].get(para)
    if permitidos is None:
        raise TransicaoInvalida(f"Não é possível mudar o status de '{de}' para '{para}'")
    if papel not in permitidos:
        raise TransicaoNaoPermitida(f"O papel '{papel}' não pode mudar de '{de}' para '{para}'")

    motivo = EXIGE_COMENTARIO.get((de, para))
    if motivo and not (comentario and comentario.strip()):
        raise ComentarioObrigatorio(motivo)
