import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "../App";

describe("App shell", () => {
  it("renders the Chinese dual-mode app frame", async () => {
    window.history.replaceState({}, "", "/");
    render(<App />);

    expect(screen.getByText("APKHacker")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "案件队列" })).toHaveAttribute("href", "/queue");
    expect(screen.getByRole("link", { name: "案件工作台" })).toHaveAttribute("href", "/workspace");
    expect(await screen.findByRole("heading", { name: "案件队列" })).toBeInTheDocument();
  });

  it("shows the workspace mode title when entering /workspace directly", async () => {
    window.history.replaceState({}, "", "/workspace");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "案件工作台" })).toBeInTheDocument();
    expect(screen.getByLabelText("当前模式")).toHaveTextContent("案件工作台");
  });

  it("keeps the Chinese shell for unknown routes", async () => {
    window.history.replaceState({}, "", "/not-found");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "案件队列" })).toBeInTheDocument();
    expect(screen.getByText("APKHacker")).toBeInTheDocument();
    expect(screen.getByLabelText("当前模式")).toHaveTextContent("案件队列");
    expect(screen.queryByText("Unexpected Application Error!")).not.toBeInTheDocument();
  });
});
