FROM python:3.11-slim

# Установка рабочей директории
WORKDIR /app

# Переменная окружения для детекции запуска внутри Docker
ENV IS_DOCKER=true

# Установка системных библиотек, необходимых для компиляции некоторых пакетов при необходимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода проекта
COPY . .

# По умолчанию запускаем бота по рекламе, 
# но в docker-compose переопределим команду запуска
CMD ["python", "main_adv.py"]
