import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CaseQueuePage } from "../pages/CaseQueuePage";
import { listCases } from "../lib/api";

vi.mock("../lib/api", () => ({
  listCases: vi.fn(),
}));

describe("CaseQueuePage", () => {
  beforeEach(() => {
    vi.mocked(listCases).mockReset();
  });

  it("renders queue items from the first API call", async () => {
    vi.mocked(listCases).mockResolvedValue({
      items: [
        {
          case_id: "case-001",
          title: "Alpha 样本",
          workspace_root: "/tmp/workspaces/case-001",
        },
      ],
    });

    render(<CaseQueuePage />);

    expect(screen.getByText("案件队列")).toBeInTheDocument();
    expect(await screen.findByRole("cell", { name: "Alpha 样本" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "case-001" })).toBeInTheDocument();
    expect(vi.mocked(listCases)).toHaveBeenCalledTimes(1);
  });
});
