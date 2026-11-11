import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../api";
import { isStaff, useAuth } from "../auth";
import { PrioridadeBadge, StatusBadge } from "../components/Badges";
import { STATUS_LABEL, formatDateTime } from "../labels";
import type { Status } from "../types";

const FILTROS: (Status | null)[] = [null, "aberto", "em_atendimento", "resolvido", "fechado"];

export default function TicketsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const status = (params.get("status") as Status | null) ?? null;

  const { data: tickets, isPending, error } = useQuery({
    queryKey: ["tickets", status],
    queryFn: () => api.tickets(status ?? undefined),
  });

  return (
    <>
      <div className="page-header">
        <h1>{isStaff(user) ? "Chamados" : "Meus chamados"}</h1>
        <Link to="/chamados/novo" className="btn btn-primary">
          + Novo chamado
        </Link>
      </div>

      <div className="chips" role="group" aria-label="Filtrar por status">
        {FILTROS.map((f) => (
          <button
            key={f ?? "todos"}
            type="button"
            className={f === status ? "chip chip-active" : "chip"}
            onClick={() => setParams(f ? { status: f } : {})}
          >
            {f ? STATUS_LABEL[f] : "Todos"}
          </button>
        ))}
      </div>

      {isPending && <p className="muted">Carregando chamados…</p>}
      {error && <p className="error">{error.message}</p>}
      {tickets && tickets.length === 0 && (
        <div className="card empty">
          <p>Nenhum chamado {status ? `com status “${STATUS_LABEL[status]}”` : "ainda"}.</p>
        </div>
      )}

      {tickets && tickets.length > 0 && (
        <div className="card table-wrap">
          <table className="table table-clickable">
            <thead>
              <tr>
                <th>#</th>
                <th>Chamado</th>
                <th>Local</th>
                <th>Status</th>
                <th>Prioridade</th>
                {isStaff(user) && <th>Responsável</th>}
                <th>Aberto em</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => (
                <tr key={t.id} onClick={() => navigate(`/chamados/${t.id}`)}>
                  <td className="muted">{t.id}</td>
                  <td>
                    <Link to={`/chamados/${t.id}`} onClick={(e) => e.stopPropagation()}>
                      {t.titulo}
                    </Link>
                    <div className="muted small">
                      {t.equipment.tipo} · {t.equipment.patrimonio}
                    </div>
                  </td>
                  <td>
                    {t.equipment.room.nome}
                    <div className="muted small">Bloco {t.equipment.room.bloco}</div>
                  </td>
                  <td>
                    <StatusBadge status={t.status} />
                  </td>
                  <td>
                    <PrioridadeBadge prioridade={t.prioridade} />
                  </td>
                  {isStaff(user) && <td>{t.assignee?.nome ?? <span className="muted">—</span>}</td>}
                  <td className="nowrap">{formatDateTime(t.criado_em)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
