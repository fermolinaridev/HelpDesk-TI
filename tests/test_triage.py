"""Triagem por IA, testada sem chamar a API de verdade.

O modelo de linguagem é substituído por dublês: um cliente falso que devolve a resposta que
a API devolveria, ou que falha como a API pode falhar.
"""

import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.main import app
from app.models import AIPrediction, Category, FonteIA, Prioridade
from app.triage import (
    Chamado,
    ClassificadorLLM,
    ClassificadorRegras,
    FalhaNaIA,
    Sugestao,
    Triagem,
    get_triagem,
)

CATEGORIAS = ["impressora", "lousa digital", "projetor", "rede", "som"]


def resposta_da_api(dados: dict | str, stop_reason: str = "end_turn") -> SimpleNamespace:
    texto = dados if isinstance(dados, str) else json.dumps(dados)
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=texto)],
        model="claude-opus-5-5",
    )


class ClienteFalso:
    """Imita anthropic.Anthropic: guarda o pedido e devolve uma resposta pronta."""

    def __init__(self, resposta=None, erro: Exception | None = None) -> None:
        self.pedidos: list[dict] = []
        self.resposta, self.erro = resposta, erro
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.pedidos.append(kwargs)
        if self.erro:
            raise self.erro
        return self.resposta


CHAMADO = Chamado(
    titulo="Projetor não liga",
    descricao="Tenho prova às 10h e o projetor não liga de jeito nenhum.",
    equipamento="Projetor",
)


# --- Classificador de reserva (regras) ---


@pytest.mark.parametrize(
    ("chamado", "categoria", "prioridade"),
    [
        (CHAMADO, "projetor", Prioridade.ALTA),
        (
            Chamado("Internet lenta", "A internet do laboratório cai às vezes.", "Roteador Wi-Fi"),
            "rede",
            Prioridade.BAIXA,  # intermitente ("às vezes")
        ),
        (
            Chamado("Cheiro estranho", "Saiu fumaça da impressora agora há pouco.", "Impressora"),
            "impressora",
            Prioridade.CRITICA,
        ),
        (
            Chamado("Caneta falhando", "A caneta falha de vez em quando.", "Lousa digital"),
            "lousa digital",
            Prioridade.BAIXA,
        ),
        (
            Chamado("Problema na sala", "Algo estranho aconteceu hoje cedo.", "Armário"),
            None,
            Prioridade.MEDIA,
        ),
    ],
)
def test_regras_sugerem_categoria_e_prioridade(chamado, categoria, prioridade):
    sugestao = ClassificadorRegras().classificar(chamado, CATEGORIAS)
    assert sugestao.categoria == categoria
    assert sugestao.prioridade == prioridade
    assert sugestao.fonte == FonteIA.REGRAS


# --- Classificador com o modelo (cliente falso) ---


def test_llm_monta_o_pedido_e_le_a_resposta_estruturada():
    cliente = ClienteFalso(
        resposta_da_api(
            {"categoria": "projetor", "prioridade": "alta", "justificativa": "Prova às 10h."}
        )
    )
    sugestao = ClassificadorLLM(cliente, "claude-opus-5-5").classificar(CHAMADO, CATEGORIAS)

    assert sugestao == Sugestao(
        categoria="projetor",
        prioridade=Prioridade.ALTA,
        justificativa="Prova às 10h.",
        fonte=FonteIA.LLM,
        modelo="claude-opus-5-5",
    )
    (pedido,) = cliente.pedidos
    schema = pedido["output_config"]["format"]["schema"]
    # A categoria só pode ser uma das cadastradas (ou "nenhuma").
    assert schema["properties"]["categoria"]["enum"] == [*CATEGORIAS, "nenhuma"]
    # O texto do professor vai delimitado, como dado.
    assert "<chamado>" in pedido["messages"][0]["content"]
    assert "prova às 10h" in pedido["messages"][0]["content"].lower()


def test_llm_categoria_nenhuma_vira_sem_categoria():
    cliente = ClienteFalso(
        resposta_da_api({"categoria": "nenhuma", "prioridade": "baixa", "justificativa": "?"})
    )
    sugestao = ClassificadorLLM(cliente, "m").classificar(CHAMADO, CATEGORIAS)
    assert sugestao.categoria is None


@pytest.mark.parametrize(
    "resposta",
    [
        resposta_da_api("isto não é JSON"),
        resposta_da_api({"categoria": "projetor"}),  # faltam campos
        resposta_da_api({}, stop_reason="refusal"),
        resposta_da_api({}, stop_reason="max_tokens"),
    ],
)
def test_llm_resposta_inutilizavel_levanta_falha(resposta):
    with pytest.raises(FalhaNaIA):
        ClassificadorLLM(ClienteFalso(resposta), "m").classificar(CHAMADO, CATEGORIAS)


# --- Triagem: usa as regras quando o modelo falha ---

ERROS_DA_API = [
    anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.example.com")),
    anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.example.com")),
    FalhaNaIA("resposta sem texto"),
]


@pytest.mark.parametrize("erro", ERROS_DA_API, ids=lambda e: type(e).__name__)
def test_triagem_usa_regras_quando_o_modelo_falha(erro):
    triagem = Triagem(llm=ClassificadorLLM(ClienteFalso(erro=erro), "m"))
    sugestao = triagem.classificar(CHAMADO, CATEGORIAS)
    assert sugestao.fonte == FonteIA.REGRAS
    assert sugestao.categoria == "projetor"


