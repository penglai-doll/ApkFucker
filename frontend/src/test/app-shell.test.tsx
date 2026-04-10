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
});
