/**
 * CellCreate 表单校验与渲染单元测试
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CellCreate } from "./CellCreate";

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { username: "test", role: "admin", allowedCells: ["crm"] },
  }),
}));

function renderWithRouter() {
  return render(
    <MemoryRouter initialEntries={["/cell/crm/new"]}>
      <Routes>
        <Route path="/cell/:cellId/new" element={<CellCreate />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("CellCreate", () => {
  it("renders create form for crm with fields", () => {
    renderWithRouter();
    expect(screen.getByText(/客户关系 · 新建/)).toBeInTheDocument();
    expect(screen.getByText("客户名称")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("必填")).toBeInTheDocument();
  });

  it("shows validation error when required field is empty", async () => {
    renderWithRouter();
    const submit = screen.getByRole("button", { name: /提交/ });
    fireEvent.click(submit);
    expect(await screen.findByText(/请填写客户名称/)).toBeInTheDocument();
  });
});
