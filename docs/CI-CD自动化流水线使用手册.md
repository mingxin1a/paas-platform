# CI/CD 自动化流水线使用手册

**版本**：1.0  
**适用范围**：GitHub Actions、GitLab CI 全流程自动化；代码质量门禁；多环境分级部署；版本管理与回滚。

---

## 一、流水线总览

### 1.1 全流程阶段

```
代码提交 → 代码规范检查 → 单元测试（含覆盖率） → 代码扫描（SonarQube） → 质量门禁
    → 镜像构建 → 镜像推送 → 交付包生成 → 开发/测试/预发布/生产 分级部署 → 验收测试
```

- **门禁**：SonarQube 质量门禁不通过时，流水线阻断，不进入构建与部署。
- **生产**：生产环境部署需人工审批（GitHub Environments 或 GitLab Manual job）。

### 1.2 已配置文件

| 平台 | 文件 | 说明 |
|------|------|------|
| GitHub | `.github/workflows/ci.yml` | 规范检查、单元测试、覆盖率、SonarCloud、集成测试 |
| GitHub | `.github/workflows/build-and-push.yml` | 版本号生成、镜像构建与推送、交付包 |
| GitHub | `.github/workflows/deploy.yml` | 多环境部署（dev→test→staging→prod），prod 需审批 |
| GitLab | `.gitlab-ci.yml` | 全阶段：lint → test → sonar → build → deploy-dev → test → staging → prod(manual) |
| 通用 | `sonar-project.properties` | SonarQube/SonarCloud 扫描范围与覆盖率路径 |
| 通用 | `scripts/version_and_changelog.sh` | 版本号生成、CHANGELOG 更新、交付版本管理 |

---

## 二、触发规则

### 2.1 GitHub Actions

| 工作流 | 触发条件 |
|--------|----------|
| CI | `push` / `pull_request` 到 `main` 或 `master` |
| Build and Push | `push` 到 `main`/`master`，或 CI 工作流完成后（workflow_run） |
| Deploy | `workflow_run`（Build and Push 成功后）、`push` 到 `main`/`master`（排除仅改 .md/docs）、或 `workflow_dispatch` 手动选择环境 |

### 2.2 GitLab CI

| 阶段 | 触发 |
|------|------|
| lint / test / sonar | Merge Request 或推送到 `main`/`master` |
| build | 推送到 `main`/`master` |
| deploy-dev | build 与 sonar 通过后自动执行 |
| deploy-test | deploy-dev 成功后自动执行 |
| deploy-staging | deploy-test 成功后自动执行 |
| deploy-prod | **手动触发**（when: manual），且需在 deploy-staging 之后 |

---

## 三、代码质量门禁

### 3.1 SonarQube/SonarCloud 集成

- **扫描范围**：`cells`、`platform_core`、`deploy`（排除 `tests`、`__pycache__`、模板目录）。
- **覆盖率**：使用各细胞单元测试生成的 `coverage.xml`，上传后作为质量门禁依据之一。

**GitHub**  
- 在仓库 Settings → Secrets 中配置 `SONAR_TOKEN`（SonarCloud 后台生成）。  
- 未配置时，CI 中 Sonar 步骤使用 `continue-on-error: true` 避免阻塞，建议正式使用前配置以启用门禁。

**GitLab**  
- 在 CI/CD → Variables 中配置：  
  - `SONAR_HOST_URL`：SonarQube 服务地址（如 `https://sonar.example.com`）。  
  - `SONAR_TOKEN`：Sonar 项目 Token（Protected + Masked）。  
- 质量门禁不通过时，`sonar` job 失败，后续 build/deploy 不执行。

### 3.2 门禁建议阈值（在 Sonar 服务端 Quality Gate 中配置）

| 指标 | 建议 | 说明 |
|------|------|------|
| 覆盖率 | ≥ 70% | 单元测试覆盖率，可按分支或项目提高 |
| 新增代码重复率 | < 3% | 阻断重复率过高的提交 |
| 新增 Bug | 0 | 阻断新增 Bug |
| 新增漏洞 | 0 | 阻断新增安全漏洞 |
| 代码规范 | 按规则集 | 如 Blocker/Critical 问题数为 0 |

不满足上述条件时，Sonar 报告 Quality Gate 失败，流水线应配置为失败（GitLab 默认即失败；GitHub 需保证 Sonar 步骤不设 `continue-on-error` 或后续依赖其成功）。

### 3.3 本地与 CI 一致性

- 本地可安装 SonarScanner，使用同一 `sonar-project.properties` 执行扫描。  
- 单元测试与覆盖率命令与 CI 保持一致（见《测试验证体系说明》），便于门禁结果一致。

---

## 四、多环境分级部署

### 4.1 环境与配置

| 环境 | 用途 | 配置来源 | 部署方式 |
|------|------|----------|----------|
| development (dev) | 开发联调 | `deploy/env/.env.dev` | 流水线自动 |
| test | 测试/集成 | `deploy/env/.env.test` | 流水线自动 |
| staging | 预发布 | `deploy/env/.env.staging` | 流水线自动 |
| production (prod) | 生产 | `deploy/env/.env.prod` | **人工审批后执行** |

### 4.2 生产环境人工审批

