# Используем официальный образ Python в качестве базового
FROM python:3.12-slim

# Устанавливаем зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcre3-dev

# Создаем рабочую директорию
WORKDIR /app

# Копируем файлы приложения в контейнер
COPY . /app

# Устанавливаем зависимости приложения
RUN pip install --no-cache-dir -r requirements.txt

# Открываем порт для Flask
EXPOSE 5000

# Запуск приложения Flask
CMD ["python", "app.py"]
