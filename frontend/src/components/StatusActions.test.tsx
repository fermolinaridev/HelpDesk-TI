import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import StatusActions from "./StatusActions";

describe("StatusActions", () => {
  it("não mostra nada quando o usuário não pode mudar o status", () => {
    const { container } = render(
      <StatusActions statusAtual="aberto" transicoes={[]} onSubmit={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("mostra só as mudanças permitidas, com o texto certo para cada uma", () => {
    render(
      <StatusActions
        statusAtual="resolvido"
        transicoes={[
          { status: "fechado", exige_comentario: false },
          { status: "em_atendimento", exige_comentario: true },
        ]}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Confirmar e fechar" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reabrir chamado" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Iniciar atendimento" })).not.toBeInTheDocument();
  });

  it("só libera a ação que exige comentário depois que ele é escrito", async () => {
    const onSubmit = vi.fn();
    render(
      <StatusActions
        statusAtual="em_atendimento"
        transicoes={[{ status: "resolvido", exige_comentario: true }]}
        onSubmit={onSubmit}
      />,
    );
    const resolver = screen.getByRole("button", { name: "Marcar como resolvido" });
    expect(resolver).toBeDisabled();

    await userEvent.type(screen.getByRole("textbox"), "  Lâmpada trocada  ");
    await userEvent.click(resolver);

    expect(onSubmit).toHaveBeenCalledWith("resolvido", "Lâmpada trocada");
  });
});
