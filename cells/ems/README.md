# EMS 细胞 - 能源管理

**版本**：0.1.0 | **交付标准**：SuperPaaS 数字创业孵化器

## 本地运行

```bash
pip install flask
python src/app.py
# 默认端口 8010
```

## Docker

```bash
docker compose up -d
# 验证：http://localhost:8010/health
```

## 与平台对接

- 网关路径前缀：`/api/v1/ems`。平台配置 `CELL_EMS_URL` 指向本细胞。
- 验签：`CELL_VERIFY_SIGNATURE=1` 与 `CELL_SIGNING_SECRET`。

## 验收

项目根执行 `./run.sh verify ems`。生产包见 `dist/PACKAGE.md`。
