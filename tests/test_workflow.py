"""Testes de unidade da regra de negócio do fluxo de status (sem HTTP e sem banco)."""

import pytest

from app.models import Papel, Status
from app.workflow import (
    EXIGE_COMENTARIO,
    TRANSICOES,
    ComentarioObrigatorio,
    TransicaoInvalida,
    TransicaoNaoPermitida,
    validar_transicao,
)

A, EM, R, F = Status.ABERTO, Status.EM_ATENDIMENTO, Status.RESOLVIDO, Status.FECHADO


def test_chamado_aberto_nao_pode_ir_direto_para_fechado():
    with pytest.raises(TransicaoInvalida):
        validar_transicao(A, F, Papel.ADMIN, "Fechando sem atender")


@pytest.mark.parametrize("de, para", [(A, R), (EM, F), (EM, A), (R, A), (A, A), (EM, EM)])
def test_transicoes_fora_do_fluxo_sao_invalidas_ate_para_admin(de, para):
    with pytest.raises(TransicaoInvalida):
        validar_transicao(de, para, Papel.ADMIN, "comentário qualquer")


@pytest.mark.parametrize("para", list(Status))
def test_fechado_e_estado_final(para):
    with pytest.raises(TransicaoInvalida):
        validar_transicao(F, para, Papel.ADMIN, "comentário qualquer")


@pytest.mark.parametrize("de, para", [(A, EM), (EM, R)])
def test_solicitante_nao_atende_nem_resolve(de, para):
    with pytest.raises(TransicaoNaoPermitida):
        validar_transicao(de, para, Papel.SOLICITANTE, "comentário qualquer")


def test_solicitante_confirma_ou_reabre_chamado_resolvido():
    validar_transicao(R, F, Papel.SOLICITANTE, None)
    validar_transicao(R, EM, Papel.SOLICITANTE, "A imagem continua piscando")


@pytest.mark.parametrize("de, para", list(EXIGE_COMENTARIO))
@pytest.mark.parametrize("comentario", [None, "", "   "])
def test_resolver_e_reabrir_exigem_comentario(de, para, comentario):
    with pytest.raises(ComentarioObrigatorio):
        validar_transicao(de, para, Papel.TECNICO, comentario)


def test_caminho_feliz_do_tecnico():
    validar_transicao(A, EM, Papel.TECNICO, None)
    validar_transicao(EM, R, Papel.TECNICO, "Lâmpada do projetor substituída")
    validar_transicao(R, F, Papel.TECNICO, None)


def test_todo_status_tem_regra_definida():
    assert set(TRANSICOES) == set(Status)
