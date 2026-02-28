/**
 * 细胞配置：与平台 cells 及 api_contract 对应，供客户端列表/详情/概览使用。
 * 依据：docs/细胞档案/*
 */
export interface CreateFieldConfig {
  name: string;
  label: string;
  type?: "text" | "number" | "email" | "textarea";
  required?: boolean;
  placeholder?: string;
}

export interface CellConfig {
  id: string;
  name: string;
  description?: string;
  path: string;
  listKey?: string;
  idKey?: string;
  /** 列表/详情表头与字段中文标签，未列出的键保持原样 */
  labelMap?: Record<string, string>;
  /** 批次1 导出：标准化 CSV 导出路径，如 /export/customers */
  exportPath?: string;
  /** 新建表单字段（有则显示「新建」按钮并支持创建流程闭环） */
  createFields?: CreateFieldConfig[];
}

export const CELLS: CellConfig[] = [
  {
    id: "crm",
    name: "客户关系",
    description: "客户、商机、线索、联系人、360° 视图与销售预测",
    path: "/customers",
    listKey: "data",
    idKey: "customerId",
    exportPath: "/export/customers",
    createFields: [
      { name: "name", label: "客户名称", required: true, placeholder: "必填" },
      { name: "contactPhone", label: "联系电话", type: "text", placeholder: "选填" },
      { name: "contactEmail", label: "邮箱", type: "email", placeholder: "选填" },
    ],
    labelMap: {
      customerId: "客户ID", tenantId: "租户", name: "名称", contactPhone: "电话", contactEmail: "邮箱",
      status: "状态", createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
  {
    id: "erp",
    name: "企业资源",
    description: "订单、总账、应收应付、物料、采购、生产",
    path: "/orders",
    listKey: "data",
    idKey: "orderId",
    exportPath: "/export/orders",
    createFields: [
      { name: "customerId", label: "客户ID", required: true },
      { name: "totalAmountCents", label: "金额(分)", type: "number", required: true },
      { name: "currency", label: "币种", placeholder: "默认 CNY" },
    ],
    labelMap: {
      orderId: "订单ID", customerId: "客户", totalAmountCents: "金额(分)", currency: "币种",
      status: "状态", createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
  {
    id: "wms",
    name: "仓储管理",
    description: "入库单、出库单、库存、库位、批次",
    path: "/inbound-orders",
    listKey: "data",
    idKey: "orderId",
    labelMap: {
      orderId: "入库单ID", tenantId: "租户", warehouseId: "仓库", status: "状态",
      createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
  {
    id: "hrm",
    name: "人力资源",
    description: "员工、部门、请假申请",
    path: "/employees",
    listKey: "data",
    idKey: "employeeId",
    labelMap: {
      employeeId: "员工ID", name: "姓名", departmentId: "部门", email: "邮箱", phone: "电话",
      status: "状态", createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
  {
    id: "oa",
    name: "协同办公",
    description: "任务、待办、审批流",
    path: "/tasks",
    listKey: "data",
    idKey: "taskId",
    createFields: [
      { name: "title", label: "任务标题", required: true },
      { name: "assigneeId", label: "负责人ID", type: "text" },
      { name: "priority", label: "优先级", placeholder: "high/medium/low" },
      { name: "dueAt", label: "截止时间", type: "text", placeholder: "ISO8601" },
    ],
    labelMap: {
      taskId: "任务ID", title: "标题", assigneeId: "负责人", status: "状态", priority: "优先级",
      dueAt: "截止时间", createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
  {
    id: "mes",
    name: "制造执行",
    description: "工单、生产订单、报工",
    path: "/work-orders",
    listKey: "data",
    idKey: "workOrderId",
    labelMap: {
      workOrderId: "工单ID", productId: "产品", quantity: "数量", status: "状态",
      plannedStartAt: "计划开始", plannedEndAt: "计划结束", createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
  {
    id: "tms",
    name: "运输管理",
    description: "运单、承运、在途跟踪",
    path: "/shipments",
    listKey: "data",
    idKey: "shipmentId",
    labelMap: {
      shipmentId: "运单ID", orderId: "订单", carrier: "承运商", status: "状态",
      fromAddress: "发货地", toAddress: "收货地", createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
  {
    id: "srm",
    name: "供应商",
    description: "供应商主数据、采购订单",
    path: "/suppliers",
    listKey: "data",
    idKey: "supplierId",
    exportPath: "/export/purchase-orders",
    createFields: [
      { name: "name", label: "供应商名称", required: true },
      { name: "code", label: "编码", type: "text" },
      { name: "contactPhone", label: "联系电话", type: "text" },
      { name: "contactEmail", label: "邮箱", type: "email" },
    ],
    labelMap: {
      supplierId: "供应商ID", name: "名称", code: "编码", contactPhone: "电话", contactEmail: "邮箱",
      status: "状态", createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
  {
    id: "plm",
    name: "产品生命周期",
    description: "产品、BOM、版本管理",
    path: "/products",
    listKey: "data",
    idKey: "productId",
    labelMap: {
      productId: "产品ID", productCode: "编码", name: "名称", version: "版本", status: "状态",
      createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
  {
    id: "ems",
    name: "能源管理",
    description: "能耗记录、计量点、能效分析",
    path: "/consumption-records",
    listKey: "data",
    idKey: "recordId",
    labelMap: {
      recordId: "记录ID", meterId: "计量点", value: "数值", unit: "单位", recordTime: "记录时间",
      tenantId: "租户", createdAt: "创建时间",
    },
  },
  {
    id: "his",
    name: "医院信息",
    description: "患者、就诊、医嘱",
    path: "/patients",
    listKey: "data",
    idKey: "patientId",
    labelMap: {
      patientId: "患者ID", name: "姓名", idNumber: "证件号", phone: "电话", status: "状态",
      createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
  {
    id: "lis",
    name: "检验信息",
    description: "样本、检验结果、报告",
    path: "/samples",
    listKey: "data",
    idKey: "sampleId",
    labelMap: {
      sampleId: "样本ID", patientId: "患者", type: "类型", status: "状态", collectedAt: "采集时间",
      createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
  {
    id: "lims",
    name: "实验室",
    description: "样本、检测结果、质控",
    path: "/samples",
    listKey: "data",
    idKey: "sampleId",
    labelMap: {
      sampleId: "样本ID", specimenType: "标本类型", status: "状态", receivedAt: "接收时间",
      createdAt: "创建时间", updatedAt: "更新时间",
    },
  },
];

export function getCellById(id: string): CellConfig | undefined {
  return CELLS.find((c) => c.id === id);
}

/** 表头或详情键的显示名：优先 labelMap，否则返回键名 */
export function getFieldLabel(cell: CellConfig | undefined, key: string): string {
  return cell?.labelMap?.[key] ?? key;
}
