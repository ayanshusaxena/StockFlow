"""Fail-closed validation for the database pytest will migrate and truncate."""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import URL, make_url


class UnsafeDatabaseConfiguration(RuntimeError):
    """Raised when the test target cannot be proven safe to mutate."""


def _effective_development_url(env: dict[str, str], env_file: Path) -> str | None:
    process_url = env.get("DATABASE_URL")
    if process_url:
        return process_url
    file_url = dotenv_values(env_file).get("DATABASE_URL") if env_file.exists() else None
    return str(file_url) if file_url else None


def _host_addresses(host: str) -> frozenset[str]:
    try:
        return frozenset(
            ipaddress.ip_address(item[4][0].split("%", 1)[0]).compressed
            for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        )
    except (OSError, ValueError) as exc:
        raise UnsafeDatabaseConfiguration(
            "Could not safely resolve a configured database host; refusing destructive tests."
        ) from exc


def _database_identity(url: URL) -> tuple[frozenset[str], int, str]:
    if not url.host or not url.database:
        raise UnsafeDatabaseConfiguration(
            "Database host and name must be explicit to validate destructive test safety."
        )
    addresses = _host_addresses(url.host)
    port = url.port or 5432
    return addresses, port, url.database


def validate_test_database(env: dict[str, str], env_file: Path) -> str:
    raw_test_url = env.get("TEST_DATABASE_URL")
    if not raw_test_url:
        raise UnsafeDatabaseConfiguration(
            "Set TEST_DATABASE_URL to an isolated loopback PostgreSQL database ending in '_test'."
        )
    try:
        test_url = make_url(raw_test_url)
    except (TypeError, ValueError):
        raise UnsafeDatabaseConfiguration("TEST_DATABASE_URL is not a valid database URL.") from None

    if test_url.get_backend_name() != "postgresql":
        raise UnsafeDatabaseConfiguration("The test database URL must use PostgreSQL.")

    if test_url.host is None or _host_addresses(test_url.host) - {
        "127.0.0.1", "::1"
    }:
        raise UnsafeDatabaseConfiguration("Tests only run against a loopback PostgreSQL database.")
    if not test_url.database or not test_url.database.endswith("_test"):
        raise UnsafeDatabaseConfiguration("The test database name must end in '_test'.")

    development_raw = _effective_development_url(env, env_file)
    if not development_raw:
        raise UnsafeDatabaseConfiguration(
            "Set DATABASE_URL in the process environment or backend .env so the test target can be compared."
        )
    try:
        development_url = make_url(development_raw)
    except (TypeError, ValueError):
        raise UnsafeDatabaseConfiguration(
            "DATABASE_URL is invalid; refusing destructive tests."
        ) from None

    test_addresses, test_port, test_name = _database_identity(test_url)
    dev_addresses, dev_port, dev_name = _database_identity(development_url)
    if test_addresses.intersection(dev_addresses) and test_port == dev_port and test_name == dev_name:
        raise UnsafeDatabaseConfiguration(
            "TEST_DATABASE_URL identifies the configured development database; refusing destructive tests."
        )
    return raw_test_url
