import cv2
import pyttsx3
import queue
import threading
from ultralytics import YOLO
import time

# Initialize YOLO model
model = YOLO('yolov8n.pt')

# Initialize text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Adjust the speaking rate if needed

# Create a queue for TTS requests
tts_queue = queue.Queue()

# Global flag for last detected objects
last_detected_objects = {}

# IP address and port from IP Webcam app
ip_camera_url = "http://10.93.7.32:8080/video"  # Replace with your actual IP address and port

# Initialize video capture from the IP camera URL
cap = cv2.VideoCapture(ip_camera_url)

def tts_worker():
    while True:
        text = tts_queue.get()
        if text is None:
            break
        engine.say(text)
        engine.runAndWait()
        tts_queue.task_done()

def speak(text):
    tts_queue.put(text)

def get_object_position(xmin, ymin, xmax, ymax, frame_width, frame_height):
    obj_center_x = (xmin + xmax) / 2
    obj_center_y = (ymin + ymax) / 2
    screen_center_x = frame_width / 2
    screen_center_y = frame_height / 2

    horizontal_position = "center"
    vertical_position = "center"

    if obj_center_x < screen_center_x - (screen_center_x / 3):
        horizontal_position = "left"
    elif obj_center_x > screen_center_x + (screen_center_x / 3):
        horizontal_position = "right"

    if obj_center_y < screen_center_y - (screen_center_y / 3):
        vertical_position = "top"
    elif obj_center_y > screen_center_y + (screen_center_y / 3):
        vertical_position = "bottom"

    return f"{vertical_position} {horizontal_position}"

def process_frame(frame):
    global last_detected_objects

    # Resize the frame to 640x480
    resized_frame = cv2.resize(frame, (640, 480))

    results = model(resized_frame)

    current_detected_objects = {}

    detected_objects_info = []

    for result in results[0].boxes:
        class_id = int(result.cls)
        class_name = results[0].names[class_id]
        xmin, ymin, xmax, ymax = map(int, result.xyxy[0])
        object_position = get_object_position(xmin, ymin, xmax, ymax, resized_frame.shape[1], resized_frame.shape[0])

        if class_name not in current_detected_objects:
            current_detected_objects[class_name] = []

        current_detected_objects[class_name].append(object_position)

    for class_name, positions in current_detected_objects.items():
        if (class_name not in last_detected_objects) or (last_detected_objects[class_name] != positions):
            position_string = ', '.join(positions)
            detected_objects_info.append(f"{class_name} is in {position_string}")

    last_detected_objects = current_detected_objects

    # Resize the processed frame to 640x480
    processed_frame = cv2.resize(results[0].plot(), (640, 480))
    return processed_frame, detected_objects_info

# Start the TTS worker thread
tts_thread = threading.Thread(target=tts_worker, daemon=True)
tts_thread.start()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    processed_frame, detected_objects_info = process_frame(frame)

    if detected_objects_info:
        print("Detected: " + ". ".join(detected_objects_info))
        for obj_info in detected_objects_info:
            speak(obj_info)
            time.sleep(0.5)  # 0.5 second gap to minimize delay

    cv2.imshow("Processed Frame", processed_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Stop the TTS worker thread
tts_queue.put(None)
tts_thread.join()
