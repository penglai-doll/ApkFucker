import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { CaseQueuePage } from "../pages/CaseQueuePage";
import { importCase, listCases } from "../lib/api";

const navigateMock = vi.fn();

vi.mock("../lib/api", () => ({
  listCases: vi.fn(),
  importCase: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");

  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

describe("CaseQueuePage", () => {
  beforeEach(() => {
    vi.mocked(listCases).mockReset();
    vi.mocked(importCase).mockReset();
    navigateMock.mockReset();
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

    render(
      <MemoryRouter>
        <CaseQueuePage />
      </MemoryRouter>,
    );

    expect(screen.getByText("案件队列")).toBeInTheDocument();
    expect(await screen.findByRole("cell", { name: "Alpha 样本" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "case-001" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "进入 Alpha 样本 工作台" })).toHaveAttribute(
      "href",
      "/workspace/case-001",
    );
    expect(vi.mocked(listCases)).toHaveBeenCalledTimes(1);
  });

  it("imports a case from text fields, refreshes the list, and navigates to the workspace", async () => {
    vi.mocked(listCases).mockResolvedValue({
      items: [
        {
          case_id: "case-001",
          title: "Alpha 样本",
          workspace_root: "/tmp/workspaces/case-001",
        },
      ],
    });
    vi.mocked(importCase).mockResolvedValue({
      case_id: "case-123",
      title: "导入案件",
      workspace_root: "/tmp/workspaces/case-123",
      sample_path: "/tmp/sample.apk",
    });

    render(
      <MemoryRouter>
        <CaseQueuePage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("样本路径"), { target: { value: "/tmp/sample.apk" } });
    fireEvent.change(screen.getByLabelText("workspace 根目录"), {
      target: { value: "/tmp/workspaces" },
    });
    fireEvent.change(screen.getByLabelText("案件标题"), { target: { value: "导入案件" } });
    fireEvent.submit(screen.getByRole("button", { name: "导入样本" }).closest("form")!);

    await waitFor(() => expect(vi.mocked(importCase)).toHaveBeenCalledTimes(1));
    expect(vi.mocked(importCase)).toHaveBeenCalledWith({
      sample_path: "/tmp/sample.apk",
      workspace_root: "/tmp/workspaces",
      title: "导入案件",
    });
    await waitFor(() => expect(vi.mocked(listCases)).toHaveBeenCalledTimes(2));
    expect(navigateMock).toHaveBeenCalledWith("/workspace/case-123");
  });

  it("shows a Chinese error message when importing fails", async () => {
    vi.mocked(listCases).mockResolvedValue({ items: [] });
    vi.mocked(importCase).mockRejectedValue(new Error("bad request"));

    render(
      <MemoryRouter>
        <CaseQueuePage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("样本路径"), { target: { value: "/tmp/sample.apk" } });
    fireEvent.change(screen.getByLabelText("workspace 根目录"), {
      target: { value: "/tmp/workspaces" },
    });
    fireEvent.change(screen.getByLabelText("案件标题"), { target: { value: "导入案件" } });
    fireEvent.submit(screen.getByRole("button", { name: "导入样本" }).closest("form")!);

    expect(await screen.findByRole("alert")).toHaveTextContent("导入案件失败，请检查样本路径和工作目录。");
    expect(navigateMock).not.toHaveBeenCalled();
  });
});
