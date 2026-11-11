import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api";
import { isStaff, useAuth } from "../auth";
import { AssetTag, PrioridadeBadge, StatusBadge } from "../components/Badges";
import Icon from "../components/Icon";
import { STATUS_LABEL, formatDateTime, formatQuando } from "../labels";
import type { Status } from "../types";

const FILTROS: (Status | null)[] = [null, "aberto", "em_atendimento", "resolvido", "fechado"];

export default function TicketsPage() {
  const { user } = useAuth();
  const staff = isStaff(user);
  const [params, setParams] = useSearchParams();
  const status = (params.get("status") as Status | null) ?? null;

  const { data: tickets, isPending, error } = useQuery({
    queryKey: ["tickets", status],
    queryFn: () => api.tickets(status ?? undefined),
  });

  return (
    <>
      <div className="page-header">
        <div>
          <h1>{staff ? "Chamados" : "Meus chamados"}</h1>
          {tickets && (
            <p className="page-sub">
              {tickets.length === 1 ? "1 chamado" : `${tickets.length} chamados`}
              {status && ` com status ${STATUS_LABEL[status].toLowerCase()}`}
            </p>
          )}
        </div>
        <Link to="/chamados/novo" className="btn btn-primary hide-mobile">
          <Icon name="mais" size={18} />
          Abrir chamado
        </Link>
      </div>

      <div className="segmented" role="group" aria-label="Filtrar por status">
        {FILTROS.map((f) => (
          <button
            key={f ?? "todos"}
            type="button"
            aria-pressed={f === status}
            className={f ? `segment segment-${f}` : "segment"}
            onClick={() => setParams(f ? { status: f } : {})}
          >
            {f ? STATUS_LABEL[f] : "Todos"}
          </button>
        ))}
      </div>

      {isPending && <p className="loading">Carregando chamados…</p>}
      {error && <p className="error">{error.message}</p>}

      {tickets && tickets.length === 0 && (
        <div className="empty">
          <p className="empty-title">
            {status
              ? `Nenhum chamado ${STATUS_LABEL[status].toLowerCase()} agora.`
              : "Nenhum chamado por aqui."}
          </p>
          <p>Algum equipamento com problema? Abra um chamado e a equipe de TI acompanha.</p>
          <Link to="/chamados/novo" className="btn btn-primary">
            Abrir chamado
          </Link>
        </div>
      )}

      {tickets && tickets.length > 0 && (
        <div className={staff ? "ticket-list com-responsavel" : "ticket-list"}>
          <div className="ticket-head" aria-hidden>
            <span>Chamado</span>
            <span>Local</span>
            <span>Status</span>
            <span>Prioridade</span>
            {staff && <span>Responsável</span>}
            <span className="ticket-when">Aberto</span>
          </div>
          <ul>
            {tickets.map((t) => (
              <li key={t.id} className={`ticket-row s-${t.status}`}>
                <div className="ticket-main">
                  <Link to={`/chamados/${t.id}`} className="ticket-title">
                    {t.titulo}
                  </Link>
                  <span className="ticket-equip">
                    <span className="ticket-id">#{t.id}</span>
                    {t.equipment.tipo}
                    <AssetTag patrimonio={t.equipment.patrimonio} />
                  </span>
                </div>
                <span className="ticket-local">
                  {t.equipment.room.nome}
                  <small>Bloco {t.equipment.room.bloco}</small>
                </span>
                <span className="ticket-status">
                  <StatusBadge status={t.status} />
                </span>
                <span className="ticket-prio">
                  <PrioridadeBadge prioridade={t.prioridade} />
                </span>
                {staff && (
                  <span className="ticket-resp">
                    {t.assignee?.nome ?? <span className="muted">Ninguém</span>}
                  </span>
                )}
                <time
                  className="ticket-when"
                  dateTime={t.criado_em}
                  title={formatDateTime(t.criado_em)}
                >
                  {formatQuando(t.criado_em)}
                </time>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
