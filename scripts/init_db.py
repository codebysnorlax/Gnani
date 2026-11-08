import asyncio
from saarthi.database.engine import init_db


async def main():
    print("Initializing SQLite database with WAL mode...")
    await init_db()
    print("Database tables initialized successfully.")


if __name__ == "__main__":
    asyncio.run(main())
