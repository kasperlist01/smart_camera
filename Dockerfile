# Используем минимальный базовый образ
FROM python:3.10-slim-buster

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    gcc \
    g++ \
    python3-dev \
    python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файл requirements.txt в контейнер
COPY requirements.txt /app/

# Устанавливаем зависимости из файла requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копируем исходный код в контейнер
COPY . /app

# Открываем порт, используемый Flask (5003)
EXPOSE 5003

# Запускаем приложение
CMD ["python", "app.py"]
