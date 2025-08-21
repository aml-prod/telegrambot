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

## Запуск на PythonAnywhere

### Вариант 1: Веб-приложение (Flask + Webhook) - РЕКОМЕНДУЕТСЯ

#### 1. Загрузка файлов
Скачай ZIP-архив проекта и загрузи через **Files** → **Upload a file**, либо через git:
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/telegram-bot.git telegram_bot
cd telegram_bot
```

#### 2. Установка зависимостей
Открой **Consoles** → **Bash** и выполни:
```bash
cd ~/telegram_bot
pip install --user -r requirements.txt
```

#### 3. Настройка токена и webhook
Создай файл `.env`:
```bash
nano .env
```
Добавь строки:
```
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
WEBHOOK_URL=https://yourusername.pythonanywhere.com
```
Замени `yourusername` на своё имя пользователя PythonAnywhere.

#### 4. Создание веб-приложения
1. **Web** → **Add a new web app**
2. **Python 3.10** → **Manual configuration**
3. **Source code**: `/home/yourusername/telegram_bot`
4. **WSGI configuration file**: отредактируй `/var/www/yourusername_pythonanywhere_com_wsgi.py`:

```python
import sys
import os

# Добавляем путь к проекту
path = '/home/yourusername/telegram_bot'
if path not in sys.path:
    sys.path.insert(0, path)

# Устанавливаем переменные окружения
os.chdir(path)

from wsgi import application
```

5. **Reload** веб-приложения.

#### 5. Проверка
- Открой `https://yourusername.pythonanywhere.com` — должно показать `{"status": "OK"}`
- Webhook автоматически настроится при первом запуске

### Вариант 2: Консольное приложение (Polling)

#### 1-2. Загрузка и установка (как в варианте 1)

#### 3. Настройка токена
```bash
nano .env
```
Добавь только:
```
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

#### 4. Тестовый запуск
```bash
python -m bot
```

#### 5. Постоянный запуск
**Платные аккаунты:**
- **Tasks** → **Always-On Tasks**: `python3.10 -m bot`

**Бесплатные аккаунты:**
- **Scheduled Tasks** каждые 5 минут: 
  ```bash
  cd /home/yourusername/telegram_bot && timeout 290 python3.10 -m bot
  ```

### Мониторинг и отладка
```bash
# Логи веб-приложения
tail -f /var/log/yourusername.pythonanywhere.com.error.log

# Логи консольного приложения  
tail -f ~/telegram_bot/bot.log

# Проверка процессов
ps aux | grep python
```

### Особенности PythonAnywhere
- **Webhook (рекомендуется)**: не расходует CPU время, мгновенный отклик
- **Polling**: расходует CPU, подходит для тестирования
- Бесплатный аккаунт: 100 секунд CPU/день, 1 веб-приложение
- Исходящие соединения к api.telegram.org разрешены

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
