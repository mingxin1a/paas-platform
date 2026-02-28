# delivery.package 规范

自主进化引擎通过扫描各细胞目录下的 `delivery.package` 识别待完善细胞。

## 文件位置

`cells/{CELL_NAME}/delivery.package`

## 格式（YAML）

```yaml
cell_name: string          # 与目录名一致，如 crm
status: string             # building | ready_for_qa | production_ready
version: string            # 语义化版本，如 "1.0.0"
last_gap_at: string|null   # 上次发现 gap 的日期 ISO8601，无则为 null
last_evolution_at: string|null  # 上次进化完成日期
completion_manifest: string # 清单文件名，通常 completion.manifest
```

## 状态含义

- **building**：开发中，需对标与进化
- **ready_for_qa**：待验证，需运行 `./run.sh verify <cell>` 或 `./scripts/verify_delivery.sh <cell>` 通过后可置为 production_ready
- **production_ready**：已通过验证，可向 PaaS 注册中心宣告

## completion.manifest

同目录下 YAML 文件，列出已交付能力（id、description、contract 等），由进化引擎与 verify_delivery 共同使用。
