import platform
import configparser
import os
from retry import retry

config_file = "sapi5_voices.ini"
engine = None

VOICE_MAP = {}

if platform.system() == "Windows":
    import comtypes.client
    from comtypes.gen import SpeechLib
    import pythoncom

def list_voices():
    tts = comtypes.client.CreateObject('SAPI.SPVoice')
    voices = tts.GetVoices()
    voice_list = []

    for voice in voices:
        voice_list.append((voice.Id, voice.GetDescription()))

    return voice_list

def voices():
    output = []
    if os.path.exists(config_file):    
        try:
            sapi5_voices = list_voices()
            config = configparser.ConfigParser()
            config.read(config_file)
            new_voices = []
            for section in config.sections():
                new_voices.append({
                    "name": config.get(section, "name"),
                    "lang": config.get(section, "lang"),
                    "gender": config.get(section, "gender"),
                    "locator": config.get(section, "locator"),
                    "sample_rate_hz": config.get(section, "sample_rate_hz")
                })

            for voice in sapi5_voices:
                for desc in new_voices:
                    if desc["locator"] in voice[0]:
                        output.append({"voiceName": desc["name"], "lang": desc["lang"], "gender": desc["gender"] })
                        VOICE_MAP[desc["name"]] = {
                            "id": voice[0],
                            "sample_rate_hz": int(desc["sample_rate_hz"])
                        }
        except ImportError:
            pass

    return output

class AudioResponse:
    def __init__(self, audio, sample_rate_hz):
        self.audio = audio
        self.sample_rate_hz = sample_rate_hz

def remove_non_utf8_chars(text):
    encoded_text = text.encode("utf-8", errors="ignore")
    decoded_text = encoded_text.decode("utf-8")
    return decoded_text

def synthesize(input_text, voice):
    final_data = bytearray()
    text = remove_non_utf8_chars(input_text)
    voice_info = VOICE_MAP[voice]
    voice_id = voice_info["id"]
    sample_rate_hz = voice_info["sample_rate_hz"]
    pythoncom.CoInitialize()
    voice_obj = comtypes.client.CreateObject('SAPI.SPVoice')
    voices = voice_obj.GetVoices()
    for voice in voices:
        if voice.Id == voice_id:
            voice_obj.Voice = voice
            break    
    try:
        memory_stream = comtypes.client.CreateObject('SAPI.SpMemoryStream')
        voice_obj.AudioOutputStream = memory_stream
        voice_obj.Speak(text)
        memory_stream.Seek(0, 0)
        final_data = final_data+bytearray(memory_stream.GetData())
    except comtypes.COMError:
        memory_stream = comtypes.client.CreateObject('SAPI.SpMemoryStream')
        voice_obj.AudioOutputStream = memory_stream
        voice_obj.Speak("COM Error")
        memory_stream.Seek(0, 0)
        final_data = final_data+bytearray(memory_stream.GetData())
    finally:
        pythoncom.CoUninitialize()
        return AudioResponse(final_data, sample_rate_hz)