# Runbook: 自愈流程与人工介入（待补充项 9）

**依据**: incubator_manifest 4; 待补充项清单 9。

## 1. 问题发现

- platform_core/core/monitor 分析业务与系统指标
- 各细胞 ai_agent.py 监听应用日志，匹配 auto_healing.yaml

## 2. 已知问题

命中 auto_healing.yaml 则按规则修复（重启、重试、降级）。无需写入 human_intervention_queue。

## 3. 新问题

1. 生成《自愈方案》文档，建议路径 glass_house/self_healing/{cell}_{date}.md
2. 内容: 现象、根因、建议修复、trace_id
3. 可自动则提交修复或 PR; 否则写入 human_intervention_queue 待处理表

## 4. 严重问题写入 human_intervention_queue

触发: 核心接口不可用、数据一致性风险、安全事件、需架构决策。  
在 glass_house/human_intervention_queue.md 待处理表追加一行，处理完成后移入已处理表。
