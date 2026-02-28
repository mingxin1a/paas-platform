/**
 * 细胞配置单元测试：getCellById、getFieldLabel、CELLS 结构
 */
import { describe, it, expect } from "vitest";
import { CELLS, getCellById, getFieldLabel } from "./cells";

describe("cells config", () => {
  it("getCellById returns correct cell for crm", () => {
    const cell = getCellById("crm");
    expect(cell).toBeDefined();
    expect(cell?.id).toBe("crm");
    expect(cell?.path).toBe("/customers");
    expect(cell?.listKey).toBe("data");
    expect(cell?.idKey).toBe("customerId");
  });

  it("getCellById returns undefined for unknown id", () => {
    expect(getCellById("unknown")).toBeUndefined();
  });

  it("getFieldLabel uses labelMap when present", () => {
    const cell = getCellById("crm");
    expect(getFieldLabel(cell, "name")).toBe("名称");
    expect(getFieldLabel(cell, "customerId")).toBe("客户ID");
  });

  it("getFieldLabel returns key when not in labelMap", () => {
    const cell = getCellById("crm");
    expect(getFieldLabel(cell, "unknownKey")).toBe("unknownKey");
  });

  it("getFieldLabel handles undefined cell", () => {
    expect(getFieldLabel(undefined, "name")).toBe("name");
  });

  it("batch1 cells have createFields", () => {
    const crm = getCellById("crm");
    const erp = getCellById("erp");
    const oa = getCellById("oa");
    const srm = getCellById("srm");
    expect(crm?.createFields?.length).toBeGreaterThan(0);
    expect(erp?.createFields?.length).toBeGreaterThan(0);
    expect(oa?.createFields?.length).toBeGreaterThan(0);
    expect(srm?.createFields?.length).toBeGreaterThan(0);
  });

  it("CELLS includes all expected batch ids", () => {
    const ids = CELLS.map((c) => c.id);
    expect(ids).toContain("crm");
    expect(ids).toContain("erp");
    expect(ids).toContain("oa");
    expect(ids).toContain("srm");
    expect(ids).toContain("mes");
    expect(ids).toContain("wms");
    expect(ids).toContain("tms");
    expect(ids).toContain("his");
    expect(ids).toContain("lis");
    expect(ids).toContain("lims");
  });
});
