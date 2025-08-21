from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    webhook_url: str = ""


def _try_load_env_from(path: Path) -> None:
    env_path = path / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def load_settings() -> Settings:
    """Загружает конфигурацию из .env и окружения.

    Пытается загрузить .env из текущей директории, затем — из директории исполняемого файла
    (при сборке PyInstaller), затем — из корня проекта (рядом с пакетом bot). Если не найдено,
    использует вшитое значение из bot/_embedded_env.py (если файл сгенерирован).
    """
    # 1) Обычная загрузка из текущей папки
    load_dotenv()

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        # 2) Если frozen, попробуем папку исполняемого файла
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            _try_load_env_from(exe_dir)
            token = os.getenv("BOT_TOKEN", "").strip()

    if not token:
        # 3) Попробуем корень проекта (на один уровень выше пакета bot)
        project_root = Path(__file__).resolve().parent.parent
        _try_load_env_from(project_root)
        token = os.getenv("BOT_TOKEN", "").strip()

    if not token:
        # 4) Fallback: вшитое значение (если сгенерирован bot/_embedded_env.py)
        try:
            from ._embedded_env import EMBEDDED_BOT_TOKEN  # type: ignore
        except Exception:
            EMBEDDED_BOT_TOKEN = ""  # type: ignore
        if EMBEDDED_BOT_TOKEN:
            token = EMBEDDED_BOT_TOKEN.strip()

    if not token:
        raise RuntimeError("Переменная окружения BOT_TOKEN не задана. Укажи её в .env")

    # Загружаем URL webhook (опционально)
    webhook_url = os.getenv("WEBHOOK_URL", "").strip()

    return Settings(bot_token=token, webhook_url=webhook_url)
