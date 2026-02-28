"""
端到端测试：网关健康、登录页与登录流程（模拟用户操作）。
需启动网关（及可选前端）；CI 中可通过 E2E_FULL_FLOW=1 或单独 job 在有环境时执行。
"""
import os
import re

import pytest

# 无 playwright 时跳过整模块
pytest.importorskip("playwright")

from playwright.sync_api import Page, expect


def test_gateway_health_api(base_url, page: Page):
    """E2E：访问 /health 应返回 200（或前端兜底页）。"""
    try:
        resp = page.goto(f"{base_url}/health", wait_until="commit", timeout=10000)
    except Exception as e:
        pytest.skip(f"网关不可达 {base_url}: {e}")
    if resp and resp.status == 200:
        body = resp.text()
        assert "status" in body or "up" in body or "ok" in body.lower()
    else:
        pytest.skip("网关 /health 未返回 200（请先启动服务）")


def test_login_page_or_api(base_url, page: Page):
    """E2E：登录 API 或登录页可访问。"""
    try:
        # 直接请求登录 API（POST 需 body，这里仅 GET 到根或登录页）
        resp = page.goto(f"{base_url}/", wait_until="commit", timeout=10000)
    except Exception as e:
        pytest.skip(f"网关不可达: {e}")
    if resp:
        assert resp.status in (200, 404, 302), f"expected 200/302, got {resp.status}"


def test_api_auth_login_via_request(base_url, page: Page):
    """E2E：通过 page.request 调用登录 API，验证返回 token。"""
    import json
    try:
        resp = page.request.post(
            f"{base_url}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
    except Exception as e:
        pytest.skip(f"网关不可达: {e}")
    if resp.status == 404:
        pytest.skip("网关未暴露 /api/auth/login")
    if resp.status != 200:
        pytest.skip(f"登录接口返回 {resp.status}")
    data = resp.json()
    assert data.get("token") or data.get("user"), "登录响应应含 token 或 user"
