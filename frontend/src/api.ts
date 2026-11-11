import type {
  Category,
  ChamadosPorMes,
  ChamadosPorSala,
  EquipamentoRanking,
  Equipment,
  Room,
  Status,
  TempoResolucaoReport,
  Ticket,
  TicketDetail,
  TicketEvent,
  TicketUpdate,
  User,
  UserBrief,
} from "./types";

const TOKEN_KEY = "helpdesk.token";

// O acesso ao localStorage pode falhar (aba anônima, cookies bloqueados): nesse caso
// a sessão só dura até recarregar a página.
let memoryToken: string | null = null;

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY) ?? memoryToken;
    } catch {
      return memoryToken;
    }
  },
  set(token: string) {
    memoryToken = token;
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* fica só em memória */
    }
  },
  clear() {
    memoryToken = null;
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* nada a limpar */
    }
  },
};

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let onUnauthorized: () => void = () => {};

/** Chamado quando a API recusa o token (expirado ou inválido). */
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

async function errorMessage(resp: Response): Promise<string> {
  try {
    const body = await resp.json();
    if (typeof body.detail === "string") return body.detail;
    // Erros de validação do FastAPI chegam como lista.
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: { msg: string }) => d.msg.replace(/^Value error, /, "")).join("; ");
    }
  } catch {
    /* corpo não é JSON */
  }
  return `Erro ${resp.status}`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (typeof init.body === "string") headers.set("Content-Type", "application/json");

  const resp = await fetch(`/api${path}`, { ...init, headers });

  if (resp.status === 401 && token) {
    tokenStore.clear();
    onUnauthorized();
  }
  if (!resp.ok) throw new ApiError(resp.status, await errorMessage(resp));
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
});

export const api = {
  login: (email: string, senha: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username: email, password: senha }),
    }),
  me: () => request<User>("/auth/me"),

  tickets: (status?: Status) =>
    request<Ticket[]>(`/tickets?limit=100${status ? `&status=${status}` : ""}`),
  ticket: (id: number) => request<TicketDetail>(`/tickets/${id}`),
  events: (id: number) => request<TicketEvent[]>(`/tickets/${id}/events`),
  createTicket: (data: { titulo: string; descricao: string; equipment_id: number }) =>
    request<Ticket>("/tickets", json("POST", data)),
  updateTicket: (id: number, data: TicketUpdate) =>
    request<TicketDetail>(`/tickets/${id}`, json("PATCH", data)),
  changeStatus: (id: number, status: Status, comentario: string | null) =>
    request<TicketDetail>(`/tickets/${id}/status`, json("POST", { status, comentario })),

  rooms: () => request<Room[]>("/rooms"),
  equipment: (roomId: number) => request<Equipment[]>(`/equipment?room_id=${roomId}`),
  categories: () => request<Category[]>("/categories"),
  team: () => request<UserBrief[]>("/users/equipe"),

  reports: {
    tempoResolucao: () => request<TempoResolucaoReport>("/reports/tempo-resolucao"),
    equipamentos: () => request<EquipamentoRanking[]>("/reports/equipamentos"),
    salas: () => request<ChamadosPorSala[]>("/reports/salas"),
    mensal: () => request<ChamadosPorMes[]>("/reports/mensal"),
  },
};
