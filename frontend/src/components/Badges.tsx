import { PRIORIDADE_LABEL, STATUS_LABEL } from "../labels";
import type { Prioridade, Status } from "../types";

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`badge status-${status}`}>{STATUS_LABEL[status]}</span>;
}

export function PrioridadeBadge({ prioridade }: { prioridade: Prioridade }) {
  return <span className={`badge prioridade-${prioridade}`}>{PRIORIDADE_LABEL[prioridade]}</span>;
}
