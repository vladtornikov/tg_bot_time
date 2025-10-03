"""Main bot application entry point."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config.settings import get_settings
from database.connection import async_engine
from models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(dp: Dispatcher) -> AsyncGenerator[None, None]:
    """Bot lifespan manager."""
    # Startup
    logger.info("Starting Telegram bot...")
    
    # Create database tables if they don't exist
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created/verified")
    
    # Set webhook if configured
    if settings.telegram_webhook_url:
        await dp.bot.set_webhook(
            url=settings.telegram_webhook_url,
            secret_token=settings.telegram_webhook_secret,
        )
        logger.info(f"Webhook set to: {settings.telegram_webhook_url}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Telegram bot...")
    
    # Remove webhook
    if settings.telegram_webhook_url:
        await dp.bot.delete_webhook()
        logger.info("Webhook removed")
    
    # Close database connections
    await async_engine.dispose()
    logger.info("Database connections closed")


async def create_bot() -> tuple[Bot, Dispatcher]:
    """Create and configure bot instance."""
    # Create bot with default properties
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        ),
    )
    
    # Create dispatcher with memory storage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Set lifespan
    dp["lifespan"] = lifespan(dp)
    
    # Register handlers
    from bot.handlers import commands, callbacks
    from bot.handlers.middlewares import AuthMiddleware, LoggingMiddleware, ErrorHandlerMiddleware
    
    # Add middlewares
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.message.middleware(ErrorHandlerMiddleware())
    
    dp.callback_query.middleware(LoggingMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.callback_query.middleware(ErrorHandlerMiddleware())
    
    # Register handlers
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    
    return bot, dp


async def main():
    """Main bot application."""
    bot, dp = await create_bot()
    
    try:
        if settings.telegram_webhook_url:
            # Webhook mode
            from aiohttp import web
            
            app = web.Application()
            
            # Setup webhook handler
            webhook_requests_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
                secret_token=settings.telegram_webhook_secret,
            )
            webhook_requests_handler.register(app, path="/webhook")
            
            # Setup application
            setup_application(app, dp, bot=bot)
            
            # Start webhook server
            runner = web.AppRunner(app)
            await runner.setup()
            
            site = web.TCPSite(runner, settings.bot_host, settings.bot_port)
            await site.start()
            
            logger.info(f"Bot webhook server started on {settings.bot_host}:{settings.bot_port}")
            
            # Keep running
            await asyncio.Future()  # Run forever
            
        else:
            # Polling mode
            logger.info("Starting bot in polling mode...")
            await dp.start_polling(bot)
    
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
