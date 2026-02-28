# 细胞独立数据库层，不依赖 platform_core；SQLite + 内存可选
from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import DATABASE_URL

# 内存模式：无文件
_conn_local = threading.local()
_db_path: Optional[str] = None


def _get_path() -> str:
    global _db_path
    if _db_path is not None:
        return _db_path
    url = DATABASE_URL
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "", 1)
        if path.strip() in ("", ":memory:"):
            _db_path = ":memory:"
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            _db_path = path
    else:
        _db_path = ":memory:"
    return _db_path


def get_conn() -> sqlite3.Connection:
    if not hasattr(_conn_local, "conn") or _conn_local.conn is None:
        _conn_local.conn = sqlite3.connect(_get_path(), check_same_thread=False)
        _conn_local.conn.row_factory = sqlite3.Row
        _init_schema(_conn_local.conn)
    return _conn_local.conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        name TEXT NOT NULL,
        contact_phone TEXT,
        contact_email TEXT,
        status INTEGER DEFAULT 1,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS contacts (
        contact_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        is_primary INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS opportunities (
        opportunity_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        title TEXT NOT NULL,
        amount_cents INTEGER DEFAULT 0,
        currency TEXT DEFAULT 'CNY',
        stage INTEGER DEFAULT 1,
        status INTEGER DEFAULT 1,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS follow_ups (
        follow_up_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        customer_id TEXT,
        opportunity_id TEXT,
        contact_id TEXT,
        content TEXT NOT NULL,
        follow_up_type TEXT DEFAULT 'call',
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS idempotent (
        request_id TEXT PRIMARY KEY,
        resource_type TEXT NOT NULL,
        resource_id TEXT NOT NULL,
        created_at TEXT
    );
    -- 商用化：合同、回款、客户负责人（数据权限）
    CREATE TABLE IF NOT EXISTS contracts (
        contract_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        opportunity_id TEXT,
        contract_no TEXT NOT NULL,
        amount_cents INTEGER NOT NULL DEFAULT 0,
        currency TEXT DEFAULT 'CNY',
        status INTEGER DEFAULT 1,
        signed_at TEXT,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS payment_records (
        payment_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        contract_id TEXT NOT NULL,
        amount_cents INTEGER NOT NULL,
        payment_at TEXT NOT NULL,
        remark TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS customer_owner (
        customer_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        owner_id TEXT NOT NULL,
        created_at TEXT,
        PRIMARY KEY (customer_id, tenant_id)
    );
    CREATE INDEX IF NOT EXISTS idx_contracts_tenant ON contracts(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_contracts_customer ON contracts(customer_id);
    CREATE INDEX IF NOT EXISTS idx_payment_records_contract ON payment_records(contract_id);
    CREATE INDEX IF NOT EXISTS idx_customer_owner_owner ON customer_owner(tenant_id, owner_id);
    CREATE INDEX IF NOT EXISTS idx_customers_tenant ON customers(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_contacts_tenant ON contacts(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_contacts_customer ON contacts(customer_id);
    CREATE INDEX IF NOT EXISTS idx_opportunities_tenant ON opportunities(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_opportunities_customer ON opportunities(customer_id);
    CREATE INDEX IF NOT EXISTS idx_opportunities_stage_status ON opportunities(tenant_id, stage, status);
    CREATE INDEX IF NOT EXISTS idx_follow_ups_tenant ON follow_ups(tenant_id);
    CREATE TABLE IF NOT EXISTS audit_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        operation_type TEXT NOT NULL,
        resource_type TEXT,
        resource_id TEXT,
        trace_id TEXT,
        occurred_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_audit_tenant_time ON audit_log(tenant_id, occurred_at);
    CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_log(trace_id);
    """)


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())


def _id() -> str:
    return str(uuid.uuid4()).replace("-", "")[:16]


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row) if row else {}


# ---------- Idempotent ----------
def idempotent_get(request_id: str) -> Optional[tuple]:
    conn = get_conn()
    r = conn.execute(
        "SELECT resource_type, resource_id FROM idempotent WHERE request_id = ?", (request_id,)
    ).fetchone()
    return (r[0], r[1]) if r else None


def idempotent_set(request_id: str, resource_type: str, resource_id: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO idempotent (request_id, resource_type, resource_id, created_at) VALUES (?,?,?,?)",
        (request_id, resource_type, resource_id, _ts()),
    )
    conn.commit()


# ---------- Customers ----------
def customer_list(
    tenant_id: str,
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
) -> tuple[List[Dict], int]:
    conn = get_conn()
    if keyword and keyword.strip():
        k = f"%{keyword.strip()}%"
        total = conn.execute(
            """SELECT COUNT(*) FROM customers WHERE tenant_id = ? AND (name LIKE ? OR contact_phone LIKE ? OR contact_email LIKE ?)""",
            (tenant_id, k, k, k),
        ).fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            """SELECT customer_id, tenant_id, name, contact_phone, contact_email, status, created_at, updated_at
               FROM customers WHERE tenant_id = ? AND (name LIKE ? OR contact_phone LIKE ? OR contact_email LIKE ?)
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, k, k, k, page_size, offset),
        ).fetchall()
    else:
        total = conn.execute(
            "SELECT COUNT(*) FROM customers WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            """SELECT customer_id, tenant_id, name, contact_phone, contact_email, status, created_at, updated_at
               FROM customers WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, page_size, offset),
        ).fetchall()
    data = [
        {
            "customerId": r["customer_id"],
            "tenantId": r["tenant_id"],
            "name": r["name"],
            "contactPhone": r["contact_phone"] or "",
            "contactEmail": r["contact_email"] or "",
            "status": r["status"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"],
        }
        for r in rows
    ]
    return data, total


def customer_list_by_owner_keyword(
    tenant_id: str, owner_id: str, keyword: Optional[str] = None, page: int = 1, page_size: int = 20
) -> tuple[List[Dict], int]:
    """数据权限：仅返回 owner 负责的客户；支持关键字筛选。"""
    conn = get_conn()
    if keyword and keyword.strip():
        k = f"%{keyword.strip()}%"
        total = conn.execute(
            """SELECT COUNT(*) FROM customers c INNER JOIN customer_owner o ON c.customer_id = o.customer_id AND c.tenant_id = o.tenant_id
               WHERE c.tenant_id = ? AND o.owner_id = ? AND (c.name LIKE ? OR c.contact_phone LIKE ? OR c.contact_email LIKE ?)""",
            (tenant_id, owner_id, k, k, k),
        ).fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            """SELECT c.customer_id, c.tenant_id, c.name, c.contact_phone, c.contact_email, c.status, c.created_at, c.updated_at
               FROM customers c INNER JOIN customer_owner o ON c.customer_id = o.customer_id AND c.tenant_id = o.tenant_id
               WHERE c.tenant_id = ? AND o.owner_id = ? AND (c.name LIKE ? OR c.contact_phone LIKE ? OR c.contact_email LIKE ?)
               ORDER BY c.created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, owner_id, k, k, k, page_size, offset),
        ).fetchall()
    else:
        total = conn.execute(
            "SELECT COUNT(*) FROM customers c INNER JOIN customer_owner o ON c.customer_id = o.customer_id AND c.tenant_id = o.tenant_id WHERE c.tenant_id = ? AND o.owner_id = ?",
            (tenant_id, owner_id),
        ).fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            """SELECT c.customer_id, c.tenant_id, c.name, c.contact_phone, c.contact_email, c.status, c.created_at, c.updated_at
               FROM customers c INNER JOIN customer_owner o ON c.customer_id = o.customer_id AND c.tenant_id = o.tenant_id
               WHERE c.tenant_id = ? AND o.owner_id = ? ORDER BY c.created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, owner_id, page_size, offset),
        ).fetchall()
    data = [
        {
            "customerId": r["customer_id"],
            "tenantId": r["tenant_id"],
            "name": r["name"],
            "contactPhone": r["contact_phone"] or "",
            "contactEmail": r["contact_email"] or "",
            "status": r["status"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"],
        }
        for r in rows
    ]
    return data, total


def customer_get(tenant_id: str, customer_id: str) -> Optional[Dict]:
    conn = get_conn()
    r = conn.execute(
        "SELECT customer_id, tenant_id, name, contact_phone, contact_email, status, created_at, updated_at FROM customers WHERE customer_id = ? AND tenant_id = ?",
        (customer_id, tenant_id),
    ).fetchone()
    if not r:
        return None
    return {
        "customerId": r["customer_id"],
        "tenantId": r["tenant_id"],
        "name": r["name"],
        "contactPhone": r["contact_phone"] or "",
        "contactEmail": r["contact_email"] or "",
        "status": r["status"],
        "createdAt": r["created_at"],
        "updatedAt": r["updated_at"],
    }


def customer_get_by_name(tenant_id: str, name: str) -> Optional[Dict]:
    conn = get_conn()
    r = conn.execute(
        "SELECT customer_id, tenant_id, name, contact_phone, contact_email, status, created_at, updated_at FROM customers WHERE tenant_id = ? AND name = ?",
        (tenant_id, name.strip()),
    ).fetchone()
    if not r:
        return None
    return {
        "customerId": r["customer_id"],
        "tenantId": r["tenant_id"],
        "name": r["name"],
        "contactPhone": r["contact_phone"] or "",
        "contactEmail": r["contact_email"] or "",
        "status": r["status"],
        "createdAt": r["created_at"],
        "updatedAt": r["updated_at"],
    }


def customer_create(
    tenant_id: str,
    name: str,
    contact_phone: Optional[str] = None,
    contact_email: Optional[str] = None,
    owner_id: Optional[str] = None,
) -> Dict:
    cid = _id()
    now = _ts()
    conn = get_conn()
    conn.execute(
        """INSERT INTO customers (customer_id, tenant_id, name, contact_phone, contact_email, status, created_at, updated_at)
           VALUES (?,?,?,?,?,1,?,?)""",
        (cid, tenant_id, name, contact_phone or "", contact_email or "", now, now),
    )
    if owner_id:
        conn.execute(
            "INSERT OR REPLACE INTO customer_owner (customer_id, tenant_id, owner_id, created_at) VALUES (?,?,?,?)",
            (cid, tenant_id, owner_id, now),
        )
    conn.commit()
    return customer_get(tenant_id, cid) or {}


def customer_update(
    tenant_id: str,
    customer_id: str,
    name: Optional[str] = None,
    contact_phone: Optional[str] = None,
    contact_email: Optional[str] = None,
) -> Optional[Dict]:
    c = customer_get(tenant_id, customer_id)
    if not c:
        return None
    now = _ts()
    conn = get_conn()
    conn.execute(
        """UPDATE customers SET name = COALESCE(?, name), contact_phone = COALESCE(?, contact_phone),
           contact_email = COALESCE(?, contact_email), updated_at = ? WHERE customer_id = ? AND tenant_id = ?""",
        (name, contact_phone, contact_email, now, customer_id, tenant_id),
    )
    conn.commit()
    return customer_get(tenant_id, customer_id)


def customer_delete(tenant_id: str, customer_id: str) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM customers WHERE customer_id = ? AND tenant_id = ?", (customer_id, tenant_id))
    conn.commit()
    return cur.rowcount > 0


# ---------- Contacts ----------
def contact_list(
    tenant_id: str,
    customer_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[List[Dict], int]:
    conn = get_conn()
    if customer_id:
        total = conn.execute(
            "SELECT COUNT(*) FROM contacts WHERE tenant_id = ? AND customer_id = ?", (tenant_id, customer_id)
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT contact_id, tenant_id, customer_id, name, phone, email, is_primary, created_at, updated_at
               FROM contacts WHERE tenant_id = ? AND customer_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, customer_id, page_size, (page - 1) * page_size),
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM contacts WHERE tenant_id = ?", (tenant_id,)).fetchone()[0]
        rows = conn.execute(
            """SELECT contact_id, tenant_id, customer_id, name, phone, email, is_primary, created_at, updated_at
               FROM contacts WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, page_size, (page - 1) * page_size),
        ).fetchall()
    data = [
        {
            "contactId": r["contact_id"],
            "tenantId": r["tenant_id"],
            "customerId": r["customer_id"],
            "name": r["name"],
            "phone": r["phone"] or "",
            "email": r["email"] or "",
            "isPrimary": bool(r["is_primary"]),
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"],
        }
        for r in rows
    ]
    return data, total


def contact_get(tenant_id: str, contact_id: str) -> Optional[Dict]:
    conn = get_conn()
    r = conn.execute(
        "SELECT contact_id, tenant_id, customer_id, name, phone, email, is_primary, created_at, updated_at FROM contacts WHERE contact_id = ? AND tenant_id = ?",
        (contact_id, tenant_id),
    ).fetchone()
    if not r:
        return None
    return {
        "contactId": r["contact_id"],
        "tenantId": r["tenant_id"],
        "customerId": r["customer_id"],
        "name": r["name"],
        "phone": r["phone"] or "",
        "email": r["email"] or "",
        "isPrimary": bool(r["is_primary"]),
        "createdAt": r["created_at"],
        "updatedAt": r["updated_at"],
    }


def contact_create(
    tenant_id: str,
    customer_id: str,
    name: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    is_primary: bool = False,
) -> Dict:
    cid = _id()
    now = _ts()
    conn = get_conn()
    conn.execute(
        """INSERT INTO contacts (contact_id, tenant_id, customer_id, name, phone, email, is_primary, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (cid, tenant_id, customer_id, name, phone or "", email or "", 1 if is_primary else 0, now, now),
    )
    conn.commit()
    return contact_get(tenant_id, cid) or {}


def contact_update(
    tenant_id: str,
    contact_id: str,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    is_primary: Optional[bool] = None,
) -> Optional[Dict]:
    c = contact_get(tenant_id, contact_id)
    if not c:
        return None
    now = _ts()
    conn = get_conn()
    ip = (1 if is_primary else 0) if is_primary is not None else (1 if c["isPrimary"] else 0)
    conn.execute(
        """UPDATE contacts SET name = COALESCE(?, name), phone = COALESCE(?, phone), email = COALESCE(?, email),
           is_primary = ?, updated_at = ? WHERE contact_id = ? AND tenant_id = ?""",
        (name, phone, email, ip, now, contact_id, tenant_id),
    )
    conn.commit()
    return contact_get(tenant_id, contact_id)


def contact_delete(tenant_id: str, contact_id: str) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM contacts WHERE contact_id = ? AND tenant_id = ?", (contact_id, tenant_id))
    conn.commit()
    return cur.rowcount > 0


# ---------- Opportunities ----------
def opportunity_list(
    tenant_id: str,
    customer_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[List[Dict], int]:
    conn = get_conn()
    if customer_id:
        total = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE tenant_id = ? AND customer_id = ?", (tenant_id, customer_id)
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT opportunity_id, tenant_id, customer_id, title, amount_cents, currency, stage, status, created_at, updated_at
               FROM opportunities WHERE tenant_id = ? AND customer_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, customer_id, page_size, (page - 1) * page_size),
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM opportunities WHERE tenant_id = ?", (tenant_id,)).fetchone()[0]
        rows = conn.execute(
            """SELECT opportunity_id, tenant_id, customer_id, title, amount_cents, currency, stage, status, created_at, updated_at
               FROM opportunities WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, page_size, (page - 1) * page_size),
        ).fetchall()
    data = [
        {
            "opportunityId": r["opportunity_id"],
            "tenantId": r["tenant_id"],
            "customerId": r["customer_id"],
            "title": r["title"],
            "amountCents": r["amount_cents"],
            "currency": r["currency"],
            "stage": r["stage"],
            "status": r["status"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"],
        }
        for r in rows
    ]
    return data, total


def opportunity_get(tenant_id: str, opportunity_id: str) -> Optional[Dict]:
    conn = get_conn()
    r = conn.execute(
        """SELECT opportunity_id, tenant_id, customer_id, title, amount_cents, currency, stage, status, created_at, updated_at
           FROM opportunities WHERE opportunity_id = ? AND tenant_id = ?""",
        (opportunity_id, tenant_id),
    ).fetchone()
    if not r:
        return None
    return {
        "opportunityId": r["opportunity_id"],
        "tenantId": r["tenant_id"],
        "customerId": r["customer_id"],
        "title": r["title"],
        "amountCents": r["amount_cents"],
        "currency": r["currency"],
        "stage": r["stage"],
        "status": r["status"],
        "createdAt": r["created_at"],
        "updatedAt": r["updated_at"],
    }


def opportunity_create(
    tenant_id: str,
    customer_id: str,
    title: str,
    amount_cents: int = 0,
    currency: str = "CNY",
    stage: int = 1,
) -> Dict:
    oid = _id()
    now = _ts()
    conn = get_conn()
    conn.execute(
        """INSERT INTO opportunities (opportunity_id, tenant_id, customer_id, title, amount_cents, currency, stage, status, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,1,?,?)""",
        (oid, tenant_id, customer_id, title, amount_cents, currency, stage, now, now),
    )
    conn.commit()
    return opportunity_get(tenant_id, oid) or {}


def opportunity_update(
    tenant_id: str,
    opportunity_id: str,
    title: Optional[str] = None,
    amount_cents: Optional[int] = None,
    stage: Optional[int] = None,
) -> Optional[Dict]:
    o = opportunity_get(tenant_id, opportunity_id)
    if not o:
        return None
    now = _ts()
    conn = get_conn()
    conn.execute(
        """UPDATE opportunities SET title = COALESCE(?, title), amount_cents = COALESCE(?, amount_cents),
           stage = COALESCE(?, stage), updated_at = ? WHERE opportunity_id = ? AND tenant_id = ?""",
        (title, amount_cents, stage, now, opportunity_id, tenant_id),
    )
    conn.commit()
    return opportunity_get(tenant_id, opportunity_id)


def opportunity_delete(tenant_id: str, opportunity_id: str) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM opportunities WHERE opportunity_id = ? AND tenant_id = ?", (opportunity_id, tenant_id))
    conn.commit()
    return cur.rowcount > 0


# ---------- 操作审计（商用：可追溯） ----------
def audit_append(
    tenant_id: str,
    user_id: str,
    operation_type: str,
    resource_type: str = "",
    resource_id: str = "",
    trace_id: str = "",
) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO audit_log (tenant_id, user_id, operation_type, resource_type, resource_id, trace_id, occurred_at)
           VALUES (?,?,?,?,?,?,?)""",
        (tenant_id, user_id, operation_type, resource_type or "", resource_id or "", trace_id or "", _ts()),
    )
    conn.commit()


def audit_list(
    tenant_id: str,
    page: int = 1,
    page_size: int = 50,
    resource_type: Optional[str] = None,
) -> tuple[List[Dict], int]:
    conn = get_conn()
    if resource_type:
        total = conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE tenant_id = ? AND resource_type = ?", (tenant_id, resource_type)
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT log_id, tenant_id, user_id, operation_type, resource_type, resource_id, trace_id, occurred_at
               FROM audit_log WHERE tenant_id = ? AND resource_type = ? ORDER BY occurred_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, resource_type, page_size, (page - 1) * page_size),
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM audit_log WHERE tenant_id = ?", (tenant_id,)).fetchone()[0]
        rows = conn.execute(
            """SELECT log_id, tenant_id, user_id, operation_type, resource_type, resource_id, trace_id, occurred_at
               FROM audit_log WHERE tenant_id = ? ORDER BY occurred_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, page_size, (page - 1) * page_size),
        ).fetchall()
    data = [
        {
            "logId": r["log_id"],
            "tenantId": r["tenant_id"],
            "userId": r["user_id"],
            "operationType": r["operation_type"],
            "resourceType": r["resource_type"] or "",
            "resourceId": r["resource_id"] or "",
            "traceId": r["trace_id"] or "",
            "occurredAt": r["occurred_at"],
        }
        for r in rows
    ]
    return data, total


# ---------- Follow-ups 跟进记录 ----------
def follow_up_list(
    tenant_id: str,
    customer_id: Optional[str] = None,
    opportunity_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[List[Dict], int]:
    conn = get_conn()
    if customer_id:
        total = conn.execute(
            "SELECT COUNT(*) FROM follow_ups WHERE tenant_id = ? AND customer_id = ?", (tenant_id, customer_id)
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT follow_up_id, tenant_id, customer_id, opportunity_id, contact_id, content, follow_up_type, created_at, updated_at
               FROM follow_ups WHERE tenant_id = ? AND customer_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, customer_id, page_size, (page - 1) * page_size),
        ).fetchall()
    elif opportunity_id:
        total = conn.execute(
            "SELECT COUNT(*) FROM follow_ups WHERE tenant_id = ? AND opportunity_id = ?", (tenant_id, opportunity_id)
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT follow_up_id, tenant_id, customer_id, opportunity_id, contact_id, content, follow_up_type, created_at, updated_at
               FROM follow_ups WHERE tenant_id = ? AND opportunity_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, opportunity_id, page_size, (page - 1) * page_size),
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM follow_ups WHERE tenant_id = ?", (tenant_id,)).fetchone()[0]
        rows = conn.execute(
            """SELECT follow_up_id, tenant_id, customer_id, opportunity_id, contact_id, content, follow_up_type, created_at, updated_at
               FROM follow_ups WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, page_size, (page - 1) * page_size),
        ).fetchall()
    data = [
        {
            "followUpId": r["follow_up_id"],
            "tenantId": r["tenant_id"],
            "customerId": r["customer_id"] or "",
            "opportunityId": r["opportunity_id"] or "",
            "contactId": r["contact_id"] or "",
            "content": r["content"],
            "followUpType": r["follow_up_type"] or "call",
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"],
        }
        for r in rows
    ]
    return data, total


def follow_up_get(tenant_id: str, follow_up_id: str) -> Optional[Dict]:
    conn = get_conn()
    r = conn.execute(
        """SELECT follow_up_id, tenant_id, customer_id, opportunity_id, contact_id, content, follow_up_type, created_at, updated_at
           FROM follow_ups WHERE follow_up_id = ? AND tenant_id = ?""",
        (follow_up_id, tenant_id),
    ).fetchone()
    if not r:
        return None
    return {
        "followUpId": r["follow_up_id"],
        "tenantId": r["tenant_id"],
        "customerId": r["customer_id"] or "",
        "opportunityId": r["opportunity_id"] or "",
        "contactId": r["contact_id"] or "",
        "content": r["content"],
        "followUpType": r["follow_up_type"] or "call",
        "createdAt": r["created_at"],
        "updatedAt": r["updated_at"],
    }


def follow_up_create(
    tenant_id: str,
    content: str,
    customer_id: Optional[str] = None,
    opportunity_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    follow_up_type: str = "call",
) -> Dict:
    fid = _id()
    now = _ts()
    conn = get_conn()
    conn.execute(
        """INSERT INTO follow_ups (follow_up_id, tenant_id, customer_id, opportunity_id, contact_id, content, follow_up_type, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (fid, tenant_id, customer_id or "", opportunity_id or "", contact_id or "", content, follow_up_type, now, now),
    )
    conn.commit()
    return follow_up_get(tenant_id, fid) or {}


def follow_up_update(tenant_id: str, follow_up_id: str, content: Optional[str] = None) -> Optional[Dict]:
    f = follow_up_get(tenant_id, follow_up_id)
    if not f:
        return None
    now = _ts()
    conn = get_conn()
    conn.execute(
        "UPDATE follow_ups SET content = COALESCE(?, content), updated_at = ? WHERE follow_up_id = ? AND tenant_id = ?",
        (content, now, follow_up_id, tenant_id),
    )
    conn.commit()
    return follow_up_get(tenant_id, follow_up_id)


def follow_up_delete(tenant_id: str, follow_up_id: str) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM follow_ups WHERE follow_up_id = ? AND tenant_id = ?", (follow_up_id, tenant_id))
    conn.commit()
    return cur.rowcount > 0


# ---------- 客户负责人（数据权限：销售只能看自己的客户） ----------
def customer_owner_set(tenant_id: str, customer_id: str, owner_id: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO customer_owner (customer_id, tenant_id, owner_id, created_at) VALUES (?,?,?,?)",
        (customer_id, tenant_id, owner_id, _ts()),
    )
    conn.commit()


def customer_list_by_owner(tenant_id: str, owner_id: str, page: int = 1, page_size: int = 20) -> tuple[List[Dict], int]:
    """数据权限：仅返回 owner_id 负责的客户。"""
    conn = get_conn()
    total = conn.execute(
        "SELECT COUNT(*) FROM customers c INNER JOIN customer_owner o ON c.customer_id = o.customer_id AND c.tenant_id = o.tenant_id WHERE c.tenant_id = ? AND o.owner_id = ?",
        (tenant_id, owner_id),
    ).fetchone()[0]
    offset = (page - 1) * page_size
    rows = conn.execute(
        """SELECT c.customer_id, c.tenant_id, c.name, c.contact_phone, c.contact_email, c.status, c.created_at, c.updated_at
           FROM customers c INNER JOIN customer_owner o ON c.customer_id = o.customer_id AND c.tenant_id = o.tenant_id
           WHERE c.tenant_id = ? AND o.owner_id = ? ORDER BY c.created_at DESC LIMIT ? OFFSET ?""",
        (tenant_id, owner_id, page_size, offset),
    ).fetchall()
    data = [
        {
            "customerId": r["customer_id"],
            "tenantId": r["tenant_id"],
            "name": r["name"],
            "contactPhone": r["contact_phone"] or "",
            "contactEmail": r["contact_email"] or "",
            "status": r["status"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"],
        }
        for r in rows
    ]
    return data, total


# ---------- 合同 ----------
def contract_list(
    tenant_id: str,
    customer_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[List[Dict], int]:
    conn = get_conn()
    if customer_id:
        total = conn.execute(
            "SELECT COUNT(*) FROM contracts WHERE tenant_id = ? AND customer_id = ?", (tenant_id, customer_id)
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT contract_id, tenant_id, customer_id, opportunity_id, contract_no, amount_cents, currency, status, signed_at, created_at, updated_at
               FROM contracts WHERE tenant_id = ? AND customer_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, customer_id, page_size, (page - 1) * page_size),
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM contracts WHERE tenant_id = ?", (tenant_id,)).fetchone()[0]
        rows = conn.execute(
            """SELECT contract_id, tenant_id, customer_id, opportunity_id, contract_no, amount_cents, currency, status, signed_at, created_at, updated_at
               FROM contracts WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, page_size, (page - 1) * page_size),
        ).fetchall()
    data = [
        {
            "contractId": r["contract_id"],
            "tenantId": r["tenant_id"],
            "customerId": r["customer_id"],
            "opportunityId": r["opportunity_id"] or "",
            "contractNo": r["contract_no"],
            "amountCents": r["amount_cents"],
            "currency": r["currency"],
            "status": r["status"],
            "signedAt": r["signed_at"] or "",
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"],
        }
        for r in rows
    ]
    return data, total


def contract_get(tenant_id: str, contract_id: str) -> Optional[Dict]:
    conn = get_conn()
    r = conn.execute(
        """SELECT contract_id, tenant_id, customer_id, opportunity_id, contract_no, amount_cents, currency, status, signed_at, created_at, updated_at
           FROM contracts WHERE contract_id = ? AND tenant_id = ?""",
        (contract_id, tenant_id),
    ).fetchone()
    if not r:
        return None
    return {
        "contractId": r["contract_id"],
        "tenantId": r["tenant_id"],
        "customerId": r["customer_id"],
        "opportunityId": r["opportunity_id"] or "",
        "contractNo": r["contract_no"],
        "amountCents": r["amount_cents"],
        "currency": r["currency"],
        "status": r["status"],
        "signedAt": r["signed_at"] or "",
        "createdAt": r["created_at"],
        "updatedAt": r["updated_at"],
    }


def contract_create(
    tenant_id: str,
    customer_id: str,
    contract_no: str,
    amount_cents: int,
    opportunity_id: Optional[str] = None,
    currency: str = "CNY",
    signed_at: Optional[str] = None,
) -> Dict:
    cid = _id()
    now = _ts()
    conn = get_conn()
    conn.execute(
        """INSERT INTO contracts (contract_id, tenant_id, customer_id, opportunity_id, contract_no, amount_cents, currency, status, signed_at, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,1,?,?,?)""",
        (cid, tenant_id, customer_id, opportunity_id or "", contract_no, amount_cents, currency, signed_at or "", now, now),
    )
    conn.commit()
    return contract_get(tenant_id, cid) or {}


def contract_exists_by_no(tenant_id: str, contract_no: str) -> bool:
    conn = get_conn()
    r = conn.execute("SELECT 1 FROM contracts WHERE tenant_id = ? AND contract_no = ?", (tenant_id, contract_no)).fetchone()
    return r is not None


def contract_update_status(tenant_id: str, contract_id: str, status: int) -> Optional[Dict]:
    c = contract_get(tenant_id, contract_id)
    if not c:
        return None
    now = _ts()
    conn = get_conn()
    conn.execute("UPDATE contracts SET status = ?, updated_at = ? WHERE contract_id = ? AND tenant_id = ?", (status, now, contract_id, tenant_id))
    conn.commit()
    return contract_get(tenant_id, contract_id)


# ---------- 回款 ----------
def payment_list(tenant_id: str, contract_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> tuple[List[Dict], int]:
    conn = get_conn()
    if contract_id:
        total = conn.execute(
            "SELECT COUNT(*) FROM payment_records WHERE tenant_id = ? AND contract_id = ?", (tenant_id, contract_id)
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT payment_id, tenant_id, contract_id, amount_cents, payment_at, remark, created_at
               FROM payment_records WHERE tenant_id = ? AND contract_id = ? ORDER BY payment_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, contract_id, page_size, (page - 1) * page_size),
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM payment_records WHERE tenant_id = ?", (tenant_id,)).fetchone()[0]
        rows = conn.execute(
            """SELECT payment_id, tenant_id, contract_id, amount_cents, payment_at, remark, created_at
               FROM payment_records WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (tenant_id, page_size, (page - 1) * page_size),
        ).fetchall()
    data = [
        {
            "paymentId": r["payment_id"],
            "tenantId": r["tenant_id"],
            "contractId": r["contract_id"],
            "amountCents": r["amount_cents"],
            "paymentAt": r["payment_at"],
            "remark": r["remark"] or "",
            "createdAt": r["created_at"],
        }
        for r in rows
    ]
    return data, total


def payment_get(tenant_id: str, payment_id: str) -> Optional[Dict]:
    conn = get_conn()
    r = conn.execute(
        "SELECT payment_id, tenant_id, contract_id, amount_cents, payment_at, remark, created_at FROM payment_records WHERE payment_id = ? AND tenant_id = ?",
        (payment_id, tenant_id),
    ).fetchone()
    if not r:
        return None
    return {
        "paymentId": r["payment_id"],
        "tenantId": r["tenant_id"],
        "contractId": r["contract_id"],
        "amountCents": r["amount_cents"],
        "paymentAt": r["payment_at"],
        "remark": r["remark"] or "",
        "createdAt": r["created_at"],
    }


def payment_create(tenant_id: str, contract_id: str, amount_cents: int, payment_at: str, remark: Optional[str] = None) -> Dict:
    pid = _id()
    now = _ts()
    conn = get_conn()
    conn.execute(
        "INSERT INTO payment_records (payment_id, tenant_id, contract_id, amount_cents, payment_at, remark, created_at) VALUES (?,?,?,?,?,?,?)",
        (pid, tenant_id, contract_id, amount_cents, payment_at, remark or "", now),
    )
    conn.commit()
    r = conn.execute(
        "SELECT payment_id, tenant_id, contract_id, amount_cents, payment_at, remark, created_at FROM payment_records WHERE payment_id = ?",
        (pid,),
    ).fetchone()
    if not r:
        return {}
    return {
        "paymentId": r["payment_id"],
        "tenantId": r["tenant_id"],
        "contractId": r["contract_id"],
        "amountCents": r["amount_cents"],
        "paymentAt": r["payment_at"],
        "remark": r["remark"] or "",
        "createdAt": r["created_at"],
    }


# ---------- 销售漏斗统计（商机按阶段汇总） ----------
def opportunity_funnel(tenant_id: str) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT stage, status, COUNT(*) AS cnt, COALESCE(SUM(amount_cents), 0) AS total_cents
           FROM opportunities WHERE tenant_id = ? GROUP BY stage, status""",
        (tenant_id,),
    ).fetchall()
    return [
        {"stage": r["stage"], "status": r["status"], "count": r["cnt"], "totalAmountCents": r["total_cents"]}
        for r in rows
    ]
