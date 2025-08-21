# Telegram Photo+Caption Bot (aiogram 3)

## Быстрый старт (Windows PowerShell)

1. Установи Python 3.11+ с добавлением в PATH.
2. Создай и активируй виртуальное окружение:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Поставь зависимости:
   ```powershell
   pip install -r requirements.txt
   ```
4. Создай `.env` и укажи `BOT_TOKEN`:
   ```powershell
   copy .env.example .env
   notepad .env
   ```
5. Запусти бота:
   ```powershell
   python -m bot
   ```

## Что делает бот
- Принимает фото и текст, рисует текст снизу изображения на полупрозрачной плашке и отправляет обратно одно изображение.
- Если прислать фото с подписью сразу — бот сразу вернёт фото с нарисованной подписью.

## Сборка exe (PyInstaller)
1. Установи зависимости (см. выше) и активируй venv.
2. Собери onefile-экзешник:
   ```powershell
   pyinstaller --onefile --noconfirm --name photo_caption_bot run_bot.py
   ```
3. Положи рядом с `dist\photo_caption_bot.exe` файл `.env` с `BOT_TOKEN=...` (либо помести `.env` в корень проекта — загрузка поддерживается и там).
4. Запуск:
   ```powershell
   .\dist\photo_caption_bot.exe
   ```

## Разработка
- Линтер: Ruff (`pyproject.toml`).
- Изображения: Pillow.
- Проверка линтов:
  ```powershell
  ruff check .
  ```
