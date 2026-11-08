import asyncio
from saarthi.config import settings
from saarthi.database.engine import AsyncSessionLocal, init_db
from saarthi.database.repository import DisputeRepository


async def main():
    await init_db()
    async with AsyncSessionLocal() as session:
        repo = DisputeRepository(session)
        brands_path = settings.data_dir / "brands.json"
        print(f"Seeding brands from {brands_path}...")
        count = await repo.seed_brands(brands_path)
        print(f"Successfully seeded {count} new brands into SQLite brand_directory.")


if __name__ == "__main__":
    asyncio.run(main())
