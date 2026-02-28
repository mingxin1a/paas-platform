# SuperPaaS 一键部署（玻璃房验证与自主运维）

在隔离的本地环境中完整部署并激活 SuperPaaS 平台（平台核心 + 细胞），进入自主运行状态。

## 一键启动

### 方式一：统一 docker-compose（全平台：治理中心 + 网关 + 13 细胞 + 监控 + 双端前端）

在项目根目录执行：

```bash
cp deploy/.env.example deploy/.env
# 可选：编辑 deploy/.env 修改端口或细胞 URL
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d
```

或在 deploy 目录下：

```bash
cd deploy
cp .env.example .env
docker compose --env-file .env up -d
```

启动后：治理中心 http://localhost:8005，网关 http://localhost:8000，客户端 http://localhost:5173，管理端 http://localhost:5174。可选组件：Redis 会话与联动 Worker 通过 profile 启用：`docker compose -f deploy/docker-compose.yml --env-file deploy/.env --profile with-redis --profile with-sync-worker up -d`。详见 **docs/生产级部署运维手册.md**。

### 方式二：deploy.sh 一键部署脚本（推荐）

全流程：环境检查 → 依赖就绪 → PaaS 核心（治理/网关/监控）→ 细胞批量 → 双端前端 → 冒烟测试；失败时自动回滚并输出错误原因。

```bash
# 全量部署（默认）
./deploy/deploy.sh
# 或
sh deploy/deploy.sh
```

**增量部署**（仅重启指定模块，不影响其他运行中服务）：

```bash
./deploy/deploy.sh --only=gateway,crm-cell
./deploy/deploy.sh --only=frontend,frontend-admin
./deploy/deploy.sh --only=lims-cell --skip-build
```

**参数说明**：

| 参数 | 说明 |
|------|------|
| `--only=SERVICE1,SERVICE2` | 仅启动指定服务（如 gateway、crm-cell、frontend），逗号分隔 |
| `--skip-build` | 不重新构建镜像，仅启动/重启容器 |
| `--no-smoke` | 跳过冒烟测试 |
| `--no-rollback` | 失败时不自动停止本次启动的服务 |

**部署日志**：每次执行会写入 `deploy/deploy.log`，标注各环节 `[OK]` / `[FAIL]`。配置通过 `deploy/.env` 解耦，后续可扩展 `DEPLOY_MODE=k8s` 支持 K8s 部署。

## 目录说明

| 目录/文件 | 说明 |
|------|------|
| `docker-compose.yml` | 全平台编排：PaaS 核心、13 细胞、双前端；env_file 统一 .env；可选 profile：with-redis、with-sync-worker |
| `.env` / `.env.example` | 环境变量（端口、GOVERNANCE_URL、细胞 URL 等） |
| `env/.env.dev|test|staging|prod` | 四套环境配置，部署时通过 `--env=dev` 等切换，见 env/README.md |
| `gateway_route_spec.yaml` | 网关在 Docker 网络内的路由规范 |
| `deploy.sh` | 一键部署；支持 `--env=dev|test|staging|prod`、`--only=SERVICE`、`--skip-build`、`--no-smoke`、`--no-rollback`；失败自动回滚 |
| `deploy.log` | 每次部署的日志（[OK]/[FAIL]） |
| `scripts/env_check.sh` | 环境检查（docker/k8s、.env、端口） |
| `scripts/deploy_rollback.sh` | 版本回滚（docker [SERVICE] \| k8s [DEPLOYMENT]） |
| `scripts/service_control.sh` | 服务启停（docker \| k8s start\|stop\|restart） |
| `scripts/k8s_apply_all.sh` | K8s 一键部署（可选 --no-redis、--no-ingress、--no-hpa） |
| `run_gateway.py` / `run_governance.py` | 本地启动网关/治理中心（非 Docker） |
| `smoke_test.py` | HTTP 冒烟测试 |

## 服务与端口

| 服务 | 宿主机端口 | 说明 |
|------|------------|------|
| governance | 8005 | 治理中心：注册发现、健康巡检、链路与 RED 指标 API |
| gateway | 8000 | 统一入口，路由至各细胞（可选从治理中心发现并上报） |
| frontend | 5173 | 客户端（Nginx 托管，/api 代理到网关） |
| frontend-admin | 5174 | 管理端（同上） |
| crm-cell ~ lims-cell | 8001~8013（仅内网） | 13 个细胞，见 docker-compose.yml |
| monitor | 9000 | 监控中心 / 黄金指标 |

依赖与端口详见 **docs/依赖与部署清单.md**。

## 配置

复制 `deploy/.env.example` 为 `deploy/.env`，按需修改端口、数据库连接、API 密钥占位符等；详见《接口设计说明书》与 **docs/配置项与扩展点.md**。

## K8s 生产级高可用部署

- **deploy/k8s/**：Namespace、ConfigMap、Secret、Redis(StatefulSet)、PaaS 核心、全部 13 细胞、前端、Ingress、HPA。
- 一键应用：`./deploy/scripts/k8s_apply_all.sh`（可选 `--no-redis`、`--no-ingress`、`--no-hpa`）。
- 详见 **deploy/k8s/README.md** 与 **docs/生产级部署运维手册.md**。

## 备份与恢复（按细胞独立）

- **backup_cells.sh**：按细胞备份（meta + 占位数据），可选上传 S3（BACKUP_S3_BUCKET、BACKUP_S3_PREFIX）。
- **restore_cells.sh**：按 RESTORE_DATE 从 BACKUP_DIR 或 S3 恢复。
- **verify_backup.sh**：校验备份包存在且 meta 可读。
- 详见 **scripts/backup_example.md**。

## 商用验收一键校验

项目根执行：`./run.sh commercial_accept`，将执行自检（含细胞架构合规、全链路健康）+ 批次1 细胞 verify_delivery。

## 依赖

- Docker 与 Docker Compose（或 `docker compose`）
- 宿主机可访问 `localhost:8000`（网关）以运行冒烟测试；若已安装 pytest，将自动执行 E2E。
