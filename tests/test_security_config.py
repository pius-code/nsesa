import os

import pytest

from core.config import get_auth_config


def test_auth_secret_is_required_in_production(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        get_auth_config()


def test_auth_secret_allows_local_dev_defaults(monkeypatch):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    config = get_auth_config()

    assert config.jwt_secret
    assert config.jwt_algorithm == "HS256"
