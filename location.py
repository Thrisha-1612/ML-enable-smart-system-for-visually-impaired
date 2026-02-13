# NOTE: Replace placeholders with your own API keys and numbers before running

import pyttsx3
from twilio.rest import Client
import threading
import queue
import time
import urllib.request
import json
import speech_recognition as sr

# Twilio credentials (replace with your actual credentials)
account_sid = '<your-twilio-account-id>'
auth_token = '<your-twilio-auth-token>'
client = Client(account_sid, auth_token)

# OpenCage API key (replace with your key)
OPENCAGE_API_KEY = '<ypur-opencage-api-key>'

# Initialize text-to-speech engine
engine = pyttsx3.init()

# Create a queue for TTS requests
tts_queue = queue.Queue()

# Global flags
emergency_mode = False

# Manually set latitude and longitude (replace with any location you want)
DEFAULT_LATITUDE = 12.9719  # Set your desired latitude
DEFAULT_LONGITUDE = 77.5937  # Set your desired longitude

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

# Function to listen for voice commands and activate emergency mode if 'laptop' is detected
def listen_for_commands():
    global emergency_mode
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for 'laptop' command...") #can set your desired keyword
        while True:
            try:
                # Listen to the audio from the microphone
                audio = recognizer.listen(source)
                command = recognizer.recognize_google(audio).lower()
                print(f"Command: {command}")
                
                if "laptop" in command: #can set your desired keyword
                    emergency_mode = True
                    speak("Emergency mode activated.")
                    send_emergency_sms()
                    speak("Emergency SMS sent.")
                    send_emergency_location()
                    speak("Emergency location sent to caretaker.")
                    emergency_mode = False

            except sr.UnknownValueError:
                # In case the speech was not understood
                pass
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")
                break

# Function to send emergency SMS to the caretaker
def send_emergency_sms():
    caretaker_number = '<caretaker-phone-number>'  # Replace with the actual caretaker number
    message = client.messages.create(
        body="Emergency! Please check on the person.",
        from_='<your-twilio-phone-number>',  # Replace with your Twilio phone number
        to=caretaker_number
    )
    print(f"Emergency SMS sent to {caretaker_number}.")

# Function to get current location using manually set coordinates
def get_current_location():
    # Use the manually set coordinates instead of IP-based geolocation
    latitude = DEFAULT_LATITUDE
    longitude = DEFAULT_LONGITUDE
    print(f"Current Coordinates: Latitude: {latitude}, Longitude: {longitude}")

    # Use OpenCage for reverse geocoding to get more address details via urllib
    url = f'https://api.opencagedata.com/geocode/v1/json?q={latitude},{longitude}&key={OPENCAGE_API_KEY}'
    with urllib.request.urlopen(url) as response:
        data = json.load(response)
        if data['results']:
            address = data['results'][0]['formatted']
            print(f"Address: {address}")
        else:
            address = "Address not available"

    return f"Latitude: {latitude}, Longitude: {longitude}, Address: {address}"

# Function to send the emergency location to the caretaker
def send_emergency_location():
    location = get_current_location()
    caretaker_number = '<caretaker-phone-number>'  # Replace with the actual caretaker number
    message = client.messages.create(
        body=f"Emergency! Current location: {location}",
        from_='<your-twilio-phone-number>',  # Replace with your Twilio phone number
        to=caretaker_number
    )
    print(f"Emergency location sent to {caretaker_number}: {location}")

# Start the TTS worker thread
tts_thread = threading.Thread(target=tts_worker, daemon=True)
tts_thread.start()

# Start listening for voice commands
command_thread = threading.Thread(target=listen_for_commands, daemon=True)
command_thread.start()

# Keep the program running
while True:
    time.sleep(1)  # Run continuously
