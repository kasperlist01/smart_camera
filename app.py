from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from PIL import Image, ImageDraw
import base64
import io
import os

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

basedir = os.path.abspath(os.path.dirname(__file__))


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('send_frame')
def handle_frame(data):
    try:
        processed_image = process_frame(data)
        emit('receive_frame', {'image': processed_image})
    except Exception as e:
        print(f"Error processing frame: {e}")


def process_frame(data):
    try:
        image = decode_image(data)
        image = draw_rectangle(image)
        return encode_image(image)
    except Exception as e:
        print(f"Error in process_frame: {e}")
        raise


def decode_image(data):
    try:
        image_data = base64.b64decode(data)
        return Image.open(io.BytesIO(image_data))
    except Exception as e:
        print(f"Error decoding image: {e}")
        raise


def draw_rectangle(image):
    try:
        draw = ImageDraw.Draw(image)
        width, height = image.size
        rectangle_specs = (width // 4, height // 4, width * 3 // 4, height * 3 // 4)
        draw.rectangle(rectangle_specs, outline="red", width=10)
        return image
    except Exception as e:
        print(f"Error drawing rectangle: {e}")
        raise


def encode_image(image):
    try:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=95)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {e}")
        raise


if __name__ == '__main__':
    socketio.run(app, allow_unsafe_werkzeug=True, debug=True, host='0.0.0.0', port=5000)
