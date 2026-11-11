import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { isStaff, useAuth } from "../auth";
import { PrioridadeBadge, StatusBadge } from "../components/Badges";
import StatusActions from "../components/StatusActions";
import { PRIORIDADE_LABEL, STATUS_LABEL, formatDateTime } from "../labels";
import type { Prioridade, Status, TicketDetail, TicketUpdate } from "../types";

export default function TicketDetailPage() {
  const id = Number(useParams().id);
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const ticket = useQuery({ queryKey: ["ticket", id], queryFn: () => api.ticket(id) });
  const events = useQuery({ queryKey: ["events", id], queryFn: () => api.events(id) });

  // Depois de uma mudança, a API devolve o chamado atualizado: usamos direto no cache.
  const aplicar = (atualizado: TicketDetail) => {
    queryClient.setQueryData(["ticket", id], atualizado);
    queryClient.invalidateQueries({ queryKey: ["events", id] });
    queryClient.invalidateQueries({ queryKey: ["tickets"] });
  };

  const mudarStatus = useMutation({
    mutationFn: ({ status, comentario }: { status: Status; comentario: string | null }) =>
      api.changeStatus(id, status, comentario),
    onSuccess: aplicar,
  });

  if (ticket.isPending) return <p className="muted">Carregando chamado…</p>;
  if (ticket.error) {
    return (
      <div className="card empty">
        <p className="error">{ticket.error.message}</p>
        <Link to="/">Voltar para os chamados</Link>
      </div>
    );
  }

  const t = ticket.data;

  return (
    <>
      <Link to="/" className="back">
        ← Chamados
      </Link>
      <div className="page-header">
        <h1>
          <span className="muted">#{t.id}</span> {t.titulo}
        </h1>
        <div className="badges">
          <StatusBadge status={t.status} />
          <PrioridadeBadge prioridade={t.prioridade} />
        </div>
      </div>

      <div className="detail-grid">
        <div className="detail-main">
          <section className="card">
            <dl className="meta">
              <div>
                <dt>Local</dt>
                <dd>
                  {t.equipment.room.nome} · Bloco {t.equipment.room.bloco}
                </dd>
              </div>
              <div>
                <dt>Equipamento</dt>
                <dd>
                  {t.equipment.tipo} <span className="muted">({t.equipment.patrimonio})</span>
                </dd>
              </div>
              <div>
                <dt>Solicitante</dt>
                <dd>{t.requester.nome}</dd>
              </div>
              <div>
                <dt>Responsável</dt>
                <dd>{t.assignee?.nome ?? <span className="muted">Ninguém ainda</span>}</dd>
              </div>
              <div>
                <dt>Categoria</dt>
                <dd>{t.category?.nome ?? <span className="muted">Sem categoria</span>}</dd>
              </div>
              <div>
                <dt>Aberto em</dt>
                <dd>{formatDateTime(t.criado_em)}</dd>
              </div>
            </dl>
            <h2 className="card-title">Descrição</h2>
            <p className="descricao">{t.descricao}</p>
          </section>

          <section className="card">
            <h2 className="card-title">Histórico</h2>
            {events.isPending && <p className="muted">Carregando…</p>}
            <ol className="timeline">
              {events.data?.map((e) => (
                <li key={e.id}>
                  <div className="timeline-head">
                    <strong>
                      {e.de_status === null
                        ? "Chamado aberto"
                        : `${STATUS_LABEL[e.de_status]} → ${STATUS_LABEL[e.para_status]}`}
                    </strong>
                    <span className="muted small">
                      {e.autor.nome} · {formatDateTime(e.criado_em)}
                    </span>
                  </div>
                  {e.comentario && <p className="timeline-comment">{e.comentario}</p>}
                </li>
              ))}
            </ol>
          </section>
        </div>

        <aside className="detail-side">
          <StatusActions
            statusAtual={t.status}
            transicoes={t.transicoes}
            pending={mudarStatus.isPending}
            error={mudarStatus.error?.message}
            onSubmit={(status, comentario) => mudarStatus.mutate({ status, comentario })}
          />
          {isStaff(user) && t.status !== "fechado" && (
            <TriageForm
              key={`${t.prioridade}-${t.category_id}-${t.assignee_id}`}
              ticket={t}
              onSaved={aplicar}
            />
          )}
        </aside>
      </div>
    </>
  );
}

function TriageForm({
  ticket,
  onSaved,
}: {
  ticket: TicketDetail;
  onSaved: (t: TicketDetail) => void;
}) {
  const [prioridade, setPrioridade] = useState<Prioridade>(ticket.prioridade);
  const [categoryId, setCategoryId] = useState<number | null>(ticket.category_id);
  const [assigneeId, setAssigneeId] = useState<number | null>(ticket.assignee_id);

  const categories = useQuery({ queryKey: ["categories"], queryFn: api.categories });
  const team = useQuery({ queryKey: ["team"], queryFn: api.team });

  const salvar = useMutation({
    mutationFn: (data: TicketUpdate) => api.updateTicket(ticket.id, data),
    onSuccess: onSaved,
  });

  const alterado =
    prioridade !== ticket.prioridade ||
    categoryId !== ticket.category_id ||
    assigneeId !== ticket.assignee_id;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    salvar.mutate({ prioridade, category_id: categoryId, assignee_id: assigneeId });
  }

  const toId = (value: string) => (value ? Number(value) : null);

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2 className="card-title">Triagem</h2>
      <label className="field">
        <span>Prioridade</span>
        <select value={prioridade} onChange={(e) => setPrioridade(e.target.value as Prioridade)}>
          {Object.entries(PRIORIDADE_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Categoria</span>
        <select value={categoryId ?? ""} onChange={(e) => setCategoryId(toId(e.target.value))}>
          <option value="">Sem categoria</option>
          {categories.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nome} (SLA {c.sla_horas} h)
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Responsável</span>
        <select value={assigneeId ?? ""} onChange={(e) => setAssigneeId(toId(e.target.value))}>
          <option value="">Ninguém</option>
          {team.data?.map((u) => (
            <option key={u.id} value={u.id}>
              {u.nome}
            </option>
          ))}
        </select>
      </label>
      {salvar.error && <p className="error">{salvar.error.message}</p>}
      <button type="submit" className="btn btn-block" disabled={!alterado || salvar.isPending}>
        {salvar.isPending ? "Salvando…" : "Salvar triagem"}
      </button>
    </form>
  );
}
