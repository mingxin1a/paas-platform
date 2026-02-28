# Runbook: 每周业界对标扫描（待补充项 8）

**依据**: incubator_manifest 3; 待补充项清单 8。

## 目标

每周对每个细胞执行业界对标扫描，识别可新增能力并安全注入，更新 delivery.package / 用户手册。

## 执行

```bash
bash scripts/weekly_benchmark_scan.sh
```

Cron 每周一 9:00: `0 9 * * 1 cd /path/to/pass-platform && bash scripts/weekly_benchmark_scan.sh`

## 产出

- glass_house/gap_analysis/*.md 更新
- glass_house/weekly_benchmark.log 追加
