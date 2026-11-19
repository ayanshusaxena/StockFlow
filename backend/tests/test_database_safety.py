from pathlib import Path

import pytest

from tests.database_safety import UnsafeDatabaseConfiguration, validate_test_database


def validate(env: dict[str, str], env_file: Path):
    return validate_test_database(env, env_file)


def test_valid_isolated_test_database(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://dev:secret@127.0.0.1:5432/stockflow\n", encoding="utf-8"
    )
    result = validate(
        {"TEST_DATABASE_URL": "postgresql+psycopg://test:secret@localhost/stockflow_test"},
        env_file,
    )
    assert result.endswith("/stockflow_test")


def test_rejects_exact_development_database_match(tmp_path):
    test_url = "postgresql://user:secret@127.0.0.1:5432/stockflow_test"
    with pytest.raises(UnsafeDatabaseConfiguration, match="identifies"):
        validate({"DATABASE_URL": test_url, "TEST_DATABASE_URL": test_url}, tmp_path / ".env")


def test_rejects_dotenv_development_url_conflict(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://dev:secret@127.0.0.1/stockflow_test\n", encoding="utf-8"
    )
    with pytest.raises(UnsafeDatabaseConfiguration, match="identifies"):
        validate(
            {"TEST_DATABASE_URL": "postgresql+psycopg://test:other@localhost:5432/stockflow_test"},
            env_file,
        )


def test_process_database_url_overrides_dotenv(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://dev:secret@127.0.0.1/stockflow_test\n", encoding="utf-8"
    )
    result = validate(
        {
            "DATABASE_URL": "postgresql://dev:secret@127.0.0.1/stockflow",
            "TEST_DATABASE_URL": "postgresql://test:secret@localhost/stockflow_test",
        },
        env_file,
    )
    assert result.endswith("/stockflow_test")


def test_detects_localhost_and_ipv4_url_alias(tmp_path):
    with pytest.raises(UnsafeDatabaseConfiguration, match="identifies"):
        validate(
            {
                "DATABASE_URL": "postgresql://dev:one@127.0.0.1:5432/stockflow_test",
                "TEST_DATABASE_URL": "postgresql+psycopg://test:two@localhost/stockflow_test",
            },
            tmp_path / ".env",
        )


def test_rejects_missing_test_database_url(tmp_path):
    with pytest.raises(UnsafeDatabaseConfiguration, match="Set TEST_DATABASE_URL"):
        validate({"DATABASE_URL": "postgresql://dev@localhost/stockflow"}, tmp_path / ".env")


def test_rejects_missing_development_database_identity(tmp_path):
    with pytest.raises(UnsafeDatabaseConfiguration, match="Set DATABASE_URL"):
        validate({"TEST_DATABASE_URL": "postgresql://test@localhost/stockflow_test"}, tmp_path / ".env")


def test_rejects_non_loopback_host(tmp_path):
    with pytest.raises(UnsafeDatabaseConfiguration, match="loopback"):
        validate(
            {
                "DATABASE_URL": "postgresql://dev@localhost/stockflow",
                "TEST_DATABASE_URL": "postgresql://test@192.0.2.1/stockflow_test",
            },
            tmp_path / ".env",
        )


def test_rejects_unresolvable_test_host_closed(tmp_path):
    with pytest.raises(UnsafeDatabaseConfiguration, match="Could not safely resolve"):
        validate(
            {
                "DATABASE_URL": "postgresql://dev@localhost/stockflow",
                "TEST_DATABASE_URL": "postgresql://test@not-a-real-host.invalid/stockflow_test",
            },
            tmp_path / ".env",
        )


def test_rejects_database_name_without_test_suffix(tmp_path):
    with pytest.raises(UnsafeDatabaseConfiguration, match="end in"):
        validate(
            {
                "DATABASE_URL": "postgresql://dev@localhost/stockflow",
                "TEST_DATABASE_URL": "postgresql://test@localhost/stockflowtest",
            },
            tmp_path / ".env",
        )
