from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import numpy as np
import cv2
import base64
import threading
from queue import Queue
from ultralytics import YOLO
import ssl

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

frame_counter = 0  # Глобальный счетчик кадров
model = YOLO('yolov8n.pt')  # Загружаем модель YOLO здесь
last_results = None  # Последние результаты для рисования рамок

frame_queue = Queue(maxsize=10)  # Очередь для кадров

@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('send_frame')
def handle_frame(data):
    global frame_counter, last_results
    frame_counter += 1

    frame = decode_frame(data)
    if frame is not None:
        frame_queue.put(frame)  # Добавляем кадр в очередь

    if frame_counter % 7 == 0:  # Обрабатываем и отправляем сообщение только для каждого пятнадцатого кадра
        threading.Thread(target=process_frame, args=(frame,)).start()


def process_frame(frame):
    global last_results
    try:
        last_results = model(frame)[0]  # Обработка кадра моделью YOLO
        message = summarize_results(last_results)
        socketio.emit('receive_message', {'message': message})  # Отправляем сообщение о найденных объектах
    except Exception as e:
        print(f"Error processing frame: {e}")
        last_results = None  # Обнуляем результаты в случае ошибки

    while not frame_queue.empty():
        frame = frame_queue.get()
        if last_results:
            frame = draw_boxes(frame, last_results)
        encoded_frame = encode_frame(frame)
        socketio.emit('receive_frame', {'image': encoded_frame})  # Отправляем изображение с рамками


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


def summarize_results(results):
    counts = {}
    class_names = results.names  # Доступ к именам классов
    for result in results.boxes:
        class_name = class_names[int(result.cls)]
        if class_name in counts:
            counts[class_name] += 1
        else:
            counts[class_name] = 1
    return ', '.join([f"{value} {key}(s)" for key, value in counts.items()])


def draw_boxes(frame, results):
    try:
        for result in results.boxes:
            coords = result.xyxy[0].tolist()  # Преобразование тензора в список
            x1, y1, x2, y2 = map(int, coords)
            class_name = results.names[int(result.cls)]
            confidence = float(result.conf)  # Преобразование тензора в скаляр

            # Рисуем прямоугольник
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Подписываем объект
            label = f"{class_name} ({confidence:.2f})"
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame
    except Exception as e:
        print(f"Error drawing boxes: {e}")
        return frame


def encode_frame(frame):
    try:
        _, buffer = cv2.imencode('.jpg', frame)
        return base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        print(f"Error encoding frame: {e}")
        return None


if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    socketio.run(app, allow_unsafe_werkzeug=True, debug=True, host='0.0.0.0', port=5001, ssl_context=context)
