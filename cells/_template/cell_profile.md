# 细胞档案（模板）

**细胞代码**：复制后改为 erp、mes 等  
**约束文档**：《接口设计说明书_V2.0》、细胞化架构规范

---

## 1. 目录结构

```
api/          # 接口：路由、请求/响应模型、鉴权与中间件
models/       # 数据模型与存储
service/      # 业务逻辑
config/       # 配置（仅环境变量）
tests/        # 测试
docker/       # 部署（Dockerfile）
```

## 2. 接口规范（《接口设计说明书》）

- 请求头：Content-Type、Authorization、X-Request-ID（POST/PUT/PATCH）
- 响应头：Content-Type、X-Response-Time
- 错误体：`{"code","message","details","requestId"}`
- 健康：GET /health → `{"status":"up","cell":"<细胞名>"}`

## 3. 复制模板后

- 修改 delivery.package 中 cell_name、status
- 在 models/、service/、api/ 中填充业务实体与路由
- 更新 completion.manifest、cell_profile.md、docker/Dockerfile 端口与 COPY 路径
