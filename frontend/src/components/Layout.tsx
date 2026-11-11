import { Link, NavLink, Outlet } from "react-router-dom";

import { isStaff, useAuth } from "../auth";
import { PAPEL_LABEL, iniciais } from "../labels";
import Icon, { BrandMark } from "./Icon";

export default function Layout() {
  const { user, logout } = useAuth();
  if (!user) return null;
  const staff = isStaff(user);

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/" className="brand">
            <BrandMark />
            <span>HelpDesk TI</span>
          </Link>

          <nav className="nav" aria-label="Principal">
            <NavLink to="/" end>
              <Icon name="lista" />
              <span>{staff ? "Chamados" : "Meus chamados"}</span>
            </NavLink>
            <NavLink to="/chamados/novo">
              <Icon name="mais" />
              <span>Novo chamado</span>
            </NavLink>
            {staff && (
              <NavLink to="/relatorios">
                <Icon name="grafico" />
                <span>Relatórios</span>
              </NavLink>
            )}
          </nav>

          <div className="whoami">
            <span className="avatar" aria-hidden>
              {iniciais(user.nome)}
            </span>
            <span className="whoami-text">
              <strong>{user.nome}</strong>
              <small>{PAPEL_LABEL[user.papel]}</small>
            </span>
            <button type="button" className="btn-sair" onClick={logout}>
              <Icon name="sair" size={18} />
              <span>Sair</span>
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
