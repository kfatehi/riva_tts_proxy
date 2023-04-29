import os
import uuid
import numpy as np
import riva.client
import io
import av
import wave
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, send_file, after_this_request

app = Flask(__name__)
auth = riva.client.Auth(uri=os.getenv('RIVA_URI'))
riva_tts = riva.client.SpeechSynthesisService(auth)
sample_rate_hz = 48000

@app.route('/')
def index():
    return jsonify({"service_name": "riva_tts_proxy"})

# Voice list can be found here https://docs.nvidia.com/deeplearning/riva/user-guide/docs/tts/tts-overview.html
VOICES = [
    {"voiceName": "English-US.Female-1", "lang": "en", "gender": "Female"},
    {"voiceName": "English-US.Male-1", "lang": "en", "gender": "Male"},
    {"voiceName": "English-US-RadTTS.Female-1", "lang": "en", "gender": "Female"},
    {"voiceName": "English-US-RadTTS.Male-1", "lang": "en", "gender": "Male"}
]

@app.route('/voices')
def voices():
    return jsonify(VOICES)

@app.route('/tts', methods=['POST'])
def tts():
    data = request.json
    pitch = "1"
    rate = "100%"
    
    if "pitch" in data:
        input_range = (0, 2)
        output_range = (-3, 3) # https://docs.nvidia.com/deeplearning/riva/archives/2-1-0/user-guide/docs/tutorials/tts-python-advanced-customizationwithssml.html#pitch-attribute
        pitch = str(np.interp(float(data["pitch"]), input_range, output_range))

    if "rate" in data:
        input_range = (0, 3)
        output_range = (25, 250) # https://docs.nvidia.com/deeplearning/riva/archives/2-1-0/user-guide/docs/tutorials/tts-python-advanced-customizationwithssml.html#rate-attribute
        rate = str(int(np.interp(float(data["rate"]), input_range, output_range)))+"%"

    text = data["text"]
    voice_name = data.get("voice", "English-US.Female-1")
    req = {
        "language_code": "en-US",
        "encoding": riva.client.AudioEncoding.LINEAR_PCM,
        "sample_rate_hz": sample_rate_hz,
        "voice_name": voice_name
    }
    req["text"] = f"""<speak><prosody pitch="{pitch}" rate="{rate}">{text}</prosody></speak>"""
    
    print(datetime.now(), request.access_route[-1], req)

    resp = riva_tts.synthesize(**req)
    audio_samples = np.frombuffer(resp.audio, dtype=np.int16)

    # Create a WAV file in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(audio_samples.tobytes())

    # Rewind the buffer
    wav_buffer.seek(0)

    # Convert WAV to OGG using PyAV
    input_container = av.open(wav_buffer, mode='r')
    output_buffer = io.BytesIO()

    output_container = av.open(output_buffer, mode='w', format='ogg')
    output_stream = output_container.add_stream("libopus", rate=48000)

    for frame in input_container.decode(audio=0):
        for packet in output_stream.encode(frame):
            output_container.mux(packet)

    for packet in output_stream.encode(None):
        output_container.mux(packet)

    output_container.close()

    # Rewind the output buffer
    output_buffer.seek(0)

    # Serve the OGG file
    return send_file(output_buffer, mimetype="audio/ogg")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv("PORT"))
