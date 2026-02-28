"""
模块间业务联动 Worker：轮询事件总线，按事件类型调用网关/数据湖标准化接口。
实现：CRM→ERP、ERP→SRM、全模块→OA、全模块→数据湖；智能制造 ERP→MES→WMS→TMS 全流程联动。
严格解耦：仅通过 HTTP 调用网关 /api/v1/<cell>/<path> 与 /api/datalake/ingest，不导入任何细胞代码。
"""
from __future__ import annotations

import os
import time
import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger("sync_worker")

# 联动开关（环境变量）
LINK_CRM_TO_ERP = os.environ.get("LINK_CRM_TO_ERP", "1") == "1"
LINK_ERP_TO_SRM = os.environ.get("LINK_ERP_TO_SRM", "1") == "1"
LINK_ALL_TO_OA = os.environ.get("LINK_ALL_TO_OA", "1") == "1"
LINK_ALL_TO_DATALAKE = os.environ.get("LINK_ALL_TO_DATALAKE", "1") == "1"
# 智能制造全场景联动（批次1+2）
LINK_ERP_TO_MES = os.environ.get("LINK_ERP_TO_MES", "1") == "1"
LINK_MES_TO_WMS = os.environ.get("LINK_MES_TO_WMS", "1") == "1"
LINK_WMS_TO_TMS = os.environ.get("LINK_WMS_TO_TMS", "1") == "1"
# 默认车间/仓库（联动创建 MES 生产订单、WMS 出入库时使用）
DEFAULT_WORKSHOP_ID = os.environ.get("SMART_MFG_DEFAULT_WORKSHOP_ID", "WS01")
DEFAULT_WAREHOUSE_ID = os.environ.get("SMART_MFG_DEFAULT_WAREHOUSE_ID", "WH01")

GATEWAY_URL = (os.environ.get("GATEWAY_URL") or "http://localhost:8000").strip().rstrip("/")
DATALAKE_URL = (os.environ.get("DATALAKE_URL") or "").strip().rstrip("/")
AUTH_TOKEN = os.environ.get("EVENT_BUS_TOKEN") or os.environ.get("GATEWAY_TOKEN") or "smoke-test"
POLL_INTERVAL_SEC = max(1, int(os.environ.get("SYNC_WORKER_POLL_INTERVAL_SEC", "5")))


def _req(method: str, url: str, body: dict | None = None, tenant_id: str = "default") -> tuple[int, dict]:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AUTH_TOKEN}", "X-Tenant-Id": tenant_id, "X-Request-ID": f"sync-{int(time.time()*1000)}"}
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.getcode(), json.loads(r.read().decode()) if r.length else {}
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        logger.warning("request failed %s %s: %s", method, url, e)
        return 0, {}


def _ingest(tenant_id: str, cell_id: str, table: str, records: list, sync_type: str = "incremental") -> bool:
    if not DATALAKE_URL or not LINK_ALL_TO_DATALAKE:
        return True
    url = f"{DATALAKE_URL}/api/datalake/ingest"
    body = {"tenantId": tenant_id, "cellId": cell_id, "table": table, "syncType": sync_type, "records": records}
    code, _ = _req("POST", url, body, tenant_id)
    return code in (200, 201)


def _handle_crm_contract_signed(payload: dict) -> None:
    tenant_id = payload.get("tenantId") or "default"
    if LINK_CRM_TO_ERP:
        url = f"{GATEWAY_URL}/api/v1/erp/orders"
        body = {"customerId": payload.get("customerId", ""), "totalAmountCents": payload.get("amountCents", 0), "currency": payload.get("currency", "CNY")}
        code, resp = _req("POST", url, body, tenant_id)
        if code in (200, 201) and resp.get("orderId"):
            logger.info("crm→erp order created orderId=%s", resp.get("orderId"))
            if LINK_ALL_TO_OA:
                oa_body = {"typeCode": "contract", "formData": {"sourceCell": "crm", "sourceId": payload.get("contractId"), "sourceType": "contract", "erpOrderId": resp.get("orderId")}}
                _req("POST", f"{GATEWAY_URL}/api/v1/oa/approvals", oa_body, tenant_id)
    if LINK_ALL_TO_DATALAKE:
        _ingest(tenant_id, "crm", "contracts", [payload])


