import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { isStaff, useAuth } from "../auth";
import { AssetTag, PrioridadeBadge, StatusBadge } from "../components/Badges";
import Icon from "../components/Icon";
import StatusActions from "../components/StatusActions";
import {
  ORDEM_STATUS,
  PRIORIDADE_LABEL,
  STATUS_LABEL,
  eventoLabel,
  formatDateTime,
} from "../labels";
import type { Prioridade, Status, SugestaoIA, TicketDetail, TicketUpdate } from "../types";

/** Por quanto tempo depois da abertura vale esperar a sugestão da IA. */
const ANALISE_MS = 90_000;

export default function TicketDetailPage() {
  const id = Number(useParams().id);
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const staff = isStaff(user);
  const ticket = useQuery({
    queryKey: ["ticket", id],
    queryFn: () => api.ticket(id),
    // A IA analisa o chamado logo depois da abertura: a equipe vê a sugestão chegar.
    refetchInterval: (query) => {
      const t = query.state.data;
      if (!staff || !t || t.sugestao_ia) return false;
      return Date.now() - new Date(t.criado_em).getTime() < ANALISE_MS ? 2000 : false;
    },
  });
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

  if (ticket.isPending) return <p className="loading">Carregando chamado…</p>;
  if (ticket.error) {
    return (
      <div className="empty">
        <p className="empty-title">{ticket.error.message}</p>
        <Link to="/" className="btn">
          Voltar para os chamados
        </Link>
      </div>
    );
  }

  const t = ticket.data;
  const mostrarTriagem = staff && t.status !== "fechado";

  return (
    <>
      <Link to="/" className="back">
        <Icon name="voltar" size={18} />
        Chamados
      </Link>

      <header className="detail-header">
        <p className="detail-id">Chamado #{t.id}</p>
        <h1>{t.titulo}</h1>
        <div className="detail-badges">
          <StatusBadge status={t.status} />
          <PrioridadeBadge prioridade={t.prioridade} />
        </div>
      </header>

      <Progresso status={t.status} />

      <div className="detail-grid">
        <section className="panel detail-info">
          <dl className="meta">
            <div>
              <dt>Local</dt>
              <dd>
                {t.equipment.room.nome}, bloco {t.equipment.room.bloco}
              </dd>
            </div>
            <div>
              <dt>Equipamento</dt>
              <dd className="meta-equip">
                {t.equipment.tipo} <AssetTag patrimonio={t.equipment.patrimonio} />
              </dd>
            </div>
            <div>
              <dt>Aberto por</dt>
              <dd>{t.requester.nome}</dd>
            </div>
            <div>
              <dt>Responsável</dt>
              <dd>{t.assignee?.nome ?? <span className="muted">Ninguém ainda</span>}</dd>
            </div>
            <div>
              <dt>Categoria</dt>
              <dd>{t.category?.nome ?? <span className="muted">A definir na triagem</span>}</dd>
            </div>
            <div>
              <dt>Aberto em</dt>
              <dd>{formatDateTime(t.criado_em)}</dd>
            </div>
          </dl>
          <h2 className="panel-title">Descrição</h2>
          <p className="descricao">{t.descricao}</p>
        </section>

        {(t.transicoes.length > 0 || mostrarTriagem) && (
          <aside className="detail-side">
            <StatusActions
              statusAtual={t.status}
              transicoes={t.transicoes}
              pending={mudarStatus.isPending}
              error={mudarStatus.error?.message}
              onSubmit={(status, comentario) => mudarStatus.mutate({ status, comentario })}
            />
            {mostrarTriagem && (
              <TriageForm
                key={`${t.prioridade}-${t.category_id}-${t.assignee_id}`}
                ticket={t}
                onSaved={aplicar}
              />
            )}
          </aside>
        )}

        <section className="panel detail-history">
          <h2 className="panel-title">Histórico</h2>
          {events.isPending && <p className="loading">Carregando…</p>}
          <ol className="timeline">
            {events.data?.map((e) => (
              <li key={e.id} className={`s-${e.para_status}`}>
                <p className="timeline-what">
                  <strong>{e.autor.nome}</strong> {eventoLabel(e.de_status, e.para_status)}
                </p>
                <time className="timeline-when" dateTime={e.criado_em}>
                  {formatDateTime(e.criado_em)}
                </time>
                {e.comentario && <p className="timeline-comment">{e.comentario}</p>}
              </li>
            ))}
          </ol>
        </section>
      </div>
    </>
  );
}

/** As quatro etapas do fluxo, com a atual destacada. */
function Progresso({ status }: { status: Status }) {
  const atual = ORDEM_STATUS.indexOf(status);
  return (
    <ol className="progresso" aria-label="Etapas do chamado">
      {ORDEM_STATUS.map((s, i) => {
        const estado = i < atual ? "feito" : i === atual ? "atual" : "depois";
        return (
          <li
            key={s}
            className={`etapa etapa-${estado}`}
            aria-current={estado === "atual" ? "step" : undefined}
          >
            <span className="etapa-marca" aria-hidden>
              {estado === "feito" || (estado === "atual" && s === "fechado") ? (
                <Icon name="check" size={14} />
              ) : (
                i + 1
              )}
            </span>
            <span className="etapa-nome">{STATUS_LABEL[s]}</span>
          </li>
        );
      })}
    </ol>
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
  const sugestao = ticket.sugestao_ia;
  const analisando =
    !sugestao && Date.now() - new Date(ticket.criado_em).getTime() < ANALISE_MS;

  return (
    <form className="panel" onSubmit={handleSubmit}>
      <h2 className="panel-title">Triagem</h2>
      {analisando && (
        <p className="ia-analisando" role="status">
          <span className="ia-pulso" aria-hidden />A IA está analisando o chamado…
        </p>
      )}
      {sugestao && (
        <SugestaoCard
          sugestao={sugestao}
          aplicada={
            prioridade === sugestao.prioridade_sugerida &&
            categoryId === (sugestao.categoria_sugerida?.id ?? null)
          }
          onUsar={() => {
            setPrioridade(sugestao.prioridade_sugerida);
            setCategoryId(sugestao.categoria_sugerida?.id ?? null);
          }}
        />
      )}
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
              {c.nome} (prazo de {c.sla_horas} h)
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

function SugestaoCard({
  sugestao,
  aplicada,
  onUsar,
}: {
  sugestao: SugestaoIA;
  aplicada: boolean;
  onUsar: () => void;
}) {
  const doModelo = sugestao.fonte === "llm";
  return (
    <section className="ia-card" aria-label="Sugestão da IA">
      <p className="ia-fonte">
        {doModelo
          ? "Sugestão da IA"
          : "Sugestão automática por palavras-chave (IA indisponível)"}
      </p>
      <div className="ia-valores">
        <span>{sugestao.categoria_sugerida?.nome ?? "Sem categoria"}</span>
        <PrioridadeBadge prioridade={sugestao.prioridade_sugerida} />
      </div>
      <p className="ia-motivo">{sugestao.justificativa}</p>
      <button type="button" className="btn btn-ia" onClick={onUsar} disabled={aplicada}>
        {aplicada ? "Sugestão aplicada" : "Usar sugestão"}
      </button>
    </section>
  );
}
