import pyttsx3
import threading
import pyaudio
import os
import time
from queue import Queue
import subprocess

VIRTUAL_CABLE_DRIVER = "CABLE Input"
tts_queue = Queue()

OUTPUT_FILE = "output.mp3"
OUTPUT_WAV_FILE = "output.wav"

# Initialize the pyttsx3 engine
engine = pyttsx3.init()

# Function to find the virtual cable
def find_virtual_cable():
    audio = pyaudio.PyAudio()
    for i in range(audio.get_device_count()):
        device_info = audio.get_device_info_by_index(i)
        if VIRTUAL_CABLE_DRIVER in device_info['name']:
            return device_info['index']
    raise RuntimeError("Virtual cable not found")

# Function to set up TTS properties
def setup_tts():
    # Set properties like volume and speed if necessary
    engine.setProperty('rate', 160)  # Speed of speech
    engine.setProperty('volume', 1)  # Volume level (0.0 to 1.0)
    voices = engine.getProperty('voices')
    
    # Set a female voice (on Windows, it might be index 1 or on macOS it could be 'com.apple.speech.synthesis.voice.Alex')
    engine.setProperty('voice', voices[1].id)  # Adjust the index as per your system

# Function to convert MP3 to WAV using ffmpeg
def convert_mp3_to_wav(mp3_file, wav_file):
    try:
        # Use ffmpeg to convert MP3 to WAV
        subprocess.call([
            'ffmpeg', '-i', mp3_file, 
            '-analyzeduration', '10000000', '-probesize', '5000000', 
            wav_file
        ])
    except Exception as e:
        print(f"Error with ffmpeg conversion: {e}")
        raise

# Function to process the TTS queue
def process_tts_queue():
    while True:
        text = tts_queue.get()
        if text is None:
            break
        try:
            # Before generating new speech, remove the old output files if they exist
            if os.path.exists(OUTPUT_FILE):
                os.remove(OUTPUT_FILE)
            if os.path.exists(OUTPUT_WAV_FILE):
                os.remove(OUTPUT_WAV_FILE)

            # Use pyttsx3 to generate audio and save it to a file
            engine.save_to_file(text, OUTPUT_FILE)
            engine.runAndWait()

            # Convert the MP3 file to WAV
            convert_mp3_to_wav(OUTPUT_FILE, OUTPUT_WAV_FILE)

            # Now, stream the generated output.wav to the virtual cable
            virtual_cable_index = find_virtual_cable()
            audio = pyaudio.PyAudio()

            # Open the WAV file
            with open(OUTPUT_WAV_FILE, "rb") as wf:
                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=22050,  # Ensure the correct sample rate (WAV typically uses 44100Hz or 22050Hz)
                    output=True,
                    output_device_index=virtual_cable_index
                )

                # Read and stream the WAV file in chunks
                chunk_size = 1024
                while True:
                    data = wf.read(chunk_size)
                    if not data:
                        break
                    stream.write(data)

                stream.close()
                audio.terminate()

            # Delete the output files after playback
            os.remove(OUTPUT_FILE)
            os.remove(OUTPUT_WAV_FILE)

        except Exception as e:
            print(f"Error in TTS processing: {e}")
        tts_queue.task_done()

# Add message to TTS queue
def addToTtsQueue(message):
    tts_queue.put(message)

# Start the TTS thread
def startTtsThread():
    setup_tts()  # Set up TTS settings before starting the thread
    tts_thread = threading.Thread(target=process_tts_queue, daemon=True)
    tts_thread.start()

# Example usage
# if __name__ == "__main__":
#     startTtsThread()

#     # Add some text to the queue for testing
#     addToTtsQueue("Hello, this is a test message. Please check the output.")
#     time.sleep(3)  # Wait for TTS to finish playing
#     addToTtsQueue("Another test message.")
#     time.sleep(3)  # Wait for the second TTS to finish
