from enum import Enum
import time
import os
import json
from arduino.app_utils import App, Bridge

from vision import VisionTracker
from display import DisplayManager

print("Starting Biwheel Control Python App...")

# The config file stores persistant config params for the robot
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.json'))

DEFAULT_CONFIG = {
    "scan_speed": 30,
    "hunt_base_speed": 50,
    "min_area": 100,
    "min_sat": 120,
    "min_val": 80,
    "hue_tolerance": 10
}

def load_config():
    cfg = dict(DEFAULT_CONFIG)

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            cfg.update(json.load(f))

    else:
        # If the config file doesnt exist create it with default values
        save_config_file(cfg)

    return cfg


def save_config_file(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)


config = load_config()

tracker = VisionTracker(
    min_area=config["min_area"],
    min_sat=config["min_sat"],
    min_val=config["min_val"],
    hue_tolerance=config["hue_tolerance"]
)


# Controls what the roadrunner is doing
class RobotState(str, Enum):
    SCAN = "SCAN"
    HUNT = "HUNT"


current_state = RobotState.SCAN


# Called by the dashboard when the settings form is submitted
def on_config_change(new_values):
    config.update(new_values)

    # Live update the vision tracker settings
    tracker.set_parameters(
        min_area=config["min_area"],
        min_sat=config["min_sat"],
        min_val=config["min_val"],
        hue_tolerance=config["hue_tolerance"]
    )


display_mgr = DisplayManager(
    config=config,
    load_saved_config=load_config,
    on_config_change=on_config_change,
    on_save_config=lambda: save_config_file(config)
)

display_mgr.start()



def send_motors(l_speed, r_speed):
    Bridge.notify("set_motors", int(l_speed), int(r_speed))




# Send initial state
send_motors(config["scan_speed"], -config["scan_speed"])




last_time = time.time()
frame_count = 0
calculated_fps = 0.0




# Called every update cycle
def step():

    # Not great to use globals but it's easier with this small app
    global current_state, last_time, frame_count, calculated_fps

    # If we didnt get a frame from the camera, just skip this cycle
    ret, frame = tracker.cam.read()
    if not ret or frame is None:
        return

    frame_count += 1
    now = time.time()

    # calculate FPS every second
    if now - last_time >= 1.0:
        calculated_fps = frame_count / (now - last_time)
        frame_count = 0
        last_time = now

    # Results from the tracker (boxes get drawn onto the frame for the dashboard)
    x_norm, y_norm, color_name, area, best_box, boxes = tracker.process_frame(frame, draw_annotations=True)

    delta = 0.0

    # State management
    # If we have a target switch to hunt, otherwise scan

    if best_box is not None and x_norm is not None:

        if current_state != RobotState.HUNT:
            print("Target found -> Switching to HUNT")
            current_state = RobotState.HUNT

        delta = x_norm * 30.0 # Assuming the camera has about 60 deg FOV

        l_speed = int(config["hunt_base_speed"] + delta)
        r_speed = int(config["hunt_base_speed"] - delta)
    else:
        if current_state != RobotState.SCAN:
            print("Target lost -> Switching to SCAN")
            current_state = RobotState.SCAN
        l_speed = int(config["scan_speed"])
        r_speed = int(-config["scan_speed"])

    send_motors(l_speed, r_speed)

    # Send telemetry values to the dashboard
    display_mgr.update(frame, {
        "state": current_state.value,
        "target": color_name,
        "x_offset": round(x_norm, 2) if x_norm is not None else None,
        "area": round(area),
        "delta": round(delta, 1),
        "left_speed": l_speed,
        "right_speed": r_speed,
        "fps": round(calculated_fps, 1)
    })

if __name__ == '__main__':
    App.run(user_loop=step)
