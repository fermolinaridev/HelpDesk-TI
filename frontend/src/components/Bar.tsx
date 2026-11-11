/** Barra horizontal simples para comparar valores em tabelas de relatório. */
export default function Bar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="bar" aria-hidden>
      <span style={{ width: `${pct}%` }} />
    </div>
  );
}
