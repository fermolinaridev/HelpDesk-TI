// Tipos espelhando os schemas da API (app/schemas.py).

export type Papel = "solicitante" | "tecnico" | "admin";
export type Status = "aberto" | "em_atendimento" | "resolvido" | "fechado";
export type Prioridade = "baixa" | "media" | "alta" | "critica";

export interface User {
  id: number;
  nome: string;
  email: string;
  papel: Papel;
}

export interface UserBrief {
  id: number;
  nome: string;
  papel: Papel;
}

export interface Room {
  id: number;
  nome: string;
  bloco: string;
}

export interface Equipment {
  id: number;
  tipo: string;
  patrimonio: string;
  room_id: number;
}

export interface Category {
  id: number;
  nome: string;
  sla_horas: number;
}

export interface Ticket {
  id: number;
  titulo: string;
  descricao: string;
  status: Status;
  prioridade: Prioridade;
  category_id: number | null;
  equipment_id: number;
  requester_id: number;
  assignee_id: number | null;
  criado_em: string;
  category: Category | null;
  equipment: { id: number; tipo: string; patrimonio: string; room: Room };
  requester: UserBrief;
  assignee: UserBrief | null;
}

export interface Transicao {
  status: Status;
  exige_comentario: boolean;
}

export interface SugestaoIA {
  fonte: "llm" | "regras";
  modelo: string | null;
  categoria_sugerida: Category | null;
  prioridade_sugerida: Prioridade;
  justificativa: string;
  criado_em: string;
  avaliado_em: string | null;
}

export interface TicketDetail extends Ticket {
  transicoes: Transicao[];
  /** null enquanto a IA analisa o chamado, ou para o solicitante. */
  sugestao_ia: SugestaoIA | null;
}

export interface TicketEvent {
  id: number;
  de_status: Status | null;
  para_status: Status;
  comentario: string | null;
  criado_em: string;
  autor: UserBrief;
}

export interface TicketUpdate {
  prioridade?: Prioridade;
  category_id?: number | null;
  assignee_id?: number | null;
}

// --- Relatórios ---

export interface TempoResolucao {
  categoria: string;
  resolvidos: number;
  horas_media: number | null;
  horas_mediana: number | null;
  pct_no_sla: number | null;
}

export interface TempoResolucaoReport {
  geral: TempoResolucao;
  por_categoria: TempoResolucao[];
}

export interface EquipamentoRanking {
  posicao: number;
  equipment_id: number;
  tipo: string;
  patrimonio: string;
  sala: string;
  bloco: string;
  chamados: number;
}

export interface ChamadosPorSala {
  room_id: number;
  bloco: string;
  sala: string;
  chamados: number;
  em_aberto: number;
  pct_do_total: number | null;
}

export interface ChamadosPorMes {
  mes: string;
  chamados: number;
  variacao: number | null;
  acumulado: number;
}

export interface AcertoIA {
  fonte: "llm" | "regras" | "todas";
  sugestoes: number;
  avaliadas: number;
  pct_categoria: number | null;
  pct_prioridade: number | null;
  pct_ambos: number | null;
}

export interface AcertoIAReport {
  geral: AcertoIA;
  por_fonte: AcertoIA[];
  correcoes: { sugerida: string; final: string; vezes: number }[];
}
