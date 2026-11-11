import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../auth";
import LoginPage from "./LoginPage";

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderLogin() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<p>Página inicial</p>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function preencherEEntrar() {
  await userEvent.type(screen.getByLabelText("E-mail"), "prof@escola.example.com");
  await userEvent.type(screen.getByLabelText("Senha"), "senha-segura-123");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
}

describe("LoginPage", () => {
  it("mostra a mensagem da API quando a senha está errada", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(401, { detail: "E-mail ou senha incorretos" }),
    );
    renderLogin();

    await preencherEEntrar();

    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou senha incorretos");
  });

  it("guarda o token e vai para a página inicial após o login", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(200, { access_token: "token-123" }))
      .mockResolvedValueOnce(
        jsonResponse(200, { id: 1, nome: "Prof.", email: "p@e.com", papel: "solicitante" }),
      );
    renderLogin();

    await preencherEEntrar();

    expect(await screen.findByText("Página inicial")).toBeInTheDocument();
    expect(localStorage.getItem("helpdesk.token")).toBe("token-123");
    const [, meInit] = fetchMock.mock.calls[1];
    expect(new Headers(meInit?.headers).get("Authorization")).toBe("Bearer token-123");
  });
});
