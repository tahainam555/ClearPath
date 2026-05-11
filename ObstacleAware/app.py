"""Flask application entry point for the ObstacleAware web interface.

This module sets up the Flask web server with WebSocket support via Flask-SocketIO.
It manages real-time depth estimation, zone analysis, and alert generation, streaming
live depth maps and obstacle alerts to connected clients.
"""

import cv2
import numpy as np
import base64
import threading
import time
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from depth_estimator import DepthEstimator
from zone_analyzer import ZoneAnalyzer
from alert_engine import AlertEngine


# ============ FLASK APP INITIALIZATION ============

# Create Flask application instance
app = Flask(__name__)
app.config['SECRET_KEY'] = 'obstacle-aware-secret-key'

# Initialize Flask-SocketIO with eventlet as the async mode
# eventlet provides lightweight concurrency for handling multiple WebSocket connections
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")


# ============ GLOBAL OBJECTS ============

# Initialize the three core processing components
print("[App] Initializing depth estimator...")
depth_estimator = DepthEstimator(device="cpu")

print("[App] Initializing zone analyzer...")
zone_analyzer = ZoneAnalyzer(threshold=180)

print("[App] Initializing alert engine...")
alert_engine = AlertEngine()

# Webcam capture object
cap = None

# Background processing thread control
processing_thread = None
thread_running = False
thread_lock = threading.Lock()

# Target frame rate for processing (~8 FPS)
TARGET_FPS = 8
FRAME_INTERVAL = 1.0 / TARGET_FPS


# ============ BACKGROUND PROCESSING THREAD ============

