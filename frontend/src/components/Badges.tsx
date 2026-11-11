import { PRIORIDADE_LABEL, STATUS_LABEL } from "../labels";
import type { Prioridade, Status } from "../types";

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={`badge status-${status}`}>
      <span className="badge-dot" aria-hidden />
      {STATUS_LABEL[status]}
    </span>
  );
}

export function PrioridadeBadge({ prioridade }: { prioridade: Prioridade }) {
  return (
    <span className={`prioridade prioridade-${prioridade}`} title="Prioridade">
      <span className="prioridade-nivel" aria-hidden>
        <i />
        <i />
        <i />
        <i />
      </span>
      {PRIORIDADE_LABEL[prioridade]}
    </span>
  );
}

/** Número de patrimônio no formato da etiqueta colada no equipamento. */
export function AssetTag({ patrimonio }: { patrimonio: string }) {
  return (
    <span className="asset-tag" title="Número de patrimônio">
      <span className="asset-tag-hole" aria-hidden />
      {patrimonio}
    </span>
  );
}
