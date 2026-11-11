import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { AssetTag } from "../components/Badges";

export default function NewTicketPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [roomId, setRoomId] = useState<number | null>(null);
  const [equipmentId, setEquipmentId] = useState<number | null>(null);
  const [titulo, setTitulo] = useState("");
  const [descricao, setDescricao] = useState("");

  const rooms = useQuery({ queryKey: ["rooms"], queryFn: api.rooms });
  const equipment = useQuery({
    queryKey: ["equipment", roomId],
    queryFn: () => api.equipment(roomId!),
    enabled: roomId !== null,
  });

  const criar = useMutation({
    mutationFn: api.createTicket,
    onSuccess: (ticket) => {
      queryClient.invalidateQueries({ queryKey: ["tickets"] });
      navigate(`/chamados/${ticket.id}`);
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (equipmentId === null) return;
    criar.mutate({ titulo, descricao, equipment_id: equipmentId });
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Novo chamado</h1>
          <p className="page-sub">Conte onde está o problema e o que está acontecendo.</p>
        </div>
      </div>

      <form className="form" onSubmit={handleSubmit}>
        <fieldset className="panel">
          <legend>Onde está o problema?</legend>
          <label className="field">
            <span>Sala</span>
            <select
              required
              value={roomId ?? ""}
              onChange={(e) => {
                setRoomId(e.target.value ? Number(e.target.value) : null);
                setEquipmentId(null);
              }}
            >
              <option value="">Selecione a sala…</option>
              {rooms.data?.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.nome} (bloco {r.bloco})
                </option>
              ))}
            </select>
          </label>

          {roomId !== null && (
            <div className="field" role="radiogroup" aria-labelledby="equip-label">
              <span id="equip-label">Equipamento</span>
              {equipment.isPending && <p className="loading">Carregando equipamentos…</p>}
              {equipment.data?.length === 0 && (
                <p className="hint">
                  Nenhum equipamento cadastrado nesta sala. Fale com a equipe de TI.
                </p>
              )}
              <div className="equip-grid">
                {equipment.data?.map((eq) => (
                  <label key={eq.id} className="equip-option">
                    <input
                      type="radio"
                      name="equipamento"
                      value={eq.id}
                      aria-label={`${eq.tipo}, patrimônio ${eq.patrimonio}`}
                      required
                      checked={equipmentId === eq.id}
                      onChange={() => setEquipmentId(eq.id)}
                    />
                    <span className="equip-tipo">{eq.tipo}</span>
                    <AssetTag patrimonio={eq.patrimonio} />
                  </label>
                ))}
              </div>
            </div>
          )}
        </fieldset>

        <fieldset className="panel">
          <legend>O que está acontecendo?</legend>
          <label className="field">
            <span>Resumo</span>
            <input
              required
              minLength={5}
              maxLength={150}
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              placeholder="Ex.: Projetor não liga"
            />
          </label>

          <label className="field">
            <span>Detalhes</span>
            <textarea
              required
              minLength={10}
              maxLength={5000}
              rows={5}
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Desde quando acontece? Aparece alguma mensagem? Já tentou algo?"
            />
          </label>
        </fieldset>

        {criar.error && <p className="error">{criar.error.message}</p>}

        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={() => navigate(-1)}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={criar.isPending}>
            {criar.isPending ? "Abrindo…" : "Abrir chamado"}
          </button>
        </div>
      </form>
    </>
  );
}
