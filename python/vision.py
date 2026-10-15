import cv2
import numpy as np

# Class for tracking prey in frame
class VisionTracker:
    def __init__(self, camera_index=0, min_area=100, min_sat=120, min_val=80, hue_tolerance=10):
        self.cam = cv2.VideoCapture(camera_index)
        if self.cam.isOpened():
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            print(f"Camera opened at index {camera_index}.")
        else:
            print(f"Error: Could not open camera at index {camera_index}.")

        # Use set_parameters so the starting values get the same limits as live updates
        self.set_parameters(min_area, min_sat, min_val, hue_tolerance)
        self.kernel = np.ones((5, 5), dtype=np.uint8) # kernal of 5 is pretty robust so we don't need the option to change it

    

    # Use this to live update from the dashboard if needed
    def set_parameters(self, min_area=None, min_sat=None, min_val=None, hue_tolerance=None):

        # We allow passing in none values to update only specific parameters
        if min_area is not None:
            self.min_area = max(10, min(2000, int(min_area)))

        if min_sat is not None:
            self.min_sat = max(0, min(255, int(min_sat)))

        if min_val is not None:
            self.min_val = max(0, min(255, int(min_val)))

        if hue_tolerance is not None:
            self.hue_tolerance = max(1, min(30, int(hue_tolerance))) # Hue tolerance should be 1-30 reasonably

    def process_frame(self, frame, draw_annotations=False):
        
        # Return early if we didnt get anything
        if frame is None:
            return None, None, None, 0.0, None, []


        h, w = frame.shape[:2]
        cx, cy = w / 2.0, h / 2.0


        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Calculate bounds for red color in HSV space 
        lower1 = np.array([0, self.min_sat, self.min_val], dtype=np.uint8)
        upper1 = np.array([self.hue_tolerance, 255, 255], dtype=np.uint8)

        lower2 = np.array([180 - self.hue_tolerance, self.min_sat, self.min_val], dtype=np.uint8)
        upper2 = np.array([180, 255, 255], dtype=np.uint8)

        # Create a mask for red color using the two ranges (how red is each part of the image)
        mask = cv2.bitwise_or(
            cv2.inRange(hsv, lower1, upper1),
            cv2.inRange(hsv, lower2, upper2)
        )
        
        # This allows us to expand regions and fill in small gaps making our detection better
        # The kernel "blurs" the mask
        mask = cv2.dilate(mask, self.kernel)

        # Find parts of the image where it gets much redder or much less red
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        largest_area = 0.0
        best_box = None
        boxes = []

        # Loop over all detections and find the biggest
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_area:
                bx, by, bw, bh = cv2.boundingRect(contour)
                boxes.append({
                    "box": [bx, by, bw, bh],
                    "color": "Red"
                })


                # Draw bounding box on frame for visualization
                if draw_annotations:
                    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 0, 255), 2)

                if area > largest_area:
                    largest_area = area
                    best_box = (bx, by, bw, bh)

        # Crosshair in center for ref
        if draw_annotations:

            cross_size = 20

            cv2.line(frame, (int(cx) - cross_size, int(cy)), (int(cx) + cross_size, int(cy)), (0, 255, 255), 2)
            cv2.line(frame, (int(cx), int(cy) - cross_size), (int(cx), int(cy) + cross_size), (0, 255, 255), 2)

        if best_box is not None:
            
            # Find the center and compute offset from center frame
            bx, by, bw, bh = best_box
            center_x = bx + bw / 2.0
            center_y = by + bh / 2.0

            x_norm = (center_x - cx) / cx
            y_norm = (cy - center_y) / cy

            if draw_annotations:
                cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 255), 3)
                cv2.circle(frame, (int(center_x), int(center_y)), 5, (0, 255, 255), -1)

            return float(x_norm), float(y_norm), "Red", float(largest_area), best_box, boxes

        return None, None, None, 0.0, None, boxes

    # Remove references to camera
    def release(self):
        if self.cam and self.cam.isOpened():
            self.cam.release()
