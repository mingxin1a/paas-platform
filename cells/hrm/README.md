# HRM 细胞 - 人力资源管理

**版本**：0.1.0 | **来源**：外部孵化（对标 OrangeHRM，SuperPaaS 架构重写）

## 本地运行

```bash
pip install flask
python src/app.py
# 默认端口 8004
```

或：`docker compose up -d`（在本目录执行）。

## 与平台对接

- 网关路径前缀：`/api/v1/hrm`。平台配置 `CELL_HRM_URL` 指向本细胞。
- 仅通过网关或事件与平台/其他细胞交互。

## API

- GET/POST /employees、/departments、/leave-requests；GET /health。详见 api_contract.yaml。
