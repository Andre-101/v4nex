from app.core.config import settings


def test_test_config_uses_sqlite_in_memory() -> None:
    assert settings.app_env == "test"
    assert settings.database_url == "sqlite:///:memory:"
