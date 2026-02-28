# CRM 细胞 - 生产级安装包说明

## 包内容

- 本细胞目录下所有交付物（src/、api_contract.yaml、cell_profile.md、auto_healing.yaml、ai_agent.py、Dockerfile、docker-compose.yml、docs/、delivery.package、completion.manifest）。
- 发布时可从仓库根执行：`tar -czvf dist/crm-1.2.0.tar.gz -C cells crm`，或由 CI 生成 `crm-{version}.tar.gz`。

## 部署

1. 解压至目标环境。
2. 进入 `crm` 目录，执行 `docker compose up -d` 或按 README 以 Python 运行。
3. 在平台网关配置 `CELL_CRM_URL` 指向本细胞地址。

## 版本

- 与 delivery.package 中 version 一致；当前 1.2.0。
