from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event
from consumerdost.config import settings
from consumerdost.database.models import Base


# Ensure sqlite database parent directory exists
db_url = settings.database_url
if db_url.startswith("sqlite+aiosqlite:///"):
    path_str = db_url.replace("sqlite+aiosqlite:///", "")
    db_path = Path(path_str)
    if not db_path.is_absolute():
        db_path = settings.base_dir / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine_url = f"sqlite+aiosqlite:///{db_path}"
else:
    engine_url = db_url

engine = create_async_engine(
    engine_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine.sync_engine, "connect")
def configure_sqlite_pragmas(dbapi_connection, connection_record):
    """Enable WAL mode and foreign key constraints for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.close()


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables in the SQLite database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Async session context provider."""
    async with AsyncSessionLocal() as session:
        yield session
