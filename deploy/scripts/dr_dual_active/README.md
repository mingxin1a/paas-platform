# 异地容灾与双活部署

**原则**：平台层中立治理；容灾与双活通过部署拓扑与备份同步、故障切换脚本实现。

---

## 一、同城双活（基础）

- **网关/治理/监控**：多副本部署（K8s Deployment replicas ≥ 2），跨可用区反亲和；入口 SLB/Ingress 负载均衡。
- **细胞**：每个细胞独立 Deployment，多副本；数据库主从或集群，同城多 AZ。
- **路由**：治理中心配置细胞 upstream 为 K8s Service（多 Pod），无状态水平扩展。

---

## 二、异地容灾

- **数据同步**：主站通过 `backup_runner.sh` 全量/增量备份并上传 S3/OSS；灾备站通过 `sync_backup_to_dr.sh`（DR_PULL_ONLY=1）或 `prepare_dr_site.sh` 拉取最新备份，实现准实时同步。
- **恢复与切换**：灾备站执行 `restore_full.sh` 恢复数据后启动服务，执行 `dr_failover.sh` 并切换 DNS/SLB 至灾备站。
- **部署配置**：见 `deploy_standby.yaml.example`；环境变量见 `env.example`。

---

## 三、脚本清单

| 脚本 | 说明 |
|------|------|
| `prepare_dr_site.sh` | 灾备站准备：目录、从 S3 拉取备份 |
| `sync_backup_to_dr.sh` | 主站上传/灾备站拉取（DR_PULL_ONLY=1） |
| `dr_failover.sh` | 故障切换：写标记、提示 DNS/SLB 切换 |
| `deploy_standby.yaml.example` | 灾备 K8s 部署示例 |
| `env.example` | DR_SITE_ID、S3 等变量 |

---

## 四、详细步骤

见《数据备份与灾备手册》第五章灾备方案、故障切换与回切。

**文档归属**：deploy/scripts/dr_dual_active