**GitHub**  
1. 仓库 → Settings → Environments → 新建 `development`、`test`、`staging`、`production`（与 workflow 中 environment 名称一致）。  
2. 在 `production` 中启用 “Required reviewers”，添加审批人；可选 “Wait timer”。  
3. `Deploy` 工作流中 `deploy-prod` job 使用 `environment: production`，部署前会等待审批；dev/test/staging 无审批自动执行。

**GitLab**  
1. `deploy:prod` 已配置 `when: manual`，仅手动点击执行。  
2. 可在 Settings → CI/CD → Protected environments 中将 `production` 设为受保护，仅 Maintainers 可触发。

### 4.3 部署脚本与流水线衔接

- 流水线中的“部署”步骤为占位（echo 或调用脚本占位），实际部署需对接：  
  - 单机：`deploy/deploy.sh`、`deploy/scripts/service_control.sh` 等；  
  - K8s：`deploy/scripts/k8s_apply_all.sh`、`deploy_rollback.sh`。  
- 将 `deploy/env/.env.<env>` 与对应环境变量（如 `DEV_GATEWAY_URL`）在 GitHub Variables/Environments 或 GitLab Variables 中配置，供流水线或部署脚本使用。

---

## 五、版本管理

### 5.1 版本号规则

- **语义化**：`v<major>.<minor>.<patch>`（如 `v1.2.3`）。  
- **CI 自动**：无 tag 时使用 `0.0.0-<short_sha>`（如 `0.0.0-a1b2c3d`）；有 tag 时使用该 tag 作为镜像与交付包版本。

### 5.2 版本与更新日志脚本

```bash
# 仅查看当前/下一版本
./scripts/version_and_changelog.sh show

# 生成下一 patch 版本并写入 deploy/VERSION、更新 CHANGELOG
./scripts/version_and_changelog.sh next-patch

# 生成下一 minor 版本
./scripts/version_and_changelog.sh next-minor

# 打 tag 并推送（需自行执行）
git tag v1.2.3 && git push origin v1.2.3
```

- `deploy/VERSION` 用于部署或流水线读取版本；`CHANGELOG.md` 记录版本与日期，可手写补充变更说明。

### 5.3 交付包

- **GitHub**：Build and Push 工作流生成 `dist/superpaas-<version>.zip`，上传为 Artifact。  
- **GitLab**：`deliverable` job 生成 `dist/superpaas-<version>.zip`，作为 Pipeline Artifact 下载。  
- 交付包可用于离线部署或归档，解压后按《生产级部署运维手册》执行部署。

### 5.4 版本回滚

- **镜像**：使用前一版本 tag 重新部署（如 `kubectl set image deployment/gateway gateway=xxx/gateway:v1.2.2` 或 Docker 使用 `v1.2.2`）。  
- **脚本**：`deploy/scripts/deploy_rollback.sh docker [SERVICE]` 或 `deploy_rollback.sh k8s [DEPLOYMENT_NAME]`，见《生产级部署运维手册》。  
- **GitLab**：可结合 “Rollback” 按钮（若配置了 K8s 部署）或重新运行上一成功 Pipeline 的 deploy job。

---

## 六、故障处理

### 6.1 流水线失败常见原因

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| lint 失败 | Flake8 报错 | 按提示修改代码或调整 `flake8` 配置/忽略项 |
| unit-test 失败 | 用例失败或依赖缺失 | 本地执行 `pytest`，补全依赖（requirements.txt） |
| sonar 失败 | 质量门禁未通过或 SONAR_TOKEN 无效 | 在 Sonar 查看报告，修代码或放宽门禁；检查 Token 与 Sonar 地址 |
| build 失败 | Dockerfile 或构建上下文错误 | 本地 `docker build` 复现，修正 Dockerfile 或路径 |
| deploy 失败 | 环境变量/权限/脚本错误 | 查看 job 日志，核对 Environment 与 Variables，本地执行部署脚本验证 |

### 6.2 Sonar 门禁不通过

1. 在 Sonar 项目首页查看 “Quality Gate” 与 “Issues”。  
2. 按 “Blocker/Critical” 优先修复；补充测试提高覆盖率；减少重复代码。  
3. 若确需临时放宽，在 Sonar 服务端调整 Quality Gate 规则，不建议长期关闭门禁。

### 6.3 生产部署审批与回滚

- 审批人应在部署前确认变更说明与回滚方案。  
- 部署后若异常，立即执行回滚（见 5.4），再排查原因并修复后重新走流水线。

### 6.4 获取帮助

- 流水线配置与阶段定义：见 `.github/workflows/*.yml`、`.gitlab-ci.yml` 内注释。  
- 部署与回滚步骤：见《生产级部署运维手册》。  
- 测试与覆盖率：见《测试验证体系说明》。

---

## 七、快速检查清单

- [ ] 仓库已配置 `SONAR_TOKEN`（GitHub）或 `SONAR_HOST_URL` + `SONAR_TOKEN`（GitLab）。  
- [ ] 生产环境已配置 Required reviewers（GitHub）或 Protected + Manual（GitLab）。  
- [ ] 各环境变量（如 `DEV_GATEWAY_URL`、`.env.prod` 对应项）已在对应 Environment/Variables 中配置。  
- [ ] 镜像仓库登录与权限正常（GitHub Packages 或 GitLab Registry）。  
- [ ] 版本与 CHANGELOG 按需使用 `scripts/version_and_changelog.sh` 维护，重要发布打 tag。

---

**文档归属**：SuperPaaS CI/CD  
**关联**：《测试验证体系说明》《生产级部署运维手册》
