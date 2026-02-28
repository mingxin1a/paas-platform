# PaaS 核心层性能优化报告

**目标**：路由转发、Token 校验、数据湖查询、治理心跳等性能极致优化，核心转发耗时降低 30% 以上，且 100% 兼容现有 Cell 调用。  
**范围**：platform_core 网关、认证会话、治理存储、事件总线、健康巡检。

---

## 一、优化项总览

| 模块 | 优化项 | 实现方式 | 兼容性 |
|------|--------|----------|--------|
| API 网关 | 连接池复用 | urllib3 PoolManager，按 host 复用 TCP | 100%，仅替换底层 HTTP 客户端 |
| API 网关 | GET 请求缓存 | 短 TTL 内存缓存，key=cell+path+query | 可选开启（GATEWAY_GET_CACHE_TTL_SEC>0） |
| API 网关 | 压缩传输 | 上游 Accept-Encoding: gzip；响应 body 可选 gzip 压缩 | 透明，客户端支持 Accept-Encoding 即可 |
| 认证/Token | 本地缓存 | 网关 Redis 存储外包装 LRU 缓存；auth_center token→user_id 缓存 | 100% |
| 认证/Token | 黑名单 | 无效/注销 token 短时黑名单，避免重复查库与 JWT 校验 | 100% |
| 数据湖/治理 | 分库分表 | Span 按 trace_id hash 分片，分片独立锁 | 100%，接口不变 |
| 数据湖/治理 | 冷热分离 | 每分片内 trace 数量上限，超量淘汰最旧 | 100% |
| 数据湖/事件 | 索引优化 | list_events 按 ts 二分查找 since_ts | 100% |
| 治理 | 心跳连接池 | 健康巡检使用 urllib3 连接池，复用连接 | 100% |
| 治理 | 配置可调 | 巡检间隔/超时/池大小可配，降低资源占用 | 100% |

---

## 二、优化前后对比与压测建议

### 2.1 网关转发耗时（核心指标）

- **优化前**：每次转发新建 TCP 连接（urllib.request），无缓存、无压缩。
- **优化后**：
  - 连接池：同 host 多请求复用连接，**建立连接 RTT 消除**，在高 QPS 下预期**降低 20%～40% 的 P99 延迟**（视网络 RTT 与细胞响应时间而定）。
  - GET 缓存：命中时**无转发、无细胞调用**，延迟接近内存读（&lt;1ms）。
  - 压缩：大 body 时带宽与传输时间下降，**端到端耗时可再降 10%～30%**（视 body 大小与压缩比）。

**建议压测命令（示例）：**

```bash
# 网关转发 P99 对比（需先启动网关 + 至少一个细胞，USE_REAL_FORWARD=1）
# 优化前：关闭连接池（不装 urllib3 或使用旧代码）
ab -n 5000 -c 50 -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -H "X-Request-ID: req-1" http://localhost:8000/api/v1/erp/health

# 优化后：安装 urllib3，同上
# 对比 Total time、Time per request (mean)、Transfer rate、Requests per second
```

**预期结果（示例）：**

| 场景 | 优化前 P99 (ms) | 优化后 P99 (ms) | 降幅 |
|------|-----------------|-----------------|------|
| 同 cell 高并发 50 | 85 | 52 | ~39% |
| GET 缓存命中 | 80 | &lt;2 | &gt;97% |
| 大 body 2KB+ 压缩 | 120 | 88 | ~27% |

（以上为典型环境参考，实际以自测为准。）

### 2.2 Token 校验性能

- **优化前**：每次 /api/auth/me 或需校验的请求均访问 Redis 或内存；auth_center 每次 JWT 解码 + DB 查询。
- **优化后**：
  - 网关：Redis 外包装本地 LRU 缓存 + 黑名单，**命中缓存无 Redis 往返**；黑名单命中直接拒绝，无存储访问。
  - auth_center：token→user_id 缓存 + 黑名单，**命中缓存仅一次 get_by_id(PK)**，无 JWT 解码。

**压测建议：** 对 /api/auth/me 或带 Bearer 的 /api/v1/&lt;cell&gt;/... 做高 QPS 压测，对比优化前后 QPS 与 P99。

### 2.3 数据湖 / 治理存储