def process_frames():
    """
    Background thread function: continuous depth estimation and zone analysis.
    
    Reads frames from the webcam, runs them through the depth estimation pipeline,
    analyzes zones, generates alerts, and emits results to all connected clients
    via WebSocket events.
    
    This function runs in a separate thread and processes frames at ~8 FPS to
    maintain real-time responsiveness without overwhelming the client or server.
    """
    
    global cap, thread_running
    
    print("[ProcessThread] Started")
    
    try:
        # Initialize webcam capture
        # 0 refers to the default system camera
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("[ProcessThread] ERROR: Failed to open webcam. Ensure camera is connected.")
            thread_running = False
            return
        
        # Configure webcam for optimal performance
        # Set resolution to HD (reduces processing load)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)  # Request 30 FPS from camera
        
        print("[ProcessThread] Webcam initialized successfully")
        
        # Main processing loop
        while thread_running:
            frame_start_time = time.time()
            
            # ============ FRAME CAPTURE ============
            
            # Read frame from webcam
            ret, frame = cap.read()
            
            if not ret:
                print("[ProcessThread] Warning: Failed to read frame from webcam")
                continue
            
            # ============ DEPTH ESTIMATION ============
            
            try:
                # Run depth estimation on the captured frame
                # Returns: colored_depth_map (for display), normalized_depth_array (for analysis)
                colored_depth_map, normalized_depth_array = depth_estimator.predict(frame)
            except Exception as e:
                print(f"[ProcessThread] Error in depth estimation: {e}")
                continue
            
            # ============ ZONE ANALYSIS ============
            
            try:
                # Analyze depth map to get obstacle danger levels in each zone
                zone_result = zone_analyzer.analyze(normalized_depth_array)
            except Exception as e:
                print(f"[ProcessThread] Error in zone analysis: {e}")
                continue
            
            # ============ ALERT GENERATION ============
            
            try:
                # Generate alert message based on zone dangers
                alert_message = alert_engine.get_alert(zone_result)
                
                # Get color codes for UI visualization of zone status
                zone_colors = alert_engine.get_zone_colors(zone_result)
            except Exception as e:
                print(f"[ProcessThread] Error in alert generation: {e}")
                continue
            
            # ============ FRAME ENCODING ============
            
            try:
                # Encode colored depth map as JPEG for transmission
                # JPEG compression reduces bandwidth significantly
                ret, jpeg_buffer = cv2.imencode('.jpg', colored_depth_map)
                
                if not ret:
                    print("[ProcessThread] Warning: Failed to encode depth map as JPEG")
                    continue
                
                # Convert JPEG bytes to base64 string for safe transmission over WebSocket
                # Base64 encoding ensures compatibility with JSON serialization
                jpeg_base64 = base64.b64encode(jpeg_buffer).decode('utf-8')
            except Exception as e:
                print(f"[ProcessThread] Error in frame encoding: {e}")
                continue
            
            # ============ WEBSOCKET EMISSION ============
            
            try:
                # Emit depth frame to all connected clients
                # Event name: "depth_frame"
                # Payload: {"image": base64_encoded_jpeg}
                socketio.emit(
                    'depth_frame',
                    {'image': jpeg_base64},
                    broadcast=True,
                    skip_sid=None
                )
                
                # Emit zone status (danger levels + alert message) to all connected clients
                # Event name: "zone_status"
                # Payload: {
                #   "zones": {"left": "red"|"green", "centre": "red"|"green", "right": "red"|"green"},
                #   "alert": "alert string" or null
                # }
                socketio.emit(
                    'zone_status',
                    {
                        'zones': zone_colors,
                        'alert': alert_message
                    },
                    broadcast=True,
                    skip_sid=None
                )
            except Exception as e:
                print(f"[ProcessThread] Error emitting WebSocket events: {e}")
            
            # ============ FRAME RATE CONTROL ============
            
            # Calculate elapsed time for this frame iteration
            elapsed_time = time.time() - frame_start_time
            
            # Sleep to maintain target FPS (~8 FPS = 125 ms per frame)
            # If processing takes longer than target interval, skip the sleep
            sleep_time = max(0, FRAME_INTERVAL - elapsed_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
        
    except Exception as e:
        print(f"[ProcessThread] Unexpected error: {e}")
    finally:
        # Cleanup: release webcam resource
        if cap is not None:
            cap.release()
            print("[ProcessThread] Webcam released")
        
        thread_running = False
        print("[ProcessThread] Stopped")


# ============ FLASK ROUTES ============

@app.route('/')
def index():
    """
    Serve the main index.html page.
    
    Returns:
        HTML page with WebSocket client code for real-time streaming.
    """
    return render_template('index.html')


@app.route('/settings', methods=['POST'])
def update_settings():
    """
    Update ZoneAnalyzer threshold at runtime.
    
    Accepts JSON POST request with new depth threshold value and updates
    the zone analyzer's danger detection threshold.
    
    Expected JSON payload:
    {
      "threshold": int (0-255)
    }
    
    Returns:
        JSON response: {"status": "ok"} on success
        JSON response: {"status": "error", "message": error_details} on failure
    """
    
    try:
        # Parse JSON request body
        data = request.get_json()
        
        if not data or 'threshold' not in data:
            return jsonify({"status": "error", "message": "Missing 'threshold' field"}), 400
        
        threshold_value = data['threshold']
        
        # Validate threshold is an integer
        if not isinstance(threshold_value, int):
            return jsonify({"status": "error", "message": "Threshold must be an integer"}), 400
        
        # Update the zone analyzer with new threshold
        # This will validate range and update internally
        zone_analyzer.set_threshold(threshold_value)
        
        print(f"[App] Settings updated: threshold = {threshold_value}")
        
        return jsonify({"status": "ok"}), 200
    
    except Exception as e:
        print(f"[App] Error in /settings endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============ SOCKETIO EVENT HANDLERS ============

@socketio.on('connect')
def handle_connect():
    """
    Handle WebSocket client connection.
    
    When a client connects, start the background processing thread if not
    already running. Multiple connections share the same thread to avoid
    redundant processing.
    """
    
    global processing_thread, thread_running
    
    print("[SocketIO] Client connected")
    
    # Use lock to ensure thread-safe access to thread control variables
    with thread_lock:
        # Only start thread if it's not already running
        if not thread_running:
            thread_running = True
            
            # Create and start the background processing thread
            # daemon=True means thread will terminate when main program exits
            processing_thread = threading.Thread(target=process_frames, daemon=True)
            processing_thread.start()
            
            print("[SocketIO] Background processing thread started")
        else:
            print("[SocketIO] Background processing thread already running")


@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle WebSocket client disconnection.
    
    Currently just logs the disconnection. Thread continues running to serve
    other connected clients. If no clients remain after a timeout, the thread
    could be optimized to stop (not implemented in this basic version).
    """
    print("[SocketIO] Client disconnected")


# ============ ENTRY POINT ============

if __name__ == '__main__':
    print("[App] Starting ObstacleAware Flask server...")
    print("[App] Access the app at: http://localhost:5000 or http://<your-ip>:5000")
    
    # Run the Flask-SocketIO server
    # host="0.0.0.0" allows connections from any network interface (mobile/remote)
    # port=5000 is the standard Flask development port
    # debug=False for production-like behavior
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
