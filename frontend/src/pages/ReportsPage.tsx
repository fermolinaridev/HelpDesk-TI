import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { api } from "../api";
import Bar from "../components/Bar";
import { formatHoras, formatMes, formatPct } from "../labels";

function ReportCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section className="card report">
      <h2 className="card-title">{title}</h2>
      <p className="muted small">{subtitle}</p>
      {children}
    </section>
  );
}

const Vazio = () => <p className="muted">Ainda não há dados.</p>;

export default function ReportsPage() {
  const tempo = useQuery({ queryKey: ["report", "tempo"], queryFn: api.reports.tempoResolucao });
  const equip = useQuery({ queryKey: ["report", "equip"], queryFn: api.reports.equipamentos });
  const salas = useQuery({ queryKey: ["report", "salas"], queryFn: api.reports.salas });
  const mensal = useQuery({ queryKey: ["report", "mensal"], queryFn: api.reports.mensal });

  const maxEquip = Math.max(0, ...(equip.data?.map((e) => e.chamados) ?? []));
  const maxSala = Math.max(0, ...(salas.data?.map((s) => s.chamados) ?? []));
  const maxMes = Math.max(0, ...(mensal.data?.map((m) => m.chamados) ?? []));

  return (
    <>
      <div className="page-header">
        <h1>Relatórios</h1>
      </div>

      {tempo.data && (
        <div className="kpis">
          <div className="card kpi">
            <span className="kpi-value">{tempo.data.geral.resolvidos}</span>
            <span className="muted small">chamados resolvidos</span>
          </div>
          <div className="card kpi">
            <span className="kpi-value">{formatHoras(tempo.data.geral.horas_media)}</span>
            <span className="muted small">tempo médio de resolução</span>
          </div>
          <div className="card kpi">
            <span className="kpi-value">{formatHoras(tempo.data.geral.horas_mediana)}</span>
            <span className="muted small">tempo mediano</span>
          </div>
          <div className="card kpi">
            <span className="kpi-value">{formatPct(tempo.data.geral.pct_no_sla)}</span>
            <span className="muted small">resolvidos dentro do SLA</span>
          </div>
        </div>
      )}

      <div className="reports-grid">
        <ReportCard
          title="Tempo de resolução por categoria"
          subtitle="Da abertura até a resolução definitiva (chamados reabertos contam a última)."
        >
          {tempo.data?.por_categoria.length === 0 && <Vazio />}
          {!!tempo.data?.por_categoria.length && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Categoria</th>
                    <th className="num">Resolvidos</th>
                    <th className="num">Média</th>
                    <th className="num">Mediana</th>
                    <th className="num">No SLA</th>
                  </tr>
                </thead>
                <tbody>
                  {tempo.data.por_categoria.map((c) => (
                    <tr key={c.categoria}>
                      <td>{c.categoria}</td>
                      <td className="num">{c.resolvidos}</td>
                      <td className="num">{formatHoras(c.horas_media)}</td>
                      <td className="num">{formatHoras(c.horas_mediana)}</td>
                      <td className="num">{formatPct(c.pct_no_sla)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ReportCard>

        <ReportCard title="Equipamentos com mais chamados" subtitle="Top 10; empates dividem a posição.">
          {equip.data?.length === 0 && <Vazio />}
          {!!equip.data?.length && (
            <table className="table">
              <tbody>
                {equip.data.map((e) => (
                  <tr key={e.equipment_id}>
                    <td className="muted num">{e.posicao}º</td>
                    <td>
                      {e.tipo} <span className="muted small">({e.patrimonio})</span>
                      <div className="muted small">
                        {e.sala} · Bloco {e.bloco}
                      </div>
                    </td>
                    <td className="bar-cell">
                      <Bar value={e.chamados} max={maxEquip} />
                    </td>
                    <td className="num">{e.chamados}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ReportCard>

        <ReportCard title="Chamados por sala" subtitle="Total, quantos ainda em aberto e % do total.">
          {salas.data?.length === 0 && <Vazio />}
          {!!salas.data?.length && (
            <table className="table">
              <thead>
                <tr>
                  <th>Sala</th>
                  <th />
                  <th className="num">Total</th>
                  <th className="num">Em aberto</th>
                  <th className="num">%</th>
                </tr>
              </thead>
              <tbody>
                {salas.data.map((s) => (
                  <tr key={s.room_id}>
                    <td>
                      {s.sala} <span className="muted small">· Bloco {s.bloco}</span>
                    </td>
                    <td className="bar-cell">
                      <Bar value={s.chamados} max={maxSala} />
                    </td>
                    <td className="num">{s.chamados}</td>
                    <td className="num">{s.em_aberto}</td>
                    <td className="num">{formatPct(s.pct_do_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ReportCard>

        <ReportCard title="Chamados por mês" subtitle="Meses sem chamados aparecem com zero.">
          {mensal.data?.length === 0 && <Vazio />}
          {!!mensal.data?.length && (
            <table className="table">
              <thead>
                <tr>
                  <th>Mês</th>
                  <th />
                  <th className="num">Chamados</th>
                  <th className="num">Variação</th>
                  <th className="num">Acumulado</th>
                </tr>
              </thead>
              <tbody>
                {mensal.data.map((m) => (
                  <tr key={m.mes}>
                    <td className="nowrap">{formatMes(m.mes)}</td>
                    <td className="bar-cell">
                      <Bar value={m.chamados} max={maxMes} />
                    </td>
                    <td className="num">{m.chamados}</td>
                    <td className="num">
                      {m.variacao === null ? "—" : m.variacao > 0 ? `+${m.variacao}` : m.variacao}
                    </td>
                    <td className="num">{m.acumulado}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ReportCard>
      </div>
    </>
  );
}
