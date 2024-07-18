from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import base64
import os
import random
import ssl
import numpy as np
import cv2
from ultralytics import YOLO
from queue import Queue
from threading import Thread

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")
CORS(app)
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('cert.pem', 'key.pem')

model = YOLO('yolov8n.pt')  # Загружаем модель YOLO
frame_counter = 0  # Глобальный счетчик кадров
object_coords = []  # Список для хранения координат объектов
frame_queue = Queue()  # Очередь кадров для обработки


def frame_processor():
    while True:
        frame_data = frame_queue.get()
        if frame_data is None:
            break  # Завершаем поток, если получен None
        handle_frame(frame_data)


@app.route('/')
def index():
    dice_roll = random.randint(1, 6)  # Генерация случайного числа от 1 до 6
    return render_template('index.html', dice_roll=dice_roll)


@socketio.on('send_frame')
def handle_frame_socket(data):
    frame_queue.put(data)  # Добавляем кадр в очередь для обработки


def handle_frame(data):
    global frame_counter
    print("Frame received")
    frame_counter += 1
    try:
        processed_image = process_frame(data)
        socketio.emit('receive_frame', {'image': processed_image}, namespace='/')
        print("Processed frame sent back to client")
    except Exception as e:
        print(f"Error processing frame: {e}")


def process_frame(data):
    global frame_counter, object_coords
    try:
        image_cv = decode_frame(data)
        if image_cv is None:
            raise ValueError("Failed to decode frame")

        if frame_counter % 10 == 0:  # Каждый 10-й кадр
            object_coords = detect_objects(image_cv)
            print(f"Detected objects: {object_coords}")
        image_cv = draw_boxes(image_cv, object_coords)
        return encode_image(image_cv)
    except Exception as e:
        print(f"Error in process_frame: {e}")
        raise


def decode_frame(data):
    try:
        if not data:
            print("Received empty frame data")
            return None

        frame_data = base64.b64decode(data)
        buffer_array = np.frombuffer(frame_data, np.uint8)

        if buffer_array.size == 0:
            print("Buffer array is empty")
            return None

        frame = cv2.imdecode(buffer_array, cv2.IMREAD_COLOR)

        if frame is None:
            print("Failed to decode frame")

        return frame
    except Exception as e:
        print(f"Error decoding frame: {e}")
        return None


def detect_objects(image):
    try:
        results = model(image)[0]
        coords = []
        for result in results.boxes:
            coords.append({
                "coords": result.xyxy[0].tolist(),
                "class_name": results.names[int(result.cls)],
                "confidence": float(result.conf)
            })
        print(f"Detected coordinates: {coords}")
        return coords
    except Exception as e:
        print(f"Error in detect_objects: {e}")
        return []


def draw_boxes(image, object_coords):
    try:
        for obj in object_coords:
            coords = obj["coords"]
            x1, y1, x2, y2 = map(int, coords)
            class_name = obj["class_name"]
            confidence = obj["confidence"]

            # Рисуем прямоугольник
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Подписываем объект
            label = f"{class_name} ({confidence:.2f})"
            cv2.putText(image, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        print(f"Boxes drawn: {len(object_coords)}")
        return image
    except Exception as e:
        print(f"Error drawing boxes: {e}")
        return image


def encode_image(image):
    try:
        _, buffer = cv2.imencode('.jpg', image)
        return base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {e}")
        raise


if __name__ == '__main__':
    processor_thread = Thread(target=frame_processor)
    processor_thread.start()
    socketio.run(app, allow_unsafe_werkzeug=True, host='0.0.0.0', port=5003, debug=True, ssl_context=ssl_context)
