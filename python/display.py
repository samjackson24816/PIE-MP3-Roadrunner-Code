import time
import threading
import logging
import cv2
from flask import Flask, Response, jsonify, request, render_template, redirect


# A small Flask server that shows the camera feed, robot status, and settings
class DisplayManager:

    def __init__(self, config, load_saved_config, on_config_change, on_save_config, port=5000):
        self.config = config
        self.load_saved_config = load_saved_config
        self.on_config_change = on_config_change
        self.on_save_config = on_save_config
        self.port = port

        # The robot loop and the server run in different threads, so lock shared data
        self.lock = threading.Lock()
        self.latest_jpeg = None
        self.last_encode_time = 0.0
        self.status = {"state": "STARTING"}

        self.app = Flask(__name__)
        self.app.json.sort_keys = False  # keep status in the order main.py sends it
        logging.getLogger('werkzeug').setLevel(logging.ERROR)  # don't flood the console

        

        # Routes can be called from the browser

        @self.app.route('/')
        def index():
            # Show the values in use, plus the values saved in config.json
            return render_template('index.html', config=self.config, saved=self.load_saved_config())

        @self.app.route('/video_feed')
        def video_feed():
            def generate():
                while True:
                    with self.lock:
                        jpeg = self.latest_jpeg
                    if jpeg is not None:
                        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n'
                    time.sleep(0.1)
            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

        @self.app.route('/status')
        def status():
            with self.lock:
                return jsonify(self.status)

        @self.app.route('/config', methods=['POST'])
        def set_config():
            self.on_config_change({k: int(v) for k, v in request.form.items() if k in self.config})
            if 'save' in request.form:
                self.on_save_config()

            return redirect('/')

    def update(self, frame, status):
        with self.lock:
            self.status = status

        # Encoding is slow so only do it 10 times a second
        now = time.time()
        if now - self.last_encode_time < 0.1:
            return
        self.last_encode_time = now

        ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 40])

        if ok:
            with self.lock:
                self.latest_jpeg = jpeg.tobytes()

    def start(self):
        # Run the server in the background so the robot loop keeps going
        threading.Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=self.port, threaded=True),
            daemon=True
        ).start()
        print(f"Display server started on port {self.port}.")
