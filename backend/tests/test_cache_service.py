import pytest

from app.services.cache import _redact_redis_url


@pytest.mark.unit
def test_redact_redis_url_hides_password():
    redacted = _redact_redis_url(
        "redis://default:secret-password@redis.example.com:11817/0"
    )

    assert "secret-password" not in redacted
    assert redacted == "redis://default:***@redis.example.com:11817/0"


@pytest.mark.unit
def test_redact_redis_url_keeps_url_without_credentials():
    assert _redact_redis_url("redis://localhost:6379/0") == "redis://localhost:6379/0"
