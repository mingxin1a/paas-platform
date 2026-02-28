/**
 * Layout 单元测试：侧栏、导航、权限过滤
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./Layout";

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { username: "admin", role: "admin", allowedCells: [] },
    logout: vi.fn(),
  }),
}));

vi.mock("@/api/cells", () => ({
  useAllowedCells: () => ({
    cells: [{ id: "crm", name: "客户关系" }],
    loading: false,
    error: null,
  }),
}));

describe("Layout", () => {
  it("renders header and sidebar with allowed cells", () => {
    render(
      <MemoryRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<div>Child</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText("SuperPaaS 控制台")).toBeInTheDocument();
    expect(screen.getByText("概览")).toBeInTheDocument();
    expect(screen.getByText("客户关系")).toBeInTheDocument();
  });
});
