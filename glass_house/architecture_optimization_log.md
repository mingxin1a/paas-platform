# 架构优化记录

**目的**：合并可合并项、解耦可解耦处、删除冗余文档与实现，优化整体架构。

---

## 2026-02 优化摘要

### 1. 文档合并与去重

- **逻辑全景图**：原存在两份——`03_超级_PaaS_平台逻辑全景图.md`（V1.0，Mermaid 五层拓扑）与 `超级PaaS平台逻辑全景图.md`（V1.1，导航地图）。已将 03 中简化拓扑图合并入《超级PaaS平台逻辑全景图》**附录 A**，并**删除** `03_超级_PaaS_平台逻辑全景图.md`，以单一文档为入口。
- **项目上下文**：`docs/文本.txt` 为对话上下文摘要、非正式规范，已**迁移**至 `glass_house/项目上下文摘要.txt`，并更新《超级PaaS平台逻辑全景图》中所有对「文本.txt」的引用。

### 2. 冗余实现删除

- **deploy/crm_cell_server.py**：最小 CRM 演示服务，与 `cells/crm` 真实细胞功能重复；deploy 已使用 `cells/crm` 通过 docker-compose 构建。已**删除** `crm_cell_server.py`。

### 3. 验签单源（解耦与统一）

- **细胞侧验签**：各细胞此前各自实现 `signing_verify.py`，与网关算法一致但存在漂移风险。已新增 **platform_core/core/cell_signing.py** 作为细胞侧验签的**规范实现单源**（`verify_signature`、`write_security_audit`），与 `platform_core/core/gateway/signing.py` 算法一致。
- **文档**：《部署与运维规范》§2 增加「细胞验签实现单源」说明：细胞可复制 `platform_core/core/cell_signing.py` 为 `src/signing_verify.py` 或通过依赖引用，避免实现漂移。细胞仍保持无强制依赖 platform_core（复制即可），架构上解耦。

### 4. 文档索引

- 新增 **docs/README.md**：简要说明文档目录、导航入口（逻辑全景图）、宪法、合规/运维、设计说明书、细胞档案及非正式文档位置，便于新成员与检索。

---

## 后续建议（未在本轮执行）

- **共享 cell 基类/模板**：各细胞 `app.py` / `store` 模式高度一致，可考虑在 platform_core 或独立模板库中提供基类/工厂，细胞仅实现业务差异（与孵化器「细胞=独立项目」平衡后决策）。
- **ai_agent 统一**：细胞 ai_agent 存在完整版与最小版两种风格，可收敛为单一可配置模块。
- **网关与 glass_house 路径解耦**：gateway/signing 写 glass_house 路径依赖项目根与目录结构，可改为通过环境变量配置审计输出路径。

---

**文档状态**：初版，记录本次架构优化内容。
