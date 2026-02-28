/**
 * 统一请求模块单元测试：buildHeaders、getGatewayHeaders、newRequestId
 */
import { describe, it, expect, beforeEach } from "vitest";
import { buildHeaders, getGatewayHeaders, getStoredToken, AUTH_KEY } from "./request";

describe("request", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("buildHeaders includes Content-Type and X-Request-ID", () => {
    const h = buildHeaders();
    expect(h["Content-Type"]).toBe("application/json");
    expect(h["X-Request-ID"]).toBeDefined();
    expect(typeof h["X-Request-ID"]).toBe("string");
    expect(h["X-Request-ID"].length).toBeGreaterThan(0);
  });

  it("buildHeaders includes X-Tenant-Id", () => {
    const h = buildHeaders();
    expect(h["X-Tenant-Id"]).toBeDefined();
  });

  it("buildHeaders includes Authorization when token present", () => {
    localStorage.setItem(AUTH_KEY, JSON.stringify({ token: "test-token" }));
    const h = buildHeaders();
    expect(h.Authorization).toBe("Bearer test-token");
  });

  it("buildHeaders skips Authorization when skipAuth true", () => {
    localStorage.setItem(AUTH_KEY, JSON.stringify({ token: "test-token" }));
    const h = buildHeaders({ skipAuth: true });
    expect(h.Authorization).toBeUndefined();
  });

  it("getGatewayHeaders returns object with headers", () => {
    const h = getGatewayHeaders();
    expect(h["Content-Type"]).toBe("application/json");
    expect(h["X-Request-ID"]).toBeDefined();
  });

  it("getStoredToken returns null when empty", () => {
    expect(getStoredToken()).toBeNull();
  });

  it("getStoredToken returns token from localStorage", () => {
    localStorage.setItem(AUTH_KEY, JSON.stringify({ token: "abc" }));
    expect(getStoredToken()).toBe("abc");
  });
});
