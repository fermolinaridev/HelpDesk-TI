import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { api, setUnauthorizedHandler, tokenStore } from "./api";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  /** true quando a pessoa clicou em Sair (e não quando a sessão expirou). */
  saiu: boolean;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => tokenStore.get() !== null);
  const [saiu, setSaiu] = useState(false);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      queryClient.clear();
      setUser(null);
    });
    if (!tokenStore.get()) return;
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, [queryClient]);

  const login = useCallback(
    async (email: string, senha: string) => {
      const { access_token } = await api.login(email, senha);
      tokenStore.set(access_token);
      queryClient.clear(); // nada em cache de outra sessão
      setUser(await api.me());
      setSaiu(false);
    },
    [queryClient],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    // Sem isto, quem entrar depois no mesmo navegador veria por um instante os dados
    // em cache da pessoa anterior.
    queryClient.clear();
    setSaiu(true);
    setUser(null);
  }, [queryClient]);

  const value = useMemo(
    () => ({ user, loading, saiu, login, logout }),
    [user, loading, saiu, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return ctx;
}

export const isStaff = (user: User | null) => user !== null && user.papel !== "solicitante";
