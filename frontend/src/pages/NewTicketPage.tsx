import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";

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
        <h1>Novo chamado</h1>
      </div>

      <form className="card form" onSubmit={handleSubmit}>
        <div className="form-row">
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
                  Bloco {r.bloco} · {r.nome}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Equipamento</span>
            <select
              required
              disabled={roomId === null}
              value={equipmentId ?? ""}
              onChange={(e) => setEquipmentId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">
                {roomId === null ? "Escolha a sala primeiro" : "Selecione o equipamento…"}
              </option>
              {equipment.data?.map((eq) => (
                <option key={eq.id} value={eq.id}>
                  {eq.tipo} ({eq.patrimonio})
                </option>
              ))}
            </select>
            {equipment.data?.length === 0 && (
              <small className="muted">Nenhum equipamento cadastrado nesta sala.</small>
            )}
          </label>
        </div>

        <label className="field">
          <span>Título</span>
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
          <span>Descrição</span>
          <textarea
            required
            minLength={10}
            maxLength={5000}
            rows={5}
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            placeholder="O que aconteceu? Desde quando? Já tentou algo?"
          />
        </label>

        {criar.error && <p className="error">{criar.error.message}</p>}

        <div className="actions">
          <button type="submit" className="btn btn-primary" disabled={criar.isPending}>
            {criar.isPending ? "Abrindo…" : "Abrir chamado"}
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => navigate(-1)}>
            Cancelar
          </button>
        </div>
      </form>
    </>
  );
}
