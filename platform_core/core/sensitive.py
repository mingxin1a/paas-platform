"""
全平台敏感字段处理：传输 HTTPS（部署层）+ 存储 AES + 展示脱敏。
依据：《01_核心法律》2.2、docs/敏感数据加密与脱敏规范.md。细胞可选用本模块。
"""
from __future__ import annotations

import os
import re
import base64
from typing import Any, Optional


def mask_phone(value: Optional[str]) -> str:
    """手机号脱敏：13812345678 -> 138****5678。"""
    if not value or not isinstance(value, str):
        return ""
    s = re.sub(r"\D", "", value)
    if len(s) < 7:
        return "***"
    return s[:3] + "****" + s[-4:]


def mask_id_no(value: Optional[str]) -> str:
    """身份证号脱敏：保留前3后4。"""
    if not value or not isinstance(value, str):
        return ""
    s = re.sub(r"\D", "", value)
    if len(s) < 8:
        return "********"
    return s[:3] + "*" * (len(s) - 7) + s[-4:]


def mask_email(value: Optional[str]) -> str:
    """邮箱脱敏：a***@example.com。"""
    if not value or not isinstance(value, str) or "@" not in value:
        return ""
    local, _, domain = value.partition("@")
    if len(local) <= 2:
        return "***@" + domain
    return local[0] + "***@" + domain


def mask_contract_no(value: Optional[str]) -> str:
    """合同号脱敏：保留前2后2。"""
    if not value or not isinstance(value, str):
        return ""
    if len(value) <= 4:
        return "****"
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def mask_amount_cents(value: Optional[int], mask: bool = False) -> Any:
    """金额（分）：mask=True 时返回脱敏占位。"""
    if mask:
        return "***"
    return value if value is not None else 0


def _get_aes_key() -> Optional[bytes]:
    """AES 密钥由环境变量 SENSITIVE_AES_KEY 或 KMS 注入。"""
    raw = os.environ.get("SENSITIVE_AES_KEY") or os.environ.get("KMS_DATA_KEY")
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("base64:"):
        try:
            return base64.b64decode(raw[7:].strip())
        except Exception:
            return raw.encode("utf-8")[:32].ljust(32, b"\0")


def encrypt_at_rest(plaintext: str) -> Optional[str]:
    """存储前 AES 加密；未配置密钥返回 None。返回 base64(iv+ciphertext)。"""
    key = _get_aes_key()
    if not key or len(key) < 16:
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import secrets
        iv = secrets.token_bytes(12)
        aes = AESGCM(key[:32].ljust(32, b"\0") if len(key) < 32 else key[:32])
        ct = aes.encrypt(iv, plaintext.encode("utf-8"), None)
        return base64.b64encode(iv + ct).decode("ascii")
    except ImportError:
        return None
    except Exception:
        return None


def decrypt_at_rest(ciphertext_b64: str) -> Optional[str]:
    """存储后解密；未配置或异常返回 None。"""
    key = _get_aes_key()
    if not key or not ciphertext_b64:
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        raw = base64.b64decode(ciphertext_b64, validate=True)
        if len(raw) < 12 + 16:
            return None
        iv, ct = raw[:12], raw[12:]
        aes = AESGCM(key[:32].ljust(32, b"\0") if len(key) < 32 else key[:32])
        return aes.decrypt(iv, ct, None).decode("utf-8")
    except Exception:
        return None
