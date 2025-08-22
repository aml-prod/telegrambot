from __future__ import annotations

import asyncio
import logging
import threading
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, Update
from flask import Flask, request

from .config import load_settings
from .main import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None

# Один общий event loop в отдельном потоке
bg_loop = asyncio.new_event_loop()
_ready = threading.Event()


def _loop_thread() -> None:
    asyncio.set_event_loop(bg_loop)
    bg_loop.run_forever()


threading.Thread(target=_loop_thread, name="aiogram-loop", daemon=True).start()


async def _async_setup() -> None:
    global bot, dp
    settings = load_settings()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # локальная инициализация
    await dp.emit_startup(bot)

    # Сразу считаем приложение готовым (исключаем зависания на сетевых вызовах)
    _ready.set()
    logger.info("Bot initialized (ready)")

    # Сетевые операции НЕ блокируют готовность
    try:
        asyncio.create_task(
            bot.set_my_commands(
                [
                    BotCommand(command="start", description="Начать"),
                    BotCommand(command="help", description="Помощь"),
                ]
            )
        )
    except Exception as e:
        logger.warning("set_my_commands scheduled with error: %s", e)


# Инициализация бота в фоновом loop
asyncio.run_coroutine_threadsafe(_async_setup(), bg_loop)


def create_flask_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def health() -> dict[str, str]:
        return {
            "status": "ready" if _ready.is_set() else "initializing",
            "message": "Telegram Photo Caption Bot is running",
        }

    @app.post("/webhook")
    def webhook() -> tuple[str, int]:
        # Всегда быстрое 200 — Telegram не будет ждать 60 сек и ставить 499
        if not _ready.is_set() or bot is None or dp is None:
            logger.warning("Webhook hit while not ready")
            return "OK", 200

        payload = request.get_json(silent=True)
        if not payload:
            return "OK", 200

        try:
            update = Update.model_validate(payload)
        except Exception as e:
            logger.exception("Update validation error: %s", e)
            return "OK", 200

        try:
            fut = asyncio.run_coroutine_threadsafe(dp.feed_update(bot, update), bg_loop)

            def _cb(f) -> None:
                exc = f.exception()
                if exc:
                    logger.exception("feed_update error: %s", exc)

            fut.add_done_callback(_cb)
        except Exception as e:
            logger.exception("Scheduling error: %s", e)

        return "OK", 200

    return app


flask_app = create_flask_app()