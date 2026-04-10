import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CaseQueuePage } from "../pages/CaseQueuePage";

describe("CaseQueuePage", () => {
  it("renders the queue title in Chinese", () => {
    render(<CaseQueuePage />);

    expect(screen.getByText("案件队列")).toBeInTheDocument();
  });
});
