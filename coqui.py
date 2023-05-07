import requests

url = "http://localhost:5001/synthesize"
class AudioResponse:
    def __init__(self, audio, sample_rate_hz):
        self.audio = audio
        self.sample_rate_hz = sample_rate_hz

def synthesize(text):
    payload = {"text": text}
    response = requests.post(url, json=payload)
    return AudioResponse(response.content, 24000)

