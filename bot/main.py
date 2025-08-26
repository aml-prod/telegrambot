from __future__ import annotations

import io
import os
from typing import Final

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BufferedInputFile, Message

from .config import load_settings
from .image_utils import render_watermark_tiled
from .links import create_link


class Awaiting(StatesGroup):
    caption = State()
    views = State()


router: Final[Router] = Router()


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    await message.answer(
        "✨ Привет!\n\n"
        "Отправь фото, затем текст — я добавлю водяной знак по всей картинке и дам ссылку.\n\n"
        "Можно сразу фото с подписью — подпись станет водяным знаком.\n\n"
        "Доступные команды: /start, /help",
    )


@router.message(F.text == "/help")
async def on_help(message: Message) -> None:
    await message.answer(
        "ℹ️ Помощь\n\n"
        "— Пришли фото без подписи\n"
        "— Затем пришли текст — нанесу водяной знак плиткой\n"
        "— Затем укажи число X — ссылка откроется X раз\n\n"
        "Можно сразу фото с подписью: подпись станет водяным знаком.",
    )


@router.message(F.photo & F.caption)
async def on_photo_with_caption(message: Message, state: FSMContext) -> None:
    largest = message.photo[-1]
    buf = io.BytesIO()
    await message.bot.download(largest, destination=buf)
    await state.update_data(raw_image=buf.getvalue(), text=message.caption or "")
    await state.set_state(Awaiting.views)
    await message.answer("🔢 Сколько открытий ссылки? Укажи число (по умолчанию 3).")


@router.message(F.photo)
async def on_photo(message: Message, state: FSMContext) -> None:
    largest = message.photo[-1]
    buf = io.BytesIO()
    await message.bot.download(largest, destination=buf)
    await state.update_data(raw_image=buf.getvalue())
    await state.set_state(Awaiting.caption)
    await message.answer("✍️ Пришли текст для водяного знака.")


@router.message(StateFilter(Awaiting.caption))
async def on_caption(message: Message, state: FSMContext) -> None:
    await state.update_data(text=message.text or "")
    await state.set_state(Awaiting.views)
    await message.answer("🔢 Сколько открытий ссылки? Укажи число (по умолчанию 3).")


@router.message(StateFilter(Awaiting.views))
async def on_views(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    raw: bytes | None = data.get("raw_image")
    text: str = data.get("text", "")
    if raw is None:
        await state.clear()
        await message.answer("Не нашёл изображение в состоянии. Отправь фото ещё раз, пожалуйста.")
        return

    # Парсим X
    try:
        x = int(message.text.strip()) if message.text else 3
    except Exception:
        x = 3
    if x <= 0:
        x = 1

    # Рендерим водяной знак
    watermarked = render_watermark_tiled(raw, text)

    # Сохраняем файл и создаём токен
    link = create_link(watermarked, x)

    base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080").rstrip("/")
    url = f"{base_url}/v/{link.token}"

    await message.answer_photo(photo=BufferedInputFile(watermarked, filename="result.jpg"))
    await message.answer(
        f"🔗 Ссылка: {url}\n"
        f"Осталось открытий: {x}\n"
        "Подсказка: чтобы дать публичную ссылку с локального ПК — используй cloudflared/ngrok.",
    )
    await state.clear()


@router.message(StateFilter(None))
async def on_text_without_photo(message: Message) -> None:
    if message.text:
        await message.answer("Сначала отправь фото, затем текст и число открытий ✍️")


async def main() -> None:
    settings = load_settings()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    if not settings.webhook_url:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception:
            pass

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать"),
            BotCommand(command="help", description="Помощь"),
        ]
    )

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
