"""
网关 /demo 演示页：前后端运行确认页可正常返回。
"""
import pytest

try:
    from platform_core.core.gateway.app import create_app
    HAS_FLASK = True
except Exception:
    HAS_FLASK = False
    create_app = None


@pytest.fixture
def gateway_app():
    if not HAS_FLASK or create_app is None:
        pytest.skip("flask or gateway not available")
    return create_app(registry_resolver=lambda c: "http://localhost:8001", use_dynamic_routes=False)


def test_demo_page_returns_html(gateway_app):
    with gateway_app.test_client() as client:
        r = client.get("/demo")
    assert r.status_code == 200
    assert "text/html" in (r.content_type or "")
    text = r.get_data(as_text=True)
    assert "细胞" in text or "demo" in text
