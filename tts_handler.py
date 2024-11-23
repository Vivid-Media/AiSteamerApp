import edge_tts
import threading
import os
import asyncio
import pyaudio
from pydub import AudioSegment
from queue import Queue

VIRTUAL_CABLE_DRIVER = "CABLE Input"
tts_queue = Queue()

OUTPUT_FILE = "output.mp3"
OUTPUT_WAV_FILE = "output.wav"

# Function to find the virtual cable
def find_virtual_cable():
    audio = pyaudio.PyAudio()
    for i in range(audio.get_device_count()):
        device_info = audio.get_device_info_by_index(i)
        if VIRTUAL_CABLE_DRIVER in device_info['name']:
            return device_info['index']
    raise RuntimeError("Virtual cable not found")

# Function to synthesize TTS with edge-tts
async def synthesize_tts(text, output_file):
    try:
        communicate = edge_tts.Communicate(text, voice="en-US-AnaNeural")
        await communicate.save(output_file)
    except Exception as e:
        print(f"Error in edge-tts synthesis: {e}")

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

            # Generate TTS output (MP3)
            asyncio.run(synthesize_tts(text, OUTPUT_FILE))

            # Convert MP3 to WAV using pydub
            audio = AudioSegment.from_file(OUTPUT_FILE, format="mp3")
            audio.export(OUTPUT_WAV_FILE, format="wav")

            # Find the virtual cable for audio playback
            virtual_cable_index = find_virtual_cable()
            py_audio = pyaudio.PyAudio()

            # Configure stream to match the WAV file properties
            stream = py_audio.open(
                format=pyaudio.paInt16,  # pydub exports 16-bit WAV files
                channels=1,             # Mono audio
                rate=int(audio.frame_rate),  # Use the frame rate from the WAV file
                output=True,
                output_device_index=virtual_cable_index
            )

            # Play the WAV file
            chunk_size = 1024
            with open(OUTPUT_WAV_FILE, "rb") as wf:
                while chunk := wf.read(chunk_size):
                    stream.write(chunk)

            stream.close()
            py_audio.terminate()

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
    tts_thread = threading.Thread(target=process_tts_queue, daemon=True)
    tts_thread.start()
