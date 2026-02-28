# 示例业务服务：复制模板后替换为订单服务、工单服务等
from __future__ import annotations

from typing import Any, Dict, List, Optional

from models import item as item_model


class ItemService:
    """示例 CRUD 服务，对接 models 层。"""

    @staticmethod
    def list(tenant_id: str, page: int = 1, page_size: int = 20) -> tuple[List[Dict], int]:
        return item_model.list_items(tenant_id, page, page_size)

    @staticmethod
    def get(tenant_id: str, item_id: str) -> Optional[Dict[str, Any]]:
        return item_model.get_item(tenant_id, item_id)

    @staticmethod
    def create(tenant_id: str, name: str, request_id: str, **extra) -> tuple[Dict[str, Any], bool]:
        """返回 (实体, 是否新建)。若已存在同 request_id 则返回 (已有实体, False)。"""
        existing_id = item_model.idempotent_get(request_id)
        if existing_id:
            obj = item_model.get_item(tenant_id, existing_id)
            if obj:
                return obj, False
        obj = item_model.create_item(tenant_id, name, extra)
        item_model.idempotent_set(request_id, obj["itemId"])
        return obj, True

    @staticmethod
    def update(tenant_id: str, item_id: str, name: Optional[str] = None, **kwargs) -> Optional[Dict]:
        return item_model.update_item(tenant_id, item_id, name, **kwargs)

    @staticmethod
    def delete(tenant_id: str, item_id: str) -> bool:
        return item_model.delete_item(tenant_id, item_id)
