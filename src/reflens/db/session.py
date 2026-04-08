"""Database session management."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from reflens.config import Settings, get_settings
from reflens.db.models import Base

_session_factory: sessionmaker[Session] | None = None


def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db(settings: Settings | None = None) -> sessionmaker[Session]:
    """Initialize the database engine and create all tables."""
    global _session_factory

    if settings is None:
        settings = get_settings()

    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(settings.database_url, connect_args=connect_args)

    if settings.database_url.startswith("sqlite"):
        event.listen(engine, "connect", _set_sqlite_pragma)

    try:
        Base.metadata.create_all(engine)
    except Exception:
        pass  # Tables may already exist from concurrent init

    _session_factory = sessionmaker(bind=engine)
    return _session_factory


def get_session() -> Session:
    """Get a new database session."""
    global _session_factory

    if _session_factory is None:
        _session_factory = init_db()

    return _session_factory()
