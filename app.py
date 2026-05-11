"""
Flask + SocketIO server for ObstacleAware.

Streams depth visualizations and zone/alert status to connected clients.
"""
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import threading
import base64
import cv2

from depth_estimator import DepthEstimator
from zone_analyzer import analyze_zones
from alert_engine import generate_alert
from flask import request
import numpy as np
import cv2
import base64

# App setup
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Core components and state
estimator = DepthEstimator()
danger_threshold = 180

camera = None
camera_lock = threading.Lock()
bg_thread = None
stop_thread = False
clients = 0


def camera_loop():
    """Background capture loop: read frames, run model, emit to clients."""
    global camera, stop_thread, danger_threshold

    with camera_lock:
        if camera is None:
            camera = cv2.VideoCapture(0)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while not stop_thread:
        with camera_lock:
            if camera is None:
                break
            ret, frame = camera.read()

        if not ret:
            socketio.sleep(0.1)
            continue

        try:
            depth_gray, vis_bgr = estimator.estimate(frame)
            zones = analyze_zones(depth_gray, threshold=danger_threshold)
            alert_msg = generate_alert(zones)

            # Encode visualization as JPEG->base64
            _, buf = cv2.imencode('.jpg', vis_bgr)
            b64 = base64.b64encode(buf).decode('ascii')
            data_url = 'data:image/jpeg;base64,' + b64

            socketio.emit('frame', {'image': data_url})
            socketio.emit('zones', zones)
            socketio.emit('alert', {'message': alert_msg})

        except Exception as e:
            print('Error processing frame:', e)

        # small sleep to cap CPU usage (~6-8 FPS)
        socketio.sleep(0.15)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/settings', methods=['POST'])
def settings():
    global danger_threshold
    data = request.get_json() or request.form
    try:
        t = int(data.get('threshold'))
        t = max(0, min(255, t))
        danger_threshold = t
        return jsonify({'status': 'ok', 'threshold': danger_threshold})
    except Exception:
        return jsonify({'status': 'error', 'message': 'invalid threshold'}), 400


@app.route('/upload', methods=['POST'])
def upload_image():
    """Accept an uploaded image file, run depth estimation and return results.

    Expects multipart/form-data with field 'image'. Returns JSON:
      {image: data_url, zones: {...}, alert: str|null}
    """
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'no image provided'}), 400

    file = request.files['image']
    data = file.read()
    # Convert bytes to numpy array then to OpenCV BGR image
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({'status': 'error', 'message': 'invalid image'}), 400

    try:
        depth_gray, vis_bgr = estimator.estimate(img)
        zones = analyze_zones(depth_gray, threshold=danger_threshold)
        alert_msg = generate_alert(zones)

        _, buf = cv2.imencode('.jpg', vis_bgr)
        b64 = base64.b64encode(buf).decode('ascii')
        data_url = 'data:image/jpeg;base64,' + b64

        return jsonify({'status': 'ok', 'image': data_url, 'zones': zones, 'alert': alert_msg})
    except Exception as e:
        print('Upload processing error:', e)
        return jsonify({'status': 'error', 'message': 'processing failed'}), 500


@socketio.on('connect')
def on_connect():
    global bg_thread, clients, stop_thread
    clients += 1
    if bg_thread is None:
        stop_thread = False
        bg_thread = socketio.start_background_task(camera_loop)
    print('Client connected, total:', clients)


@socketio.on('disconnect')
def on_disconnect():
    global clients, camera, stop_thread, bg_thread
    clients = max(0, clients - 1)
    print('Client disconnected, total:', clients)
    if clients == 0:
        stop_thread = True
        with camera_lock:
            if camera is not None:
                try:
                    camera.release()
                except Exception:
                    pass
                camera = None
        bg_thread = None


if __name__ == '__main__':
    print('Starting ObstacleAware at http://0.0.0.0:5000')
    socketio.run(app, host='0.0.0.0', port=5000)
