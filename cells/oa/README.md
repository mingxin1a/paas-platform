# OA 细胞 - 办公自动化（任务）

**版本**：0.1.0 | **交付标准**：SuperPaaS 数字创业孵化器（细胞 = 独立项目）

## 本地运行

```bash
pip install flask
python src/app.py
# 默认端口 8005，可通过环境变量 PORT 覆盖
```

## Docker

```bash
docker compose up -d
# 验证：http://localhost:8005/health
```

## 与平台对接

- 网关路径前缀：`/api/v1/oa`。平台配置 `CELL_OA_URL` 指向本细胞。
- 验签：设置 `CELL_VERIFY_SIGNATURE=1` 与 `CELL_SIGNING_SECRET` 与网关一致。

## 生产级安装包

见 `dist/PACKAGE.md`。验收：项目根执行 `./run.sh verify oa`。