def _handle_erp_order_created(payload: dict) -> None:
    tenant_id = payload.get("tenantId") or "default"
    if LINK_ALL_TO_OA:
        oa_body = {"typeCode": "sales_order", "formData": {"sourceCell": "erp", "sourceId": payload.get("orderId"), "sourceType": "order"}}
        _req("POST", f"{GATEWAY_URL}/api/v1/oa/approvals", oa_body, tenant_id)
    # ERP→MES：销售订单自动生成 MES 生产计划与生产订单
    if LINK_ERP_TO_MES:
        order_id = payload.get("orderId", "")
        plan_body = {"planNo": order_id, "productSku": "PROD-DEFAULT", "plannedQty": 1, "planDate": ""}
        code_plan, resp_plan = _req("POST", f"{GATEWAY_URL}/api/v1/mes/production-plans", plan_body, tenant_id)
        if code_plan in (200, 201) and resp_plan.get("planId"):
            plan_id = resp_plan.get("planId")
            order_lines = payload.get("orderLines") or []
            if not order_lines:
                order_lines = [{"productSku": "PROD-DEFAULT", "quantity": 1}]
            for line in order_lines:
                product_sku = (line.get("productSku") or "PROD-DEFAULT").strip()
                qty = float(line.get("quantity", 1))
                po_body = {"workshopId": DEFAULT_WORKSHOP_ID, "orderNo": order_id, "productSku": product_sku, "quantity": qty, "planId": plan_id}
                code_po, resp_po = _req("POST", f"{GATEWAY_URL}/api/v1/mes/production-orders", po_body, tenant_id)
                if code_po in (200, 201):
                    logger.info("erp→mes production order created orderId=%s", resp_po.get("orderId"))
    if LINK_ALL_TO_DATALAKE:
        _ingest(tenant_id, "erp", "orders", [payload])


def _handle_erp_purchase_requisition_created(payload: dict) -> None:
    tenant_id = payload.get("tenantId") or "default"
    if LINK_ERP_TO_SRM:
        url = f"{GATEWAY_URL}/api/v1/srm/rfqs"
        body = {"demandId": payload.get("requisitionId", "")}
        code, resp = _req("POST", url, body, tenant_id)
        if code in (200, 201):
            logger.info("erp→srm rfq created rfqId=%s", resp.get("rfqId"))
    if LINK_ALL_TO_DATALAKE:
        _ingest(tenant_id, "erp", "purchase_requisitions", [payload])


def _handle_erp_purchase_order_created(payload: dict) -> None:
    tenant_id = payload.get("tenantId") or "default"
    if LINK_ALL_TO_OA:
        oa_body = {"typeCode": "purchase_order", "formData": {"sourceCell": "erp", "sourceId": payload.get("poId"), "sourceType": "purchase_order"}}
        _req("POST", f"{GATEWAY_URL}/api/v1/oa/approvals", oa_body, tenant_id)
    if LINK_ALL_TO_DATALAKE:
        _ingest(tenant_id, "erp", "purchase_orders", [payload])


def _handle_srm_quote_awarded(payload: dict) -> None:
    tenant_id = payload.get("tenantId") or "default"
    if LINK_ERP_TO_SRM:
        url = f"{GATEWAY_URL}/api/v1/erp/mm/purchase-orders"
        body = {"supplierId": payload.get("supplierId", ""), "documentNo": f"PO-{payload.get('quoteId', '')[:8]}", "totalAmountCents": payload.get("amountCents", 0)}
        code, resp = _req("POST", url, body, tenant_id)
        if code in (200, 201):
            logger.info("srm→erp po created poId=%s", resp.get("poId"))
    if LINK_ALL_TO_DATALAKE:
        _ingest(tenant_id, "srm", "quotes", [payload])


