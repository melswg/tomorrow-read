FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование всех файлов проекта
COPY . .

# Создание папок для данных
RUN mkdir -p assets/images downloads

# Команда запуска
CMD ["python", "bot.py"]
