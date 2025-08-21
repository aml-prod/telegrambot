from __future__ import annotations

import io
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
from .image_utils import render_text_on_image_bottom


class Awaiting(StatesGroup):
    caption = State()


router: Final[Router] = Router()


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    await message.answer(
        "✨ Привет!\n\n"
        "1) Отправь мне фото без подписи\n"
        "2) Затем пришли текст — я верну это же фото с подписью внутри изображения.\n\n"
        "Можно сразу фото с подписью — я нарисую подпись внизу картинки.\n\n"
        "Доступные команды: /start, /help",
    )


@router.message(F.text == "/help")
async def on_help(message: Message) -> None:
    await message.answer(
        "ℹ️ Помощь\n\n"
        "— Пришли фото без подписи\n"
        "— Затем пришли текст — я пришлю то же фото с подписью на нём\n\n"
        "Можно сразу фото с подписью: я нарисую её внизу.",
    )


@router.message(F.photo & F.caption)
async def on_photo_with_caption(message: Message) -> None:
    largest = message.photo[-1]
    buf = io.BytesIO()
    await message.bot.download(largest, destination=buf)
    result = render_text_on_image_bottom(buf.getvalue(), message.caption or "")
    await message.answer_photo(photo=BufferedInputFile(result, filename="result.jpg"))


@router.message(F.photo)
async def on_photo(message: Message, state: FSMContext) -> None:
    largest = message.photo[-1]
    await state.update_data(photo_file_id=largest.file_id)
    await state.set_state(Awaiting.caption)
    await message.answer(
        "📸 Фото получил! Теперь пришли текст — я нарисую его снизу изображения.",
    )


@router.message(StateFilter(Awaiting.caption))
async def on_any_message_in_caption_state(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    file_id = data.get("photo_file_id")
    if not file_id:
        await state.clear()
        await message.answer("Не нашёл фото в состоянии. Отправь фото ещё раз, пожалуйста.")
        return

    if not message.text:
        await message.answer("Нужен текст для подписи. Пришли текст, пожалуйста ✍️")
        return

    # Скачиваем фото по file_id
    file = await message.bot.get_file(file_id)
    buf = io.BytesIO()
    await message.bot.download(file, destination=buf)

    result = render_text_on_image_bottom(buf.getvalue(), message.text)
    await message.answer_photo(photo=BufferedInputFile(result, filename="result.jpg"))
    await state.clear()


@router.message(StateFilter(None))
async def on_text_without_photo(message: Message) -> None:
    if message.text:
        await message.answer("Сначала отправь фото, затем текст для подписи ✍️")


async def main() -> None:
    settings = load_settings()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

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