def _handle_mes_production_order_created(payload: dict) -> None:
    """MES 生产订单创建 → 拉取 BOM 物料需求 → WMS 创建生产备料/领料出库单（typeCode=picking）。"""
    tenant_id = payload.get("tenantId") or "default"
    if not LINK_MES_TO_WMS:
        return
    order_id = payload.get("orderId", "")
    if not order_id:
        return
    code, resp = _req("GET", f"{GATEWAY_URL}/api/v1/mes/production-orders/{order_id}/material-requirements", tenant_id=tenant_id)
    if code != 200 or not resp.get("requirements"):
        logger.info("mes production order %s no material requirements or get failed", order_id)
        return
    requirements = resp.get("requirements", [])
    ob_body = {"warehouseId": DEFAULT_WAREHOUSE_ID, "typeCode": "picking", "sourceOrderId": order_id}
    code_ob, resp_ob = _req("POST", f"{GATEWAY_URL}/api/v1/wms/outbound-orders", ob_body, tenant_id)
    if code_ob not in (200, 201) or not resp_ob.get("orderId"):
        logger.warning("wms outbound (picking) create failed for mes order %s", order_id)
        return
    wms_ob_id = resp_ob.get("orderId")
    for req in requirements:
        sku = req.get("materialSku", "")
        qty = int(float(req.get("requiredQuantity", 0)) or 1)
        if not sku:
            continue
        _req("POST", f"{GATEWAY_URL}/api/v1/wms/outbound-orders/{wms_ob_id}/lines", {"skuId": sku, "quantity": qty}, tenant_id)
    logger.info("mes→wms picking outbound created wmsOrderId=%s for mesOrderId=%s", wms_ob_id, order_id)


def _handle_mes_production_order_completed(payload: dict) -> None:
    """MES 生产完成 → WMS 创建生产入库单（typeCode=production），erpOrderId=orderNo 便于回写 ERP。"""
    tenant_id = payload.get("tenantId") or "default"
    if not LINK_MES_TO_WMS:
        return
    order_id = payload.get("orderId", "")
    order_no = payload.get("orderNo", "")  # 即 ERP 订单 ID
    product_sku = (payload.get("productSku") or "PROD-DEFAULT").strip()
    quantity = int(float(payload.get("quantity", 1)) or 1)
    ib_body = {"warehouseId": DEFAULT_WAREHOUSE_ID, "typeCode": "production", "sourceOrderId": order_id, "erpOrderId": order_no}
    code_ib, resp_ib = _req("POST", f"{GATEWAY_URL}/api/v1/wms/inbound-orders", ib_body, tenant_id)
    if code_ib not in (200, 201) or not resp_ib.get("orderId"):
        logger.warning("wms inbound (production) create failed for mes order %s", order_id)
        return
    _req("POST", f"{GATEWAY_URL}/api/v1/wms/inbound-orders/{resp_ib.get('orderId')}/lines", {"skuId": product_sku, "quantity": quantity}, tenant_id)
    logger.info("mes→wms production inbound created wmsOrderId=%s erpOrderId=%s", resp_ib.get("orderId"), order_no)


def _handle_wms_inbound_completed(payload: dict) -> None:
    """WMS 生产入库完成 → 回传 ERP 更新订单状态为生产完成（orderStatus=3）。"""
    if (payload.get("typeCode") or "").strip().lower() != "production":
        return
    erp_order_id = (payload.get("erpOrderId") or "").strip()
    if not erp_order_id:
        return
    tenant_id = payload.get("tenantId") or "default"
    code, _ = _req("PATCH", f"{GATEWAY_URL}/api/v1/erp/orders/{erp_order_id}", {"orderStatus": 3}, tenant_id)
    if code in (200, 204):
        logger.info("wms production inbound→erp order status updated orderId=%s status=3", erp_order_id)


def _handle_wms_outbound_completed(payload: dict) -> None:
    """WMS 销售出库完成 → 同步 TMS 生成运输订单，携带 wmsOutboundOrderId、erpOrderId 便于签收回写。"""
    if (payload.get("typeCode") or "").strip().lower() != "sales":
        return
    if not LINK_WMS_TO_TMS:
        return
    tenant_id = payload.get("tenantId") or "default"
    wms_order_id = payload.get("orderId", "")
    erp_order_id = (payload.get("erpOrderId") or "").strip()
    body = {"origin": "factory", "destination": "customer", "wmsOutboundOrderId": wms_order_id, "erpOrderId": erp_order_id}
    code, resp = _req("POST", f"{GATEWAY_URL}/api/v1/tms/shipments", body, tenant_id)
    if code in (200, 201):
        logger.info("wms sales outbound→tms shipment created shipmentId=%s wmsOrderId=%s", resp.get("shipmentId"), wms_order_id)


