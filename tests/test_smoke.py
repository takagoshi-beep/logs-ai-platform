from app.main import health


def test_health():
    result = health()
    assert result["status"] == "ok"
