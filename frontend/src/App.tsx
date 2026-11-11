import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { isStaff, useAuth } from "./auth";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import NewTicketPage from "./pages/NewTicketPage";
import ReportsPage from "./pages/ReportsPage";
import TicketDetailPage from "./pages/TicketDetailPage";
import TicketsPage from "./pages/TicketsPage";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading, saiu } = useAuth();
  const location = useLocation();

  if (loading) return <p className="page-loading">Carregando…</p>;
  if (!user) {
    // Sessão expirada: depois do login, volta para onde estava. Clicou em Sair: não volta,
    // porque quem entrar em seguida pode ser outra pessoa (computador da sala).
    const state = saiu ? undefined : { from: location.pathname };
    return <Navigate to="/login" replace state={state} />;
  }
  return children;
}

function RequireStaff({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  return isStaff(user) ? children : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<TicketsPage />} />
        <Route path="chamados/novo" element={<NewTicketPage />} />
        <Route path="chamados/:id" element={<TicketDetailPage />} />
        <Route
          path="relatorios"
          element={
            <RequireStaff>
              <ReportsPage />
            </RequireStaff>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