def _handle_tms_shipment_delivered(payload: dict) -> None:
    """TMS 签收完成 → 回传 WMS 出库单状态、ERP 订单状态为已送达（orderStatus=4）。"""
    tenant_id = payload.get("tenantId") or "default"
    wms_order_id = (payload.get("wmsOutboundOrderId") or "").strip()
    erp_order_id = (payload.get("erpOrderId") or "").strip()
    if wms_order_id:
        _req("PATCH", f"{GATEWAY_URL}/api/v1/wms/outbound-orders/{wms_order_id}", {"status": 3}, tenant_id)
        logger.info("tms delivered→wms outbound status updated orderId=%s", wms_order_id)
    if erp_order_id:
        _req("PATCH", f"{GATEWAY_URL}/api/v1/erp/orders/{erp_order_id}", {"orderStatus": 4}, tenant_id)
        logger.info("tms delivered→erp order status updated orderId=%s status=4", erp_order_id)


def _handle_oa_approval_completed(payload: dict) -> None:
    form = payload.get("formData") or {}
    source_cell = form.get("sourceCell")
    source_id = form.get("sourceId")
    source_type = form.get("sourceType")
    status = payload.get("status")
    tenant_id = payload.get("tenantId") or "default"
    if status != "approved" or not source_cell or not source_id:
        return
    if source_cell == "erp" and source_type == "order":
        url = f"{GATEWAY_URL}/api/v1/erp/orders/{source_id}"
        _req("PATCH", url, {"orderStatus": 2}, tenant_id)
    elif source_cell == "erp" and source_type == "purchase_order":
        url = f"{GATEWAY_URL}/api/v1/erp/mm/purchase-orders/{source_id}"
        _req("PATCH", url, {"status": 2}, tenant_id)
    elif source_cell == "crm" and source_type == "contract":
        url = f"{GATEWAY_URL}/api/v1/crm/contracts/{source_id}"
        _req("PATCH", url, {"status": 2}, tenant_id)


def dispatch(event_type: str, payload: dict) -> None:
    try:
        if event_type == "crm.contract.signed":
            _handle_crm_contract_signed(payload)
        elif event_type == "erp.order.created":
            _handle_erp_order_created(payload)
        elif event_type == "erp.purchase_requisition.created":
            _handle_erp_purchase_requisition_created(payload)
        elif event_type == "erp.purchase_order.created":
            _handle_erp_purchase_order_created(payload)
        elif event_type == "srm.quote.awarded":
            _handle_srm_quote_awarded(payload)
        elif event_type == "mes.production_order.created":
            _handle_mes_production_order_created(payload)
        elif event_type == "mes.production_order.completed":
            _handle_mes_production_order_completed(payload)
        elif event_type == "wms.inbound.completed":
            _handle_wms_inbound_completed(payload)
        elif event_type == "wms.outbound.completed":
            _handle_wms_outbound_completed(payload)
        elif event_type == "tms.shipment.delivered":
            _handle_tms_shipment_delivered(payload)
        elif event_type == "oa.approval.completed":
            _handle_oa_approval_completed(payload)
        else:
            if LINK_ALL_TO_DATALAKE and payload:
                tenant_id = payload.get("tenantId") or "default"
                cell = event_type.split(".")[0] if "." in event_type else "unknown"
                _ingest(tenant_id, cell, "events", [{"eventType": event_type, **payload}])
    except Exception as e:
        logger.exception("dispatch %s: %s", event_type, e)


def run_once(since_ts: float) -> float:
    url = f"{GATEWAY_URL}/api/events?limit=50&since={since_ts}"
    code, resp = _req("GET", url, tenant_id="default")
    if code != 200:
        return since_ts
    data = resp.get("data") or []
    last_ts = since_ts
    for e in data:
        ts = e.get("ts") or 0
        if ts > last_ts:
            last_ts = ts
        event_type = (e.get("eventType") or "").strip()
        payload = e.get("payload") or e.get("data") or {}
        if event_type:
            dispatch(event_type, payload if isinstance(payload, dict) else {})
    return last_ts


def run_loop() -> None:
    since = time.time() - 3600
    while True:
        try:
            since = run_once(since)
        except Exception as e:
            logger.exception("run_once: %s", e)
        time.sleep(POLL_INTERVAL_SEC)
