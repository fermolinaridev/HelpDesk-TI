const PATHS = {
  lista: "M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01",
  mais: "M12 5v14M5 12h14",
  grafico: "M3 3v18h18M8 17v-5M13 17V8M18 17v-3",
  sair: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
  voltar: "M15 18l-6-6 6-6",
  check: "M20 6 9 17l-5-5",
} as const;

export type IconName = keyof typeof PATHS;

export default function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d={PATHS[name]} />
    </svg>
  );
}

/** Marca do sistema: uma etiqueta de patrimônio, como as coladas nos equipamentos da escola. */
export function BrandMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden className="brand-mark">
      <rect x="2" y="7" width="28" height="18" rx="4" fill="#F4C430" />
      <circle cx="8" cy="16" r="2.5" fill="#1E4D3B" />
      <path
        d="M14 11.5v9M16.8 11.5v9M19.2 11.5v9M22.4 11.5v9M25 11.5v9"
        stroke="#1E4D3B"
        strokeWidth="1.6"
      />
    </svg>
  );
}
