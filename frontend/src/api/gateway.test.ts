/**
 * 网关 API 单元测试：fetchCellList 构建的 URL 与参数
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchCellList } from "./gateway";

describe("gateway fetchCellList", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("builds URL with path only when no params", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: [], total: 0 }),
      headers: new Headers({ "content-type": "application/json" }),
    } as Response);

    await fetchCellList("crm", "/customers");

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/crm/customers"),
      expect.any(Object)
    );
    const url = (mockFetch.mock.calls[0][0] as string);
    expect(url).not.toContain("page=");
  });

  it("builds URL with page and pageSize when provided", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: [], total: 0 }),
      headers: new Headers({ "content-type": "application/json" }),
    } as Response);

    await fetchCellList("erp", "/orders", { page: 2, pageSize: 20 });

    const url = (mockFetch.mock.calls[0][0] as string);
    expect(url).toContain("/api/v1/erp/orders");
    expect(url).toContain("page=2");
    expect(url).toContain("pageSize=20");
  });
});
