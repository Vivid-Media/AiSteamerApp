import asyncio
import threading
from queue import Queue
import pyaudio
from edge_tts import Communicate


VIRTUAL_CABLE_DRIVER = "CABLE Input (VB-Audio Virtual Cable)"


tts_queue = Queue()

def findVirtualCable():
    audio = pyaudio.PyAudio()
    for i in range(audio.get_device_count()):
        deviceInfo = audio.get_device_info_by_index(i)
        if VIRTUAL_CABLE_DRIVER in deviceInfo['name']:
            return deviceInfo['index']
    raise RuntimeError("Virtual cable not found")

async def streamTtsToVirtualCable(text):
    virtualCableIndex = findVirtualCable()
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=24000,
        output=True,
        output_device_index=virtualCableIndex
    )

    communicate = Communicate(text, "en-US-JennyNeural")
    async for chunk in communicate.stream():
        if chunk['type'] == 'audio':
            stream.write(chunk['data'])
        stream.close()
        audio.terminate()

def processTtsQueue():
    while True:
        text = tts_queue.get()
        if text is None:
            break
        try:
            asyncio.run(streamTtsToVirtualCable(text))
        except Exception as e:
            print(f'Error in TTS processing: {e}')
        tts_queue.task_done()
def addToTtsQueue(message):
    tts_queue.put(message)

def startTtsThread():
    ttsThread = threading.Thread(target=processTtsQueue, daemon=True)
    ttsThread.start()