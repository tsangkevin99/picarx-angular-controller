import asyncio
import json
import threading
from flask import Flask, Response
from picarx import Picarx
import websockets
from picamera2 import Picamera2
import cv2
import time

# ----------------------
# Initialize PiCar-X and camera
# ----------------------
car = Picarx()
picam2 = Picamera2()
picam2.start()

# Driving mode: "manual" or "auto"
mode = "manual"

# PID constants (for future use)
Kp, Ki, Kd = 0.5, 0.0, 0.1
pid_integral = 0
pid_last_error = 0
pid_last_time = time.time()

# Head angles
pan_angle = 0
tilt_angle = 0

# Default camera positions
DEFAULT_PAN = -0.5
DEFAULT_TILT = 7.5

car.set_cam_pan_angle(DEFAULT_PAN)
car.set_cam_tilt_angle(DEFAULT_TILT)

# Track previous button state for rising-edge detection
prev_button_x = False

# ----------------------
# Flask app for video feed
# ----------------------
app = Flask(__name__)

def get_camera_frame():
    return picam2.capture_array()

def get_camera_frame_bytes():
    frame = get_camera_frame()
    ret, jpeg = cv2.imencode('.jpg', frame)
    return jpeg.tobytes()

def generate_video_stream():
    while True:
        frame = get_camera_frame_bytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_video_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# ----------------------
# Manual driving
# ----------------------
def drive_manual(throttle, steer, rx, ry, reset_head=False):
    global pan_angle, tilt_angle

    if reset_head:
        pan_angle = DEFAULT_PAN
        tilt_angle = DEFAULT_TILT

    # Car driving
    servo_val = steer * 35  # -35° to +35°
    speed_val = int(throttle * 100)
    car.set_dir_servo_angle(servo_val)
    car.set_motor_speed(1, speed_val)
    car.set_motor_speed(2, -speed_val)

    # Camera pan/tilt
    step = 0.5
    if rx > 0.5:
        pan_angle = min(pan_angle + step, 35)
    elif rx < -0.5:
        pan_angle = max(pan_angle - step, -35)

    if ry > 0.5:
        tilt_angle = min(tilt_angle - step, 35)
    elif ry < -0.5:
        tilt_angle = max(tilt_angle + step, -35)

    car.set_cam_pan_angle(pan_angle)
    car.set_cam_tilt_angle(tilt_angle)

# ----------------------
# Auto driving (placeholder)
# ----------------------
def drive_auto():
    # For now, just go straight
    car.set_dir_servo_angle(0)
    car.forward(50)

# ----------------------
# WebSocket handler
# ----------------------
async def handler(websocket):
    global mode, prev_button_x

    print("Client connected")
    try:
        async for message in websocket:
            data = json.loads(message)

            # Read controls
            throttle = max(-1, min(data.get("throttle", 0), 1))
            steer = max(-1, min(data.get("steer", 0), 1))
            rx = data.get("rx", 0)
            ry = data.get("ry", 0)

            # Buttons
            button_x = data.get("button_x", False)
            button_y = data.get("button_y", False)

            # Toggle mode on X button rising edge
            if button_x and not prev_button_x:
                mode = "auto" if mode == "manual" else "manual"
                print(f"Switched to {mode.upper()} mode")
            prev_button_x = button_x
            # Check for toggle from front-end button
            if data.get("toggle_mode", False):
                mode = "auto" if mode == "manual" else "manual"
                print(f"Switched to {mode.upper()} mode")


            # Reset camera if Y pressed
            reset_head = button_y

            # Drive
            if mode == "manual":
                drive_manual(throttle, steer, rx, ry, reset_head)
            elif mode == "auto":
                drive_auto()

    except Exception as e:
        print("Connection handler failed:", e)
        car.stop()

# ----------------------
# WebSocket server
# ----------------------
async def ws_main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Starting PiCar-X WebSocket server on port 8765")
        await asyncio.Future()  # run forever

# ----------------------
# Run Flask in a thread
# ----------------------
def run_flask():
    app.run(host='0.0.0.0', port=9000, threaded=True)

# ----------------------
# Main
# ----------------------
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    asyncio.run(ws_main())
