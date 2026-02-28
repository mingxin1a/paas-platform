# 细胞独立配置，不依赖 platform_core；仅环境变量与本地文件
from __future__ import annotations

import os
from typing import Optional

# 数据库：默认内存 SQLite，生产可设 DATABASE_URL=sqlite:///./data/crm.db
DATABASE_URL: str = os.environ.get("CRM_DATABASE_URL", "sqlite:///./crm_cell.db").strip()

# 平台认证（可选）：通过 HTTP 校验 Token，不直接依赖 platform_core
PLATFORM_AUTH_URL: Optional[str] = os.environ.get("PLATFORM_AUTH_URL", "").strip() or None
# 未配置时本地开发可接受任意 Bearer（仅用于联调）
AUTH_STRICT: bool = os.environ.get("CRM_AUTH_STRICT", "0") == "1"

# 服务端口（网关/治理中心巡检用）
PORT: int = int(os.environ.get("PORT", "8001"))

# 租户默认值
DEFAULT_TENANT_ID: str = os.environ.get("DEFAULT_TENANT_ID", "default")