def test_triagem_sem_modelo_configurado_usa_regras():
    assert Triagem(llm=None).classificar(CHAMADO, CATEGORIAS).fonte == FonteIA.REGRAS


# --- Pela API: sugestão ao abrir o chamado e acerto medido na triagem ---


@pytest.fixture
def categorias(db) -> dict[str, Category]:
    cats = {nome: Category(nome=nome, sla_horas=8) for nome in CATEGORIAS}
    db.add_all(cats.values())
    db.commit()
    return cats


@pytest.fixture
def ia_responde():
    """Troca a triagem por um modelo falso que sempre responde o JSON indicado."""

    def _configurar(**dados):
        cliente = ClienteFalso(resposta_da_api({"justificativa": "Teste.", **dados}))
        app.dependency_overrides[get_triagem] = lambda: Triagem(
            llm=ClassificadorLLM(cliente, "claude-opus-5-5")
        )

    return _configurar


def test_abrir_chamado_gera_sugestao_que_so_a_equipe_ve(
    client, auth, solicitante, tecnico, categorias, abrir_chamado, ia_responde
):
    ia_responde(categoria="projetor", prioridade="alta")
    chamado = abrir_chamado(solicitante)

    # A sugestão não altera o chamado: a decisão continua com a equipe.
    assert chamado["category_id"] is None
    assert chamado["prioridade"] == "media"

    detalhe = client.get(f"/tickets/{chamado['id']}", headers=auth(tecnico)).json()
    sugestao = detalhe["sugestao_ia"]
    assert sugestao["fonte"] == "llm"
    assert sugestao["modelo"] == "claude-opus-5-5"
    assert sugestao["categoria_sugerida"]["nome"] == "projetor"
    assert sugestao["prioridade_sugerida"] == "alta"
    assert sugestao["avaliado_em"] is None

    do_professor = client.get(f"/tickets/{chamado['id']}", headers=auth(solicitante)).json()
    assert do_professor["sugestao_ia"] is None


def test_falha_da_ia_nao_impede_abrir_chamado(
    client, auth, solicitante, tecnico, categorias, abrir_chamado
):
    erro = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x.example"))
    app.dependency_overrides[get_triagem] = lambda: Triagem(
        llm=ClassificadorLLM(ClienteFalso(erro=erro), "m")
    )
    chamado = abrir_chamado(solicitante)

    detalhe = client.get(f"/tickets/{chamado['id']}", headers=auth(tecnico)).json()
    assert detalhe["sugestao_ia"]["fonte"] == "regras"
    assert detalhe["sugestao_ia"]["categoria_sugerida"]["nome"] == "projetor"


def test_triagem_registra_a_decisao_e_o_relatorio_mede_o_acerto(
    client, auth, db, solicitante, tecnico, categorias, abrir_chamado, ia_responde
):
    ia_responde(categoria="projetor", prioridade="alta")
    aceito = abrir_chamado(solicitante, titulo="Projetor não liga")
    corrigido = abrir_chamado(solicitante, titulo="Projetor sem som")

    # 1º: técnico aceita a sugestão. 2º: corrige a categoria para "som".
    for chamado, categoria in ((aceito, "projetor"), (corrigido, "som")):
        resp = client.patch(
            f"/tickets/{chamado['id']}",
            json={"category_id": categorias[categoria].id, "prioridade": "alta"},
            headers=auth(tecnico),
        )
        assert resp.status_code == 200, resp.text

    prediction = db.query(AIPrediction).filter_by(ticket_id=corrigido["id"]).one()
    assert prediction.categoria_final_id == categorias["som"].id
    assert prediction.avaliado_por_id == tecnico.id
    assert prediction.avaliado_em is not None

    relatorio = client.get("/reports/ia", headers=auth(tecnico)).json()
    assert relatorio["geral"] == {
        "fonte": "todas",
        "sugestoes": 2,
        "avaliadas": 2,
        "pct_categoria": 50.0,
        "pct_prioridade": 100.0,
        "pct_ambos": 50.0,
    }
    assert [f["fonte"] for f in relatorio["por_fonte"]] == ["llm"]
    assert relatorio["correcoes"] == [{"sugerida": "projetor", "final": "som", "vezes": 1}]


def test_trocar_so_o_responsavel_nao_conta_como_avaliacao(
    client, auth, db, solicitante, tecnico, categorias, abrir_chamado
):
    chamado = abrir_chamado(solicitante)
    client.patch(
        f"/tickets/{chamado['id']}", json={"assignee_id": tecnico.id}, headers=auth(tecnico)
    )
    prediction = db.query(AIPrediction).filter_by(ticket_id=chamado["id"]).one()
    assert prediction.avaliado_em is None


def test_relatorio_de_ia_vazio(client, auth, tecnico):
    relatorio = client.get("/reports/ia", headers=auth(tecnico)).json()
    assert relatorio["geral"]["sugestoes"] == 0
    assert relatorio["geral"]["pct_categoria"] is None
    assert relatorio["por_fonte"] == []
    assert relatorio["correcoes"] == []


def test_relatorio_de_ia_e_so_da_equipe(client, auth, solicitante):
    assert client.get("/reports/ia", headers=auth(solicitante)).status_code == 403
