import speech_recognition as sr
import pyttsx3
import cv2
from ultralytics import YOLO
import hashlib
import threading
import queue
import time
from twilio.rest import Client
import geocoder
import urllib.request
import json
import webbrowser
import urllib.parse
import tkinter as tk

# Twilio credentials
account_sid = '<your-twilio-account-id>'
auth_token = '<your-twilio-auth-token>'
client = Client(account_sid, auth_token)

# OpenCage API key (replace with your key)
OPENCAGE_API_KEY = '<-your-api-key>'

# Initialize text-to-speech engine
engine = pyttsx3.init()

# Create a queue for TTS requests
tts_queue = queue.Queue()

# Global flags
emergency_mode = False
last_detected_objects = {}

# Initialize speech recognizer
recognizer = sr.Recognizer()

# Initialize YOLO model
model = YOLO('yolov8n.pt')

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

def send_emergency_sms():
    caretaker_number = '<actual-caretaker-contact-number>' #placeholder for caretaker number
    message = client.messages.create(
        body="Emergency! Please check on the person.",
        from_='<your-twilio-number>', #placeholde for twilio number
        to=caretaker_number
    )
    print(f"Emergency SMS sent to {caretaker_number}.")

def get_current_location():
    g = geocoder.ip('me')
    location = g.latlng
    print(f"Current Coordinates: Latitude: {location[0]}, Longitude: {location[1]}")

    # Reverse geocode to get the address
    url = f'https://api.opencagedata.com/geocode/v1/json?q={location[0]},{location[1]}&key={OPENCAGE_API_KEY}'
    with urllib.request.urlopen(url) as response:
        data = json.load(response)
        if data['results']:
            address = data['results'][0]['formatted']
            print(f"Address: {address}")
        else:
            address = "Address not available"

    return f"Latitude: {location[0]}, Longitude: {location[1]}, Address: {address}"

def send_emergency_location():
    location = get_current_location()
    caretaker_number = '<actual-caretaker-contact-number>' #placeholder for caretaker number
    message = client.messages.create(
        body=f"Emergency! Current location: {location}",
        from_='<your-twilio-number>', #placeholde for twilio number
        to=caretaker_number
    )
    print(f"Emergency location sent to {caretaker_number}: {location}")

def listen_for_commands():
    global emergency_mode
    while True:
        with sr.Microphone() as source:
            audio = recognizer.listen(source)
            try:
                command = recognizer.recognize_google(audio).lower()
                print(f"Command: {command}")
                if "laptop" in command:  # Activate emergency, can replace laptop with any other keyword
                    emergency_mode = True
                    speak("Emergency mode activated.")
                    send_emergency_sms()
                    speak("Emergency SMS sent.")
                    send_emergency_location()
                    speak("Emergency location sent to caretaker.")
                    emergency_mode = False

                elif "navigate to" in command:
                    destination = command.split("navigate to")[1].strip()
                    print(f"Destination: {destination}")
                    navigate_to(destination)

            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                speak("Could not request results; check your network connection.")

def navigate_to(destination):
    g = geocoder.ip('me')
    if g.ok:
        latitude, longitude = g.latlng
        print(f"Current Coordinates: Latitude: {latitude}, Longitude: {longitude}")

        # Get address from coordinates
        source_address = get_address_from_coordinates(latitude, longitude)

        # URL-encode the destination to handle spaces and special characters
        encoded_destination = urllib.parse.quote(destination)

        # Format the URL for Google Maps navigation
        maps_url = f"https://www.google.com/maps/dir/{latitude},{longitude}/{encoded_destination}/"
        print(f"Navigating from {source_address} to {destination}")
        
        # Open the URL in the browser
        webbrowser.open(maps_url)
    else:
        print("Could not determine current location for navigation.")

def get_address_from_coordinates(latitude, longitude):
    url = f'https://api.opencagedata.com/geocode/v1/json?q={latitude},{longitude}&key={OPENCAGE_API_KEY}'
    with urllib.request.urlopen(url) as response:
        data = json.load(response)
        if data['results']:
            address = data['results'][0]['formatted']
            print(f"Address: {address}")
        else:
            address = "Address not available"
    return address

def get_frame_hash(frame):
    frame_string = cv2.imencode('.jpg', frame)[1].tobytes()
    return hashlib.md5(frame_string).hexdigest()

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

    # Resize the frame to reduce processing load
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
    return cv2.resize(results[0].plot(), (frame.shape[1], frame.shape[0])), detected_objects_info

# Get screen resolution
root = tk.Tk()
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.destroy()

# Input source: 'camera', 'image', or 'video'
input_source = 'camera'  # Change to 'image' or 'video' as needed

# Define image path once here
image_path = r"<image-path-here>"  # Provide the path to your image file

# Initialize the video capture object
cap = None
if input_source == 'camera':
    cap = cv2.VideoCapture(0)
elif input_source == 'video':
    cap = cv2.VideoCapture('video.mp4')  # Provide the path to your video file here

# Start the voice command listening thread
threading.Thread(target=listen_for_commands, daemon=True).start()

# Start the TTS worker thread
tts_thread = threading.Thread(target=tts_worker, daemon=True)
tts_thread.start()

last_capture_time = time.time()  # Time when the last image was captured

while True:
    if input_source == 'camera' or input_source == 'video':  # Only use video capture for 'camera' or 'video'
        ret, frame = cap.read()
        if not ret:
            break
    elif input_source == 'image':
        # For image input source, use the static image and resize it to 640x480
        frame = cv2.imread(image_path)
        frame = cv2.resize(frame, (480, 640))  # Resize image to 640x480

    current_time = time.time()

    # If 5 seconds have passed since the last image capture or if there is a change in object positions
    if current_time - last_capture_time >= 5:
        # Process frame and capture the image
        annotated_frame, detected_objects_info = process_frame(frame)

        if annotated_frame is not None:
            cv2.imshow('YOLOv8 Detection', annotated_frame)

            # Provide continuous voice feedback for detected objects
            for obj_info in detected_objects_info:
                speak(obj_info)
                time.sleep(0.5)  # 0.5 second gap to minimize delay

        # Update the last capture time
        last_capture_time = current_time

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# After processing, release the video capture only if cap was defined
if input_source == 'camera' or input_source == 'video':
    cap.release()
cv2.destroyAllWindows()

# Stop the TTS worker thread
tts_queue.put(None)
tts_thread.join()
