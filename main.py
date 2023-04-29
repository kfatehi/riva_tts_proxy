import os
import uuid
import numpy as np
import riva.client
import wave
import ffmpeg
from io import BytesIO
from flask import Flask, request, jsonify, send_from_directory, send_file

app = Flask(__name__)
auth = riva.client.Auth(uri=os.getenv('RIVA_URI'))
riva_tts = riva.client.SpeechSynthesisService(auth)
sample_rate_hz = 44100

@app.route('/')
def index():
    return jsonify({"service_name": "riva_tts_proxy"})

# define the path to the public directory
PUBLIC_DIRECTORY = 'public'
VOICES = [
    {"voiceName": "Nvidia-Riva English-US.Female-1", "lang": "en", "gender": "Female"},
    {"voiceName": "Nvidia-Riva English-US.Male-1", "lang": "en", "gender": "Male"}
]


@app.route('/public/<path:filename>')
def download_file(filename):
    # ensure the requested file is within the public directory
    if '../' in filename or not os.path.isfile(os.path.join(PUBLIC_DIRECTORY, filename)):
        return "Invalid path", 400
    # use Flask's send_from_directory() function to send the requested file
    return send_from_directory(PUBLIC_DIRECTORY, filename)

@app.route('/voices')
def voices():
    return jsonify(VOICES)

@app.route('/tts', methods=['GET', 'POST'])
def tts():
    if request.method == 'POST':
        data = request.json
        text = data["text"]
        voice_name = data.get("voice_name", "English-US.Female-1")
    else:
        text = request.args.get("text")
        voice_name = request.args.get("voice", "English-US.Female-1")

    req = {
        "language_code": "en-US",
        "encoding": riva.client.AudioEncoding.LINEAR_PCM,
        "sample_rate_hz": sample_rate_hz,
        "voice_name": voice_name
    }
    req["text"] = text
    resp = riva_tts.synthesize(**req)
    audio_samples = np.frombuffer(resp.audio, dtype=np.int16)

    output_file = f"{uuid.uuid4()}.wav"
    output_path = os.path.join('public', output_file)

    if not os.path.exists('public'):
        os.makedirs('public')

    with wave.open(output_path, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 2 bytes (16 bits) per sample
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(audio_samples.tobytes())

    accept = request.args.get("accept", "audio/ogg;codecs=opus") if request.method == 'GET' else None

    if accept:
        converted_output_file = f"{uuid.uuid4()}.ogg"
        converted_output_path = os.path.join('public', converted_output_file)

        stream = ffmpeg.input(output_path)
        stream = ffmpeg.output(stream, converted_output_path, format='ogg', codec='libopus', acodec='libopus')
        ffmpeg.run(stream)
        return send_file(converted_output_path)

    else:
        return jsonify({"path": f"/public/{output_file}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv("PORT"))