- **优化前**：Span 单大 dict + 全局锁；list_events 全表扫描。
- **优化后**：Span 分片 + 分片锁，**并发 add_span/get_trace 锁竞争降低**；list_events 按 ts 二分，**大事件表下查询时间由 O(n) 降为 O(log n)+limit**。

**压测建议：** 并发调用 ingest/add_span 与 get_metrics/get_trace，对比优化前后吞吐与 P99。

### 2.4 治理心跳

- **优化前**：每轮每个 cell 新建 HTTP 连接。
- **优化后**：urllib3 连接池复用，**连接建立次数与端口占用减少**，服务端资源占用降低。

---

## 三、环境变量与配置（最佳实践）

| 变量 | 说明 | 推荐值 |
|------|------|--------|
| GATEWAY_POOL_NUM_POOLS | 网关连接池数量 | 32 |
| GATEWAY_POOL_MAXSIZE | 每 host 最大连接数 | 8 |
| GATEWAY_GET_CACHE_TTL_SEC | GET 缓存 TTL（秒），0=关 | 0（只读接口可设 5～30） |
| GATEWAY_GET_CACHE_MAX | GET 缓存条数上限 | 500 |
| GATEWAY_COMPRESS_MIN_BYTES | 响应 body 超过此字节数才 gzip | 256 |
| GATEWAY_TOKEN_CACHE_MAX | 网关 Token 本地缓存条数 | 2000 |
| GATEWAY_TOKEN_CACHE_TTL_SEC | Token 缓存 TTL | 60 |
| GATEWAY_TOKEN_BLACKLIST_TTL_SEC | Token 黑名单 TTL | 300 |
| AUTH_TOKEN_CACHE_TTL_SEC | 认证中心 token 缓存 TTL | 60 |
| AUTH_BLACKLIST_TTL_SEC | 认证中心黑名单 TTL | 300 |
| GOVERNANCE_SPAN_SHARDS | Span 分片数 | 16 |
| GOVERNANCE_SPAN_HOT_MAX | 每分片最大 trace 数（冷热） | 400 |
| GOVERNANCE_METRICS_WINDOW | 指标滑动窗口条数 | 1000 |
| GOVERNANCE_HEALTH_POOL_MAXSIZE | 健康巡检连接池大小 | 4 |
| GOVERNANCE_HEALTH_INTERVAL_SEC | 巡检间隔（秒） | 30 |
| GOVERNANCE_HEALTH_TIMEOUT_SEC | 单次健康检查超时 | 5 |

---

## 四、兼容性说明

- 所有优化**不改变**对 Cell 的请求/响应格式、路由规则、鉴权语义。
- 网关：仅替换底层 HTTP 客户端（urllib3 池 + 可选缓存 + 压缩），对外 API 与行为不变；未安装 urllib3 时自动回退 urllib。
- 认证：网关与 auth_center 的缓存/黑名单均为进程内或已有存储之上的包装，接口与 401 行为一致。
- 治理/事件：存储接口不变，仅内部结构分片与索引优化；健康巡检仍为 GET /health，仅复用连接。

---

## 五、风险与注意

| 风险 | 缓解 |
|------|------|
| GET 缓存导致读到旧数据 | 仅当 GATEWAY_GET_CACHE_TTL_SEC>0 时启用；对强一致性接口勿开或 TTL 设 0 |
| 黑名单 TTL 内注销 token 仍可访问 | 可调短黑名单 TTL，或提供主动注销接口清除缓存/写黑名单 |
| 连接池占满 | 合理设置 GATEWAY_POOL_MAXSIZE 与超时，监控连接数 |

---

## 六、涉及文件清单

- `platform_core/core/gateway/http_client.py`：连接池、GET 缓存、压缩
- `platform_core/core/gateway/app.py`：代理接入 http_client
- `platform_core/core/gateway/session_store.py`：Token 缓存与黑名单包装
- `platform_core/auth_center/dependencies.py`：Token 缓存与黑名单
- `platform_core/core/governance/store.py`：Span 分片、冷热淘汰
- `platform_core/core/event_bus.py`：list_events 按 ts 二分
- `platform_core/core/governance/health_runner.py`：健康巡检连接池
- `platform_core/requirements.txt`：urllib3 依赖

---

**报告版本**：1.0  
**关联文档**：`deploy/docs/PaaS核心层高可用部署手册.md`、`docs/接口设计说明书.md`
