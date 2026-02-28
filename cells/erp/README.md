# ERP 细胞 - 企业资源计划

**版本**：1.1.0 | **交付标准**：SuperPaaS 数字创业孵化器（细胞 = 独立项目）

## 本地运行

### 方式一：Python 直接运行

```bash
pip install flask
python src/app.py
# 默认端口 8002，可通过环境变量 PORT 覆盖
```

### 方式二：Docker 一键启动

```bash
docker compose up -d
# 验证：http://localhost:8002/health
```

## 与平台对接

- 网关路径前缀：`/api/v1/erp`。平台配置 `CELL_ERP_URL` 指向本细胞。
- 仅通过网关或事件与平台/其他细胞交互。

## 生产级安装包

- 见 `dist/PACKAGE.md`。发布时可生成 `erp-{version}.tar.gz`。

## 文档

- 用户手册：`docs/用户手册.md` | 部署指南：`docs/部署指南.md` | 许可证：`LICENSE`
- 验收：项目根执行 `./run.sh verify erp`
