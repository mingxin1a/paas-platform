# 细胞通用配置：仅环境变量，不依赖 platform_core
# 复制模板后可将 CELL_ 前缀改为本细胞名（如 ERP_、MES_）以隔离配置
from __future__ import annotations

import os
from typing import Optional


class Settings:
    """统一配置入口，对齐《接口设计说明书》环境要求。"""

    # 服务端口（网关/治理中心健康巡检）
    PORT: int = int(os.environ.get("PORT", "8001"))

    # 数据库（复制模板后建议改为 {CELL}_DATABASE_URL）
    DATABASE_URL: str = os.environ.get("CELL_DATABASE_URL", "sqlite:///./cell.db").strip()

    # 平台认证：通过 HTTP 校验 Token，不依赖 platform_core
    PLATFORM_AUTH_URL: Optional[str] = os.environ.get("PLATFORM_AUTH_URL", "").strip() or None
    AUTH_STRICT: bool = os.environ.get("CELL_AUTH_STRICT", "0") == "1"

    # 多租户默认值
    DEFAULT_TENANT_ID: str = os.environ.get("DEFAULT_TENANT_ID", "default")


settings = Settings()
