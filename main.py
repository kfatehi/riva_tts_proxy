import os
import uuid
import numpy as np
import riva.client
import wave
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
auth = riva.client.Auth(uri=os.getenv('RIVA_URI'))
riva_tts = riva.client.SpeechSynthesisService(auth)
sample_rate_hz = 44100

@app.route('/')
def index():
    return jsonify({"service_name": "riva_tts_proxy"})

# define the path to the public directory
PUBLIC_DIRECTORY = 'public'

@app.route('/public/<path:filename>')
def download_file(filename):
    # ensure the requested file is within the public directory
    if '../' in filename or not os.path.isfile(os.path.join(PUBLIC_DIRECTORY, filename)):
        return "Invalid path", 400
    # use Flask's send_from_directory() function to send the requested file
    return send_from_directory(PUBLIC_DIRECTORY, filename)

@app.route('/tts', methods=['POST'])
def tts():
    data = request.json

    req = {
        "language_code": data.get("language_code", "en-US"),
        "encoding": riva.client.AudioEncoding.LINEAR_PCM,
        "sample_rate_hz": sample_rate_hz,
        "voice_name": data.get("voice_name", "English-US.Female-1")
    }
    req["text"] = data["text"]
    resp = riva_tts.synthesize(**req)
    audio_samples = np.frombuffer(resp.audio, dtype=np.int16)

    # Save to WAV file
    output_file = f"{uuid.uuid4()}.wav"
    output_path = os.path.join('public', output_file)

    if not os.path.exists('public'):
        os.makedirs('public')

    with wave.open(output_path, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 2 bytes (16 bits) per sample
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(audio_samples.tobytes())

    return jsonify({"path": f"/public/{output_file}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv("PORT"))
