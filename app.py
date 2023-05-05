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
import grpc

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

def get_format_and_codec(accept_header):
    if accept_header.startswith('audio/webm'):
        return 'webm', 'libopus'
    elif accept_header.startswith('audio/ogg'):
        return 'ogg', 'libopus'
    elif accept_header.startswith('audio/mpeg'):
        return 'mp3', 'libmp3lame'
    else:
        return None, None

def gen_wav_header(sample_rate, bits_per_sample, channels, datasize):
    o = bytes("RIFF", 'ascii')  # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(4, 'little')  # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE", 'ascii')  # (4byte) File type
    o += bytes("fmt ", 'ascii')  # (4byte) Format Chunk Marker
    o += (16).to_bytes(4, 'little')  # (4byte) Length of above format data
    o += (1).to_bytes(2, 'little')  # (2byte) Format type (1 - PCM)
    o += channels.to_bytes(2, 'little')  # (2byte)
    o += sample_rate.to_bytes(4, 'little')  # (4byte)
    o += (sample_rate * channels * bits_per_sample // 8).to_bytes(4, 'little')  # (4byte)
    o += (channels * bits_per_sample // 8).to_bytes(2, 'little')  # (2byte)
    o += bits_per_sample.to_bytes(2, 'little')  # (2byte)
    o += bytes("data", 'ascii')  # (4byte) Data Chunk Marker
    o += datasize.to_bytes(4, 'little')  # (4byte) Data size in bytes
    return o

@retry(tries=5, exceptions=(_MultiThreadedRendezvous, grpc.RpcError))
def synthesize_online_with_retry(**kwargs):
    return riva_tts.synthesize_online(**kwargs)

def tts_streaming_generator(reqs, sample_rate_hz, output_format, output_codec):
    pts = 0
    if output_format == None:
        wav_header = gen_wav_header(sample_rate_hz, 16, 1, 0)
        yield wav_header

    for i, req in enumerate(reqs):
        responses = synthesize_online_with_retry(**req)
        for resp in responses:
            if output_format == None:
                yield resp.audio
            else:
                output_buffer = io.BytesIO()
                output_container = av.open(output_buffer, mode='w', format=output_format)
                output_stream = output_container.add_stream(output_codec, rate=sample_rate_hz)
                audio_samples = np.frombuffer(resp.audio, dtype=np.int16)
                if len(audio_samples) > 0:
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
                    pts += frame.samples  # Update the pts value with the number of samples in the frame
                output_container.close()  # Close the output container
                data = output_buffer.getvalue()
                if data:
                    yield data




@app.route('/tts', methods=['POST'])
def tts_streaming():
    reqs = tts_requests_from_http_request()
    accept_header = request.headers.get('Accept')
    output_format, output_codec = get_format_and_codec(accept_header)

    if len(reqs) > 0:
        # Create a generator that will synthesize and stream each request as soon as it's ready
        continuous_stream = tts_streaming_generator(reqs, sample_rate_hz, output_format, output_codec)

        return continuous_stream, {'Content-Type':"audio/ogg"}
    else:
        return "Bad request", 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv("PORT"))
