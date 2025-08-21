from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from flask import Flask, request

from .config import load_settings
from .main import router


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Глобальные переменные для бота
bot: Bot | None = None
dp: Dispatcher | None = None


def create_flask_app() -> Flask:
    """Создаёт Flask-приложение с webhook для Telegram бота."""
    app = Flask(__name__)
    
    @app.route("/", methods=["GET"])
    def health_check() -> dict[str, str]:
        """Проверка здоровья приложения."""
        return {"status": "OK", "message": "Telegram Photo Caption Bot is running"}
    
    @app.route("/webhook", methods=["POST"])
    def webhook() -> tuple[str, int]:
        """Обработчик webhook от Telegram."""
        if not bot or not dp:
            logger.error("Bot or dispatcher not initialized")
            return "Bot not ready", 500
            
        try:
            # Получаем данные от Telegram
            update_data = request.get_json()
            if not update_data:
                return "No data", 400
                
            # Создаём объект Update
            update = Update(**update_data)
            
            # Обрабатываем update асинхронно
            asyncio.create_task(dp.feed_update(bot, update))
            
            return "OK", 200
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return "Error", 500
    
    return app


async def setup_bot() -> None:
    """Инициализация бота и диспетчера."""
    global bot, dp
    
    settings = load_settings()
    
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    # Устанавливаем webhook, если указан URL
    webhook_url = getattr(settings, 'webhook_url', None)
    if webhook_url:
        await bot.set_webhook(
            url=f"{webhook_url}/webhook",
            allowed_updates=dp.resolve_used_update_types(),
        )
        logger.info(f"Webhook set to: {webhook_url}/webhook")
    
    # Устанавливаем команды бота
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать"),
        BotCommand(command="help", description="Помощь"),
    ])
    
    logger.info("Bot initialized successfully")


# Создаём Flask приложение
flask_app = create_flask_app()


def run_setup() -> None:
    """Запускает инициализацию бота в новом event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(setup_bot())
    finally:
        loop.close()


# Инициализируем бота при импорте модуля
try:
    run_setup()
except Exception as e:
    logger.error(f"Failed to initialize bot: {e}")
