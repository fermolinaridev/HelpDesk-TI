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

/** O que a pessoa fez, para o histórico: "Carla iniciou o atendimento". */
export function eventoLabel(de: Status | null, para: Status): string {
  if (de === null) return "abriu o chamado";
  if (para === "em_atendimento") return de === "resolvido" ? "reabriu o chamado" : "iniciou o atendimento";
  if (para === "resolvido") return "marcou como resolvido";
  if (para === "fechado") return "confirmou a solução e fechou";
  return `mudou para ${STATUS_LABEL[para]}`;
}

export const ORDEM_STATUS: Status[] = ["aberto", "em_atendimento", "resolvido", "fechado"];

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });
const dayMonth = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" });
const time = new Intl.DateTimeFormat("pt-BR", { timeStyle: "short" });

export const formatDateTime = (iso: string) => dateTime.format(new Date(iso));

/** "hoje, 14:20", "ontem, 09:05" ou "08 de nov." — para listas. */
export function formatQuando(iso: string, agora = new Date()): string {
  const d = new Date(iso);
  const dias = Math.round(
    (new Date(agora.toDateString()).getTime() - new Date(d.toDateString()).getTime()) / 86_400_000,
  );
  if (dias === 0) return `hoje, ${time.format(d)}`;
  if (dias === 1) return `ontem, ${time.format(d)}`;
  return dayMonth.format(d);
}

export function iniciais(nome: string): string {
  const partes = nome.replace(/^(prof|profa)\.?\s+/i, "").split(/\s+/).filter(Boolean);
  return ((partes[0]?.[0] ?? "") + (partes.length > 1 ? partes[partes.length - 1][0] : "")).toUpperCase();
}

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
