from fastapi import FastAPI

from app.routers import auth, catalog, reports, tickets, users

app = FastAPI(
    title="HelpDesk TI",
    version="0.1.0",
    description="Sistema de chamados de TI para escolas, com triagem automática por IA.",
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(catalog.router)
app.include_router(tickets.router)
app.include_router(reports.router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
