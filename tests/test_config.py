import pytest
from pydantic import ValidationError

from eleicoes_api.core.config import Settings


def test_default_tse_settings():
    settings = Settings(_env_file=None)

    assert settings.tse_http_timeout > 0
    assert settings.tse_cache_ttl == 15.0
    assert settings.tse_cache_max_entries == 512


def test_tse_settings_read_environment(monkeypatch):
    monkeypatch.setenv("TSE_HTTP_TIMEOUT", "20")
    monkeypatch.setenv("TSE_CACHE_TTL", "60")
    monkeypatch.setenv("TSE_CACHE_MAX_ENTRIES", "1000")

    settings = Settings(_env_file=None)

    assert settings.tse_http_timeout == 20.0
    assert settings.tse_cache_ttl == 60.0
    assert settings.tse_cache_max_entries == 1000


def test_rejects_invalid_timeout():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, tse_http_timeout=0)


def test_rejects_negative_cache_ttl():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, tse_cache_ttl=-1)


def test_allows_disabling_cache():
    settings = Settings(
        _env_file=None,
        tse_cache_ttl=0,
        tse_cache_max_entries=0,
    )

    assert settings.tse_cache_ttl == 0
    assert settings.tse_cache_max_entries == 0