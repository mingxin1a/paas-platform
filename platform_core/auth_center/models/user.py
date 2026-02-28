"""
用户模型 - 《01_核心法律》密码不可明文，仅存哈希
"""
from __future__ import annotations

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)  # 仅存哈希，禁止明文
    tenant_id = Column(String(64), nullable=False, default="default", index=True)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=True)
    allowed_cells = Column(Text, nullable=True)  # JSON 数组字符串，如 ["crm","erp"]
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    role = relationship("Role", back_populates="users")


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True)
    name = Column(String(64), nullable=False, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)  # admin, client 等
    description = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True)
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    resource = Column(String(128), nullable=False, index=True)  # users, roles, cells
    action = Column(String(32), nullable=False)  # create, read, update, delete, list

    role = relationship("Role", back_populates="permissions")
