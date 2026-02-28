/**
 * 细胞列表与权限 API 单元测试
 */
import { describe, it, expect, vi } from "vitest";
import { fetchAllowedCellsFromGateway } from "./cells";

vi.mock("./gateway", () => ({
  fetchGatewayCells: vi.fn(),
}));

const { fetchGatewayCells } = await import("./gateway");

describe("cells api", () => {
  it("fetchAllowedCellsFromGateway returns empty when fetch fails", async () => {
    vi.mocked(fetchGatewayCells).mockResolvedValueOnce({ ok: false, status: 500 });

    const result = await fetchAllowedCellsFromGateway(null);
    expect(result).toEqual([]);
  });

  it("fetchAllowedCellsFromGateway returns cells from gateway data", async () => {
    vi.mocked(fetchGatewayCells).mockResolvedValueOnce({
      ok: true,
      status: 200,
      data: { data: [{ id: "crm", name: "客户关系" }] },
    });

    const result = await fetchAllowedCellsFromGateway({ role: "admin", allowedCells: [] });
    expect(result.length).toBeGreaterThan(0);
    expect(result[0].id).toBe("crm");
  });
});
