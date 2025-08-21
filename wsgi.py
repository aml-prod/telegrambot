"""
WSGI точка входа для PythonAnywhere.
Используется для запуска Flask-приложения с Telegram webhook.
"""

from bot.flask_app import flask_app

# PythonAnywhere ищет переменную application
application = flask_app

if __name__ == "__main__":
    # Для локального тестирования
    flask_app.run(debug=True, port=5000)
