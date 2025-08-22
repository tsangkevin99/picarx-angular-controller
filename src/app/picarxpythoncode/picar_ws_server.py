import asyncio
import json
import threading
from flask import Flask, Response
from picarx import Picarx
import websockets
from picamera2 import Picamera2
import cv2

# Initialize PiCar and camera
car = Picarx()
picam2 = Picamera2()
picam2.start()

MIN_ANGLE = car.DIR_MIN
MAX_ANGLE = car.DIR_MAX
CENTER_ANGLE = (MIN_ANGLE + MAX_ANGLE) // 2

# Flask app for video feed
app = Flask(__name__)

def get_camera_frame_bytes():
    frame = picam2.capture_array()
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

# WebSocket handler for motor control (keyboard or Xbox controller commands)
async def handler(websocket):
    print("Client connected")
    try:
        async for message in websocket:
            data = json.loads(message)
            throttle = data.get("throttle", 0)  # Range: -1 (backward) to 1 (forward)
            steer = data.get("steer", 0)        # Range: -1 (left) to 1 (right)

            # Clamp values
            throttle = max(-1, min(throttle, 1))
            steer = max(-1, min(steer, 1))

            # Calculate servo angle and motor speed
            servo_val = int(CENTER_ANGLE + steer * (MAX_ANGLE - CENTER_ANGLE))
            speed_val = int(throttle * 100)

            # Apply controls
            car.set_dir_servo_angle(servo_val)
            car.set_motor_speed(1, speed_val)
            car.set_motor_speed(2, -speed_val)

            print(f"Throttle: {throttle}, Speed: {speed_val}, Steer: {steer}, Servo: {servo_val}")

    except Exception as e:
        print("connection handler failed:", e)
        car.stop()

async def ws_main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Starting PiCar-X WebSocket server on port 8765")
        await asyncio.Future()  # run forever

def run_flask():
    app.run(host='0.0.0.0', port=9000, threaded=True)

if __name__ == "__main__":
    # Start Flask app in a background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start WebSocket server (for controls) in asyncio event loop
    asyncio.run(ws_main())
