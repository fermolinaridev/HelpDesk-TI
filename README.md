# HelpDesk TI

Sistema de chamados de TI para escolas, com triagem automática por IA.

## O problema

Em muitas escolas, os problemas de TI chegam por WhatsApp ou no corredor: "o projetor da sala 12 não liga", "a internet do laboratório caiu". Sem registro, não existe histórico, ninguém sabe quanto tempo leva para resolver e não dá para saber quais equipamentos quebram mais.

O HelpDesk TI organiza isso:

- o professor abre o chamado escolhendo a sala e o equipamento;
- a equipe de TI faz a triagem e acompanha o atendimento;
- os dados viram relatórios.

> Todos os dados do projeto (seed, testes e exemplos) são **fictícios**.

## Funcionalidades

| Fase | Entrega | Status |
| --- | --- | --- |
| **V1 — MVP** | CRUD de chamados, login JWT com papéis, Postgres + Alembic, Docker Compose, testes de integração e CI | ✅ |
| **V2 — Regras e relatórios** | Fluxo de status com histórico, permissões refinadas, relatórios SQL (JOIN, GROUP BY, window functions), front simples | 🔜 |
| **V3 — IA e deploy** | Triagem por LLM com classificador de reserva, métrica de acerto da IA, seed fictício e deploy público | 🔜 |

### Papéis

| Papel | Pode |
| --- | --- |
| `solicitante` (professor) | abrir chamados, ver e editar **apenas os próprios** (texto, enquanto estiver aberto) |
| `tecnico` | ver todos os chamados, fazer a triagem (status, prioridade, categoria, responsável) |
| `admin` | tudo do técnico, mais cadastrar usuários, salas, equipamentos e categorias e excluir chamados |

## Stack

- **Python 3.12** + **FastAPI**
- **PostgreSQL 17** + **SQLAlchemy 2** + **Alembic** (migrações)
- **JWT** (PyJWT) e senhas com **bcrypt**
- **pytest** com testes de integração contra Postgres real
- **Docker Compose** e **GitHub Actions** (lint, testes e checagem de migrações)

## Modelo de dados

```mermaid
erDiagram
    users ||--o{ tickets : "abre (requester)"
    users ||--o{ tickets : "atende (assignee)"
    rooms ||--o{ equipment : "tem"
    equipment ||--o{ tickets : "referente a"
    categories ||--o{ tickets : "classifica"

    users {
        int id PK
        string nome
        string email UK
        string senha_hash
        string papel
    }
    rooms {
        int id PK
        string nome
        string bloco
    }
    equipment {
        int id PK
        string tipo
        string patrimonio UK
        int room_id FK
    }
    categories {
        int id PK
        string nome UK
        int sla_horas
    }
    tickets {
        int id PK
        string titulo
        text descricao
        string status
        string prioridade
        int category_id FK
        int equipment_id FK
        int requester_id FK
        int assignee_id FK
        timestamptz criado_em
    }
```

Os valores de `papel`, `status` e `prioridade` também são validados no banco com `CHECK` constraints, e não só na API. As tabelas `ticket_events` (histórico) e `ai_predictions` (acerto da IA) entram na V2 e na V3.

## Como rodar

Pré-requisito: Docker.

```bash
docker compose up -d --build
```

A API sobe em http://localhost:8000. A documentação interativa (Swagger) fica em http://localhost:8000/docs. As migrações rodam automaticamente na subida.

Crie o primeiro admin (a senha é pedida no terminal):

```bash
docker compose exec api python -m app.cli create-admin --nome "Admin" --email admin@escola.example.com
```

Depois, faça login em `POST /auth/login` (o campo `username` recebe o e-mail) ou pelo botão **Authorize** do Swagger.

## Testes

Os testes de integração rodam contra o banco `helpdesk_test`, que o Compose cria automaticamente no mesmo container do Postgres. O schema é montado pelas próprias migrações do Alembic, então os testes também validam as migrações.

```bash
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt

docker compose up -d db
pytest
```

Alguns casos cobertos:

- **Permissão:** um solicitante não enxerga nem edita o chamado de outro (recebe 404, para não revelar que o id existe).
- **Papéis:** só a equipe de TI faz a triagem; só o admin cadastra e exclui.
- **Autenticação:** token expirado, token inválido ou assinado com outra chave é recusado.
- **Validação:** o responsável precisa ser técnico ou admin; equipamento e categoria precisam existir; duplicatas retornam 409.

## Endpoints (V1)

| Método | Rota | Quem |
| --- | --- | --- |
| `POST` | `/auth/login` | público |
| `GET` | `/auth/me` | logado |
| `GET` / `POST` | `/users` | admin |
| `GET` | `/rooms`, `/equipment?room_id=`, `/categories` | logado |
| `POST` | `/rooms`, `/equipment`, `/categories` | admin |
| `GET` | `/tickets?status=&limit=&offset=` | logado (o solicitante vê só os próprios) |
| `POST` | `/tickets` | logado |
| `GET` / `PATCH` | `/tickets/{id}` | dono ou equipe de TI |
| `DELETE` | `/tickets/{id}` | admin |

## Estrutura

```
app/
  main.py          # cria o app e registra as rotas
  config.py        # configurações via variáveis de ambiente
  database.py      # engine, sessão e Base do SQLAlchemy
  models.py        # tabelas
  schemas.py       # validação de entrada e saída (Pydantic)
  security.py      # bcrypt e JWT
  deps.py          # usuário logado e checagem de papel
  cli.py           # comando create-admin
  routers/         # auth, users, catalog (salas/equipamentos/categorias), tickets
alembic/           # migrações
tests/             # testes de integração
```
