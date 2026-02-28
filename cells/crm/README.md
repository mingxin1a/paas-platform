# CRM 细胞 - 客户关系管理

**版本**：1.2.0 | **交付标准**：SuperPaaS 数字创业孵化器（细胞 = 独立项目）

## 本地运行

### 方式一：Python 直接运行

```bash
# 在 cells/crm 目录
pip install flask
python src/app.py
# 服务监听 http://0.0.0.0:8001 ，环境变量 PORT 可覆盖端口
```

### 方式二：Docker 一键启动

```bash
# 在 cells/crm 目录
docker compose up -d
# 访问 http://localhost:8001/health 验证
```

## 与平台对接

- 本细胞通过 **PaaS 网关** 对外暴露，网关路径前缀：`/api/v1/crm`。
- 平台侧配置 `CELL_CRM_URL=http://<本细胞地址>:8001`，网关将请求转发至本细胞。
- 不依赖其他细胞；仅通过网关或事件与平台/其他细胞交互。

## 生产级安装包（dist/）

- 发布时可在项目根执行打包脚本，将本细胞 + Dockerfile 打成 `dist/crm-{version}.tar.gz`，便于离线部署。
- 详见 `dist/PACKAGE.md`。

## 文档与合规

- 用户手册：`docs/用户手册.md`
- 部署指南：`docs/部署指南.md`
- 许可证：`LICENSE`
- 产品规格：`crm_自主产品规格说明书.md`
- 验收：在项目根执行 `./run.sh verify crm` 或 `./scripts/verify_delivery.sh crm`
