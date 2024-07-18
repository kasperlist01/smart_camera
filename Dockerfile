# Используем базовый образ Ubuntu
FROM ubuntu:latest

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libopencv-dev \
    python3-opencv \
    python3-venv

# Создаем рабочую директорию
WORKDIR /app

# Копируем файл requirements.txt в контейнер
COPY requirements.txt /app/

# Создаем виртуальное окружение и устанавливаем зависимости
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Копируем исходный код в контейнер
COPY . /app

# Открываем порт, используемый Flask (5003)
EXPOSE 5003

# Запускаем приложение
CMD ["/bin/bash", "-c", ". /app/venv/bin/activate && python app.py"]
