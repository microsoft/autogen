import configparser
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.engine import make_url

from autogenstudio.database.schema_manager import SchemaManager


def _alembic_ini_url(engine_uri: str) -> str:
    """Generate the alembic.ini content for a URI and return the parsed sqlalchemy.url."""
    # _generate_alembic_ini_content() only reads engine.url, so a lightweight stub
    # keeps this pure URL-rendering test free of DBAPI driver imports (psycopg/libpq).
    engine = SimpleNamespace(url=make_url(engine_uri))
    schema_manager = SchemaManager(engine=engine, base_dir=Path("/tmp/schema_manager_test"))  # type: ignore[arg-type]
    content = schema_manager._generate_alembic_ini_content()
    parser = configparser.ConfigParser()
    parser.read_string(content)
    return parser.get("alembic", "sqlalchemy.url")


def test_alembic_ini_preserves_database_password():
    """Regression test for #7341: the URL written to alembic.ini must keep the real
    password. SQLAlchemy 2.x masks passwords in ``str(URL)`` as ``***``, so writing
    that form into alembic.ini made Alembic authenticate with the literal ``***`` and
    fail with "password authentication failed" on first-time database initialization
    even though the application engine itself connected successfully."""
    ini_url = _alembic_ini_url("postgresql+psycopg://autogen:autogen@postgres:5432/autogen")
    assert make_url(ini_url).password == "autogen"
    assert "***" not in ini_url


def test_alembic_ini_roundtrips_password_with_special_characters():
    """Passwords with URL-reserved characters must survive the alembic.ini round trip
    (URL encoding on render + ConfigParser ``%%`` escaping)."""
    ini_url = _alembic_ini_url("postgresql+psycopg://alice:p%40ssw0rd@db.example.com:5432/app")
    parsed = make_url(ini_url)
    assert parsed.username == "alice"
    assert parsed.password == "p@ssw0rd"
    assert parsed.host == "db.example.com"
