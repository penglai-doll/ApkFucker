import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "../App";

describe("App shell", () => {
  it("renders the Chinese workspace frame", () => {
    render(<App />);

    expect(screen.getByText("APKHacker")).toBeInTheDocument();
    expect(screen.getByText("案件队列")).toBeInTheDocument();
  });
});
