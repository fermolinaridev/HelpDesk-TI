import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { api } from "../api";
import { AssetTag } from "../components/Badges";
import Bar from "../components/Bar";
import { formatHoras, formatMes, formatPct } from "../labels";
import type { AcertoIAReport } from "../types";

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
    <section className="panel report">
      <h2 className="panel-title">{title}</h2>
      <p className="report-sub">{subtitle}</p>
      <div className="table-wrap">{children}</div>
    </section>
  );
}

const Vazio = () => <p className="muted">Ainda não há chamados suficientes para este relatório.</p>;

export default function ReportsPage() {
  const tempo = useQuery({ queryKey: ["report", "tempo"], queryFn: api.reports.tempoResolucao });
  const equip = useQuery({ queryKey: ["report", "equip"], queryFn: api.reports.equipamentos });
  const salas = useQuery({ queryKey: ["report", "salas"], queryFn: api.reports.salas });
  const mensal = useQuery({ queryKey: ["report", "mensal"], queryFn: api.reports.mensal });
  const ia = useQuery({ queryKey: ["report", "ia"], queryFn: api.reports.ia });

  const maxEquip = Math.max(0, ...(equip.data?.map((e) => e.chamados) ?? []));
  const maxSala = Math.max(0, ...(salas.data?.map((s) => s.chamados) ?? []));
  const maxMes = Math.max(0, ...(mensal.data?.map((m) => m.chamados) ?? []));

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Relatórios</h1>
          <p className="page-sub">Como a equipe de TI está dando conta dos chamados.</p>
        </div>
      </div>

      {tempo.isPending && <p className="loading">Carregando relatórios…</p>}
      {tempo.error && <p className="error">{tempo.error.message}</p>}
      {tempo.data && (
        <dl className="kpis">
          <div>
            <dt>Chamados resolvidos</dt>
            <dd>{tempo.data.geral.resolvidos}</dd>
          </div>
          <div>
            <dt>Tempo médio até resolver</dt>
            <dd>{formatHoras(tempo.data.geral.horas_media)}</dd>
          </div>
          <div>
            <dt>Tempo mediano</dt>
            <dd>{formatHoras(tempo.data.geral.horas_mediana)}</dd>
          </div>
          <div>
            <dt>Resolvidos dentro do prazo</dt>
            <dd>{formatPct(tempo.data.geral.pct_no_sla)}</dd>
          </div>
        </dl>
      )}

      <div className="reports-grid">
        {ia.data && <AcertoIAPanel dados={ia.data} />}

        <ReportCard
          title="Tempo de resolução por categoria"
          subtitle="Da abertura até a resolução definitiva (chamados reabertos contam a última)."
        >
          {tempo.data?.por_categoria.length === 0 && <Vazio />}
          {!!tempo.data?.por_categoria.length && (
            <table className="table">
                <thead>
                  <tr>
                    <th>Categoria</th>
                    <th className="num">Resolvidos</th>
                    <th className="num">Média</th>
                    <th className="num">Mediana</th>
                    <th className="num">No prazo</th>
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
          )}
        </ReportCard>

        <ReportCard title="Equipamentos com mais chamados" subtitle="Os 10 que mais deram problema. Empatados dividem a posição.">
          {equip.data?.length === 0 && <Vazio />}
          {!!equip.data?.length && (
            <table className="table">
              <tbody>
                {equip.data.map((e) => (
                  <tr key={e.equipment_id}>
                    <td className="muted num">{e.posicao}º</td>
                    <td>
                      <span className="report-equip">
                        {e.tipo} <AssetTag patrimonio={e.patrimonio} />
                      </span>
                      <div className="muted small">
                        {e.sala}, bloco {e.bloco}
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

        <ReportCard title="Chamados por sala" subtitle="Total por sala, quantos ainda não foram resolvidos e a fatia de cada uma.">
          {salas.data?.length === 0 && <Vazio />}
          {!!salas.data?.length && (
            <table className="table">
              <thead>
                <tr>
                  <th>Sala</th>
                  <th />
                  <th className="num">Total</th>
                  <th className="num">Pendentes</th>
                  <th className="num">%</th>
                </tr>
              </thead>
              <tbody>
                {salas.data.map((s) => (
                  <tr key={s.room_id}>
                    <td>
                      {s.sala}
                      <div className="muted small">Bloco {s.bloco}</div>
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

const FONTE_LABEL: Record<string, string> = {
  llm: "IA (modelo de linguagem)",
  regras: "Palavras-chave (reserva)",
};

function AcertoIAPanel({ dados }: { dados: AcertoIAReport }) {
  const { geral } = dados;
  return (
    <section className="panel report report-wide">
      <h2 className="panel-title">Acerto da triagem por IA</h2>
      <p className="report-sub">
        A IA sugere categoria e prioridade quando o chamado é aberto. A equipe confirma ou
        corrige na triagem. {geral.avaliadas} de {geral.sugestoes} sugestões já foram avaliadas.
      </p>
      {geral.avaliadas === 0 ? (
        <Vazio />
      ) : (
        <div className="ia-report">
          <dl className="ia-taxas">
            <div>
              <dt>Categoria certa</dt>
              <dd>{formatPct(geral.pct_categoria)}</dd>
            </div>
            <div>
              <dt>Prioridade certa</dt>
              <dd>{formatPct(geral.pct_prioridade)}</dd>
            </div>
            <div>
              <dt>As duas certas</dt>
              <dd>{formatPct(geral.pct_ambos)}</dd>
            </div>
          </dl>

          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Quem sugeriu</th>
                  <th className="num">Avaliadas</th>
                  <th className="num">Categoria</th>
                  <th className="num">Prioridade</th>
                </tr>
              </thead>
              <tbody>
                {dados.por_fonte.map((f) => (
                  <tr key={f.fonte}>
                    <td>{FONTE_LABEL[f.fonte] ?? f.fonte}</td>
                    <td className="num">{f.avaliadas}</td>
                    <td className="num">{formatPct(f.pct_categoria)}</td>
                    <td className="num">{formatPct(f.pct_prioridade)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div>
            <h3 className="ia-sub">Correções mais comuns</h3>
            {dados.correcoes.length === 0 ? (
              <p className="muted">Nenhuma categoria foi corrigida até agora.</p>
            ) : (
              <ul className="ia-correcoes">
                {dados.correcoes.map((c) => (
                  <li key={`${c.sugerida}-${c.final}`}>
                    <span>
                      Sugeriu <strong>{c.sugerida}</strong>, era <strong>{c.final}</strong>
                    </span>
                    <span className="num">{c.vezes}×</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
