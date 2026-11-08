import asyncio
import logging
import sys

from saarthi.config import settings
from saarthi.database.engine import init_db, AsyncSessionLocal
from saarthi.database.repository import DisputeRepository
from saarthi.documents.pdf_generator import register_fonts
from saarthi.telegram.bot import create_bot_and_dispatcher
from saarthi.logging_config import configure_logging
from loguru import logger

# Initialize central logging configuration with sinks and redaction
configure_logging()


async def main():
    logger.info(f"Starting {settings.app_name} (Environment: {settings.app_env})")

    # 1. Initialize SQLite Database
    logger.info("Initializing SQLite database tables...")
    await init_db()

    # 2. Seed Brand Directory if needed
    brands_json = settings.data_dir / "brands.json"
    if brands_json.exists():
        async with AsyncSessionLocal() as session:
            repo = DisputeRepository(session)
            count = await repo.seed_brands(brands_json)
            if count > 0:
                logger.info(f"Seeded {count} brands into SQLite directory.")

    # 3. Register PDF Fonts
    register_fonts()
    logger.info("Unicode TrueType fonts registered for PDF generation.")

    # 4. Initialize Telegram Bot
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment or .env. Exiting.")
        sys.exit(1)

    bot, dp = create_bot_and_dispatcher()
    logger.info("Starting Telegram Bot polling...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application shut down cleanly.")
