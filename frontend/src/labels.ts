import type { Papel, Prioridade, Status } from "./types";

export const STATUS_LABEL: Record<Status, string> = {
  aberto: "Aberto",
  em_atendimento: "Em atendimento",
  resolvido: "Resolvido",
  fechado: "Fechado",
};

export const PRIORIDADE_LABEL: Record<Prioridade, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
  critica: "Crítica",
};

export const PAPEL_LABEL: Record<Papel, string> = {
  solicitante: "Professor(a)",
  tecnico: "Técnico(a)",
  admin: "Admin",
};

/** Texto do botão de uma mudança de status, que depende de onde o chamado está. */
export function acaoLabel(de: Status, para: Status): string {
  if (para === "em_atendimento") return de === "resolvido" ? "Reabrir chamado" : "Iniciar atendimento";
  if (para === "resolvido") return "Marcar como resolvido";
  if (para === "fechado") return "Confirmar e fechar";
  return STATUS_LABEL[para];
}

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

export const formatDateTime = (iso: string) => dateTime.format(new Date(iso));

export function formatHoras(horas: number | null): string {
  if (horas === null) return "—";
  if (horas < 1) return `${Math.round(horas * 60)} min`;
  return `${horas.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} h`;
}

export const formatPct = (pct: number | null) =>
  pct === null ? "—" : `${pct.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;

export function formatMes(mes: string): string {
  const [ano, m] = mes.split("-").map(Number);
  return new Date(ano, m - 1, 1).toLocaleDateString("pt-BR", { month: "short", year: "numeric" });
}
