"""
PaaS 核心层多租户能力：租户生命周期、配额、配置、角色权限。
严格数据隔离：所有存储按 tenant_id 隔离，平台不持有业务数据，仅租户元数据与配置。
"""
from .store import TenantStore, get_tenant_store
from .quota import TenantQuota, get_tenant_quota
from .config_store import TenantConfigStore, get_tenant_config_store
from .roles import TenantRoleStore, get_tenant_role_store

__all__ = [
    "TenantStore",
    "get_tenant_store",
    "TenantQuota",
    "get_tenant_quota",
    "TenantConfigStore",
    "get_tenant_config_store",
    "TenantRoleStore",
    "get_tenant_role_store",
]
