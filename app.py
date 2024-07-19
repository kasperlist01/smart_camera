from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import base64
import ssl
import numpy as np
import cv2
from ultralytics import YOLO
from queue import Queue
from threading import Thread
from translations import translations  # Импортируем словарь переводов

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")
CORS(app)
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('cert.pem', 'key.pem')

# Загружаем модели YOLO
model_1 = YOLO('./train5_n_60/weights/best.pt')
model_2 = YOLO('yolov8n.pt')
frame_counters = {}  # Глобальный счетчик кадров для каждого клиента
object_coords = {}  # Словарь для хранения координат объектов для каждого пользователя
frame_queues = {}  # Словарь очередей кадров для каждого пользователя
model_types = {}  # Словарь для хранения типа модели для каждого пользователя


def frame_processor(socket_id):
    while True:
        frame_data = frame_queues[socket_id].get()
        if frame_data is None:
            break  # Завершаем поток, если получен None
        if isinstance(frame_data, tuple) and frame_data[0] == 'set_model':
            model_types[socket_id] = frame_data[1]
            print(f"Model type for {socket_id} set to {model_types[socket_id]}")
        else:
            handle_frame(socket_id, frame_data)


# Маршрут для отдачи файла манифеста
@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def handle_connect(auth):
    socket_id = request.sid
    print(f"Client connected: {socket_id}")
    frame_queues[socket_id] = Queue()
    object_coords[socket_id] = []
    frame_counters[socket_id] = 0  # Инициализируем счетчик кадров для клиента
    model_types[socket_id] = 'model_1'  # По умолчанию выбираем модель 1
    processor_thread = Thread(target=frame_processor, args=(socket_id,))
    processor_thread.start()


@socketio.on('disconnect')
def handle_disconnect(auth):
    socket_id = request.sid
    print(f"Client disconnected: {socket_id}")
    frame_queues[socket_id].put(None)
    del frame_queues[socket_id]
    del object_coords[socket_id]
    del frame_counters[socket_id]
    del model_types[socket_id]


@socketio.on('send_frame')
def handle_frame_socket(data):
    socket_id = request.sid
    frame_queues[socket_id].put(data)


@socketio.on('set_model')
def set_model_socket(data):
    socket_id = request.sid
    model_type = data.get('model_type', 'model_1')
    frame_queues[socket_id].put(('set_model', model_type))


def handle_frame(socket_id, data):
    frame_counters[socket_id] += 1
    try:
        processed_image, detections = process_frame(socket_id, data, model_types[socket_id])
        filtered_detections = [d for d in detections if d['confidence'] >= 0.4]
        socketio.emit('receive_frame', {'image': processed_image, 'detections': filtered_detections}, to=socket_id)
        print(f"Processed frame sent back to client {socket_id}")
    except Exception as e:
        print(f"Error processing frame: {e}")


def process_frame(socket_id, data, model_type):
    try:
        image_cv = decode_frame(data)
        if image_cv is None:
            raise ValueError("Failed to decode frame")

        detections = []
        if frame_counters[socket_id] % 10 == 0:  # Каждый 10-й кадр
            detections = detect_objects(image_cv, model_type)
            object_coords[socket_id] = detections
            print(f"Detected objects for {socket_id}: {object_coords[socket_id]}")
        image_cv = draw_boxes(image_cv, object_coords[socket_id])
        return encode_image(image_cv), detections
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


def detect_objects(image, model_type):
    try:
        model = model_1 if model_type == 'model_1' else model_2
        results = model(image)[0]
        coords = []
        for result in results.boxes:
            class_name = results.names[int(result.cls)]
            translated_class_name = translations.get(class_name, class_name).capitalize()
            coords.append({
                "coords": result.xyxy[0].tolist(),
                "class_name": class_name,
                "translated_class_name": translated_class_name,
                "confidence": float(result.conf)
            })
        print(f"Detected coordinates: {coords}")
        return coords
    except Exception as e:
        print(f"Error in detect_objects: {e}")
        return []


def draw_boxes(image, object_coords):
    try:
        font_scale = 0.5  # Масштаб шрифта
        thickness = 1  # Толщина линии
        font = cv2.FONT_HERSHEY_COMPLEX  # Выбор шрифта

        for obj in object_coords:
            if obj["confidence"] < 0.4:  # Пропускаем объекты с низкой вероятностью
                continue

            coords = obj["coords"]
            x1, y1, x2, y2 = map(int, coords)
            class_name = obj["translated_class_name"]
            confidence = obj["confidence"]

            # Рисуем прямоугольник
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Рендерим текст
            label = f"{class_name} ({confidence:.2f})"
            text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
            text_x = x1
            text_y = y1 - 10

            # Позиционируем текст выше прямоугольника, проверяем, чтобы текст не вышел за верхний край изображения
            if text_y < 0:
                text_y = y1 + 20  # Если мало места сверху, ставим текст под прямоугольником

            # Рисуем фон для текста, чтобы улучшить читаемость
            cv2.rectangle(image, (text_x, text_y - text_size[1] - 4), (text_x + text_size[0], text_y), (255, 255, 255),
                          -1)

            # Добавляем текст на изображение
            cv2.putText(image, label, (text_x, text_y - 2), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)

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
    socketio.run(app, allow_unsafe_werkzeug=True, host='0.0.0.0', port=5003, debug=True, ssl_context=ssl_context)
