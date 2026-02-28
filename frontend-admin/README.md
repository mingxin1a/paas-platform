# SuperPaaS 管理端

平台管理端：登录、细胞管理（启用/停用）、用户与权限查看、审计日志占位。

## 开发

```bash
npm install
npm run dev
```

访问 http://localhost:5174 ，演示账号 **admin / admin**。

## 构建

```bash
npm run build
```

产物在 `dist/`。部署时可单独托管或与网关同域（网关根路径可指向客户端，管理端可放在子路径如 /admin）。

## 说明

- 登录调用网关 `POST /api/auth/login`。
- 细胞列表与启用/停用调用 `GET /api/admin/cells`、`PATCH /api/admin/cells/:id`。
- 用户与权限、审计为占位，对接用户中心与审计 API 后替换。
