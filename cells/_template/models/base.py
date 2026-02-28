# 模型基类与通用字段（可选：与 ORM 对接时在此扩展）
from __future__ import annotations

from typing import Any, Dict, Optional


class BaseModel:
    """占位基类：复制模板后可按细胞需求引入 SQLAlchemy/Pydantic 等。"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        raise NotImplementedError("子类实现")

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("子类实现")
