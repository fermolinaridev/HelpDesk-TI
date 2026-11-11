import { useState } from "react";

import { acaoLabel } from "../labels";
import type { Status, Transicao } from "../types";

interface Props {
  statusAtual: Status;
  transicoes: Transicao[];
  pending?: boolean;
  error?: string | null;
  onSubmit: (status: Status, comentario: string | null) => void;
}

/**
 * Botões de mudança de status. A API informa quais mudanças o usuário pode fazer agora
 * (e quais exigem comentário); aqui só exibimos. A regra continua sendo validada no backend.
 */
export default function StatusActions({ statusAtual, transicoes, pending, error, onSubmit }: Props) {
  const [comentario, setComentario] = useState("");

  if (transicoes.length === 0) return null;

  const texto = comentario.trim();
  const algumaExige = transicoes.some((t) => t.exige_comentario);

  return (
    <section className="panel panel-acao">
      <h2 className="panel-title">Andamento</h2>
      <label className="field">
        <span>Comentário{algumaExige ? "" : " (opcional)"}</span>
        <textarea
          rows={3}
          value={comentario}
          onChange={(e) => setComentario(e.target.value)}
          placeholder="Ex.: cabo HDMI substituído, testado com a professora."
        />
      </label>
      <div className="actions actions-stack">
        {transicoes.map((t) => {
          const faltaComentario = t.exige_comentario && !texto;
          return (
            <button
              key={t.status}
              type="button"
              className={t.status === "fechado" || t.status === "resolvido" ? "btn btn-primary" : "btn"}
              disabled={pending || faltaComentario}
              title={faltaComentario ? "Escreva um comentário para continuar" : undefined}
              onClick={() => {
                onSubmit(t.status, texto || null);
                setComentario("");
              }}
            >
              {acaoLabel(statusAtual, t.status)}
            </button>
          );
        })}
      </div>
      {algumaExige && !texto && (
        <p className="hint">Resolver ou reabrir um chamado exige comentário.</p>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
