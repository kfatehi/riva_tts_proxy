import os
import numpy as np
import riva.client
import io
import av
import wave
import copy
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from nltk.tokenize import sent_tokenize
from retry import retry
from grpc._channel import _MultiThreadedRendezvous

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


def tts_requests_from_http_request():
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
    req = {
        "language_code": "en-US",
        "encoding": riva.client.AudioEncoding.LINEAR_PCM,
        "sample_rate_hz": sample_rate_hz,
        "voice_name": data.get("voice", "English-US.Female-1")
    }

    if "text" in data:
        text = data["text"]
    else:
        return []

    sentences = [f'<speak><prosody pitch="{pitch}" rate="{rate}">{sentence}</prosody></speak>' for sentence in sent_tokenize(text)]
    # riva tts does not support sentences so we have to handle splitting this paragraph into separate requests
    # loop through sentences, copying all data dictionary attributes, but set "text" to the sentence, and then return the dictionaries        
    new_data_list = []

    for sentence in sentences:
        new_data = copy.deepcopy(req)
        new_data["text"] = sentence
        new_data_list.append(new_data)

    print(datetime.now(), request.path, request.access_route[-1], new_data_list)
    return new_data_list

@app.route('/tts_batch', methods=['POST'])
def tts_batch():
    reqs = tts_requests_from_http_request()
    audio_samples_list = []

    for i, req in enumerate(reqs):
        resp = riva_tts.synthesize(**req)
        audio_samples = np.frombuffer(resp.audio, dtype=np.int16)
        audio_samples_list.append(audio_samples)

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
    output_stream = output_container.add_stream("libopus", rate=sample_rate_hz)

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

@retry(tries=5, exceptions=(_MultiThreadedRendezvous,))
def tts_streaming_generator(reqs, sample_rate_hz):
    pts = 0
    for i, req in enumerate(reqs):
        responses = riva_tts.synthesize_online(**req)
        for resp in responses:
            output_buffer = io.BytesIO()
            output_container = av.open(output_buffer, mode='w', format='ogg')
            output_stream = output_container.add_stream("libopus", rate=sample_rate_hz)
            audio_samples = np.frombuffer(resp.audio, dtype=np.int16)
            frame = av.AudioFrame(format='s16', layout='mono', samples=len(audio_samples))
            frame.sample_rate = sample_rate_hz
            frame.planes[0].update(audio_samples.tobytes())
            frame.pts = pts
            for packet in output_stream.encode(frame):
                output_container.mux(packet)
                data = output_buffer.getvalue()
                if data:
                    yield data
                    output_buffer.seek(0)
                    output_buffer.truncate()

            # Flush any remaining packets
            for packet in output_stream.encode(None):
                output_container.mux(packet)

            output_container.close()

            # Yield the remaining chunk
            data = output_buffer.getvalue()
            if data:
                yield data

@app.route('/tts', methods=['POST'])
def tts_streaming():
    reqs = tts_requests_from_http_request()

    if len(reqs) > 0:
        # Create a generator that will synthesize and stream each request as soon as it's ready
        continuous_stream = tts_streaming_generator(reqs, sample_rate_hz)

        return continuous_stream, {'Content-Type':"audio/ogg"}
    else:
        return "Bad request", 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv("PORT"))
