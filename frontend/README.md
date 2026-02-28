# SuperPaaS 客户端（前端）

**客户端**：业务人员使用各细胞（CRM、ERP、WMS 等）。需登录，按角色仅可访问其 allowedCells；管理员可见全部细胞。  
管理端见 **frontend-admin/**。

## 技术栈

- **React 18** + **TypeScript**
- **Vite 5**（构建与开发服务器）
- **React Router 6**
- **CSS Modules** + 设计变量（主题、间距、圆角）

## UI/UX 要点

- 响应式布局：移动端侧栏收起为抽屉，桌面端固定侧栏
- 明/暗主题切换，跟随系统或手动切换
- 动态水印（01 4.1 占位）：用户名 + 时间
- 数据访问记录入口（透明化审计占位）
- 加载态、空态、错误态统一处理

## 开发

```bash
cd frontend
npm install
npm run dev
```

默认 `http://localhost:5173`，Vite 将 `/api`、`/health` 代理到 `http://localhost:8000`（网关）。请先启动网关与所需细胞。

## 构建与部署

```bash
npm run build
```

产物在 `dist/`。可：

- 由网关或 Nginx 托管静态：将 `dist` 内容挂到根或子路径；
- 或配置 `VITE_GATEWAY_URL` 为网关地址后构建，前端直连该地址。

## 环境变量

| 变量 | 说明 |
|------|------|
| `VITE_GATEWAY_URL` | 生产环境网关 base URL，留空则使用同源（与前端同域部署时适用） |

## 合规

- **动态水印**：见 `src/components/Watermark.tsx`
- **透明化审计**：见 `src/pages/AuditLog.tsx`（占位，待对接审计 API）
- **安全态势可视化**：登录/支付等敏感操作时按《前端感知安全需求说明》后续补充
