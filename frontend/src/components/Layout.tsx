import { NavLink, Outlet } from "react-router-dom";

import { isStaff, useAuth } from "../auth";
import { PAPEL_LABEL } from "../labels";

export default function Layout() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <span className="brand">
            <span aria-hidden>🛠️</span> HelpDesk TI
          </span>
          <nav className="nav">
            <NavLink to="/" end>
              {isStaff(user) ? "Chamados" : "Meus chamados"}
            </NavLink>
            <NavLink to="/chamados/novo">Novo chamado</NavLink>
            {isStaff(user) && <NavLink to="/relatorios">Relatórios</NavLink>}
          </nav>
          <div className="whoami">
            <span>
              {user.nome} <small className="muted">· {PAPEL_LABEL[user.papel]}</small>
            </span>
            <button type="button" className="btn btn-ghost" onClick={logout}>
              Sair
            </button>
          </div>
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </div>
  );
}
