import asyncio
import json
import threading
from flask import Flask, Response
from picarx import Picarx
import websockets
from picamera2 import Picamera2
import cv2
import time

# Initialize PiCar-X and camera
car = Picarx()
picam2 = Picamera2()
picam2.start()

# Driving mode: "manual" or "auto"
mode = "manual"

# PID constants (tune these!)
Kp, Ki, Kd = 0.5, 0.0, 0.1
pid_integral = 0
pid_last_error = 0
pid_last_time = time.time()

# Head angles
pan_angle = 0
tilt_angle = 0

# Calibrated default head positions
DEFAULT_PAN = -0.5    
DEFAULT_TILT = 7.5  

# Flask app for video feed
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
# MANUAL MODE FUNCTIONS
# ----------------------
def drive_manual(throttle, steer, rx, ry, reset_head=False):
    global pan_angle, tilt_angle
    
    # Reset camera if button pressed
    if reset_head:
        pan_angle = DEFAULT_PAN
        tilt_angle = DEFAULT_TILT
    # Car driving
    servo_val = steer * 35  # -35° to +35°
    speed_val = int(throttle * 100)
    car.set_dir_servo_angle(servo_val)
    car.set_motor_speed(1, speed_val)
    car.set_motor_speed(2, -speed_val)

    # Camera pan/tilt (discrete, step-based like i/k/j/l)
    step = 0.5
    if rx > 0.5:   # right stick pushed right
        pan_angle = min(pan_angle + step, 35)
    elif rx < -0.5:  # pushed left
        pan_angle = max(pan_angle - step, -35)

    if ry > 0.5:   # pushed up
        tilt_angle = min(tilt_angle + step, 35)
    elif ry < -0.5:  # pushed down
        tilt_angle = max(tilt_angle - step, -35)

    car.set_cam_pan_angle(pan_angle)
    car.set_cam_tilt_angle(tilt_angle)
    print(f"Tilt: {tilt_angle}, Pan: {pan_angle}")


# ----------------------
# AUTO MODE FUNCTIONS
# ----------------------
def pid_controller(desired_angle, current_angle):
    global pid_integral, pid_last_error, pid_last_time

    now = time.time()
    dt = now - pid_last_time if pid_last_time else 0.01

    error = desired_angle - current_angle
    pid_integral += error * dt
    derivative = (error - pid_last_error) / dt if dt > 0 else 0

    output = Kp * error + Ki * pid_integral + Kd * derivative

    pid_last_error = error
    pid_last_time = now
    return output

def drive_auto():
    frame = get_camera_frame()

    # TODO: Replace with AI model prediction
    # e.g., model.predict(frame)
    obstacle_detected = False  

    if not obstacle_detected:
        # Keep driving straight
        correction = pid_controller(desired_angle=0, current_angle=0)  
        car.set_dir_servo_angle(correction)
        car.forward(50)
    else:
        # Stop or avoid obstacle
        car.stop()

# ----------------------
# WEBSOCKET HANDLER
# ----------------------
async def handler(websocket):
    global mode

    print("Client connected")
    try:
        async for message in websocket:
            data = json.loads(message)

            # Mode toggle with controller button
            if data.get("toggle_mode", False):
                mode = "auto" if mode == "manual" else "manual"
                print(f"Switched to {mode.upper()} mode")

            throttle = max(-1, min(data.get("throttle", 0), 1))
            steer = max(-1, min(data.get("steer", 0), 1))
            rx = data.get("rx", 0)
            ry = data.get("ry", 0)
            reset_head = data.get("button_y", False) or data.get("button_x", False)

            if mode == "manual":
                drive_manual(throttle, steer, rx, ry, reset_head)
            elif mode == "auto":
                drive_auto()

    except Exception as e:
        print("Connection handler failed:", e)
        car.stop()

async def ws_main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Starting PiCar-X WebSocket server on port 8765")
        await asyncio.Future()  # run forever

def run_flask():
    app.run(host='0.0.0.0', port=9000, threaded=True)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    asyncio.run(ws_main())
