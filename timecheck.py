import cv2
import time
from ultralytics import YOLO

# Initialize YOLO model
model = YOLO('yolov8n.pt')  # Use the appropriate model variant

# Initialize video capture 
# \(0 for webcam or path to video file)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    start_time = time.time()

    # Perform object detection
    results = model(frame)

    end_time = time.time()
    detection_time = end_time - start_time
    print(f"Detection Time: {detection_time:.4f} seconds")

    # Display the results (optional)
    annotated_frame = results[0].plot()
    cv2.imshow('YOLOv8 Detection', annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
