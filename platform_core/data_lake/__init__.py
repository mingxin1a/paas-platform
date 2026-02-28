"""
PaaS 数据湖：多 Cell 数据统一汇聚、资产管理、权限管控、统一报表。
不侵入业务 Cell，仅通过标准化接口（POST 汇聚、配置化拉取）实现数据接入。
"""
from .store import DataLakeStore, get_store
from .app import create_app

__all__ = ["DataLakeStore", "get_store", "create_app"]
