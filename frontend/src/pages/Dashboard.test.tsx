/**
 * Dashboard 单元测试：渲染与细胞状态展示
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Dashboard } from "./Dashboard";

vi.mock("@/api/cells", () => ({
  useAllowedCells: () => ({
    cells: [
      { id: "crm", name: "客户关系", description: "CRM" },
      { id: "erp", name: "企业资源", description: "ERP" },
    ],
    loading: false,
    error: null,
  }),
}));

vi.mock("@/api/gateway", () => ({
  fetchCellHealth: () => Promise.resolve({ ok: true, data: { cell: "ok" }, status: 200 }),
}));

describe("Dashboard", () => {
  it("renders title and subtitle", () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );
    expect(screen.getByText("概览")).toBeInTheDocument();
    expect(screen.getByText(/各细胞模块运行状态/)).toBeInTheDocument();
  });

  it("renders cell cards when allowed cells exist", async () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );
    await waitFor(
      () => {
        expect(screen.getByText("客户关系")).toBeInTheDocument();
        expect(screen.getByText("企业资源")).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });
});
