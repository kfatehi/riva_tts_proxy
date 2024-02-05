# Nvidia Riva TTS Proxy

Nvidia Riva is a next-gen text-to-speech system. The text-to-speech (TTS) pipeline implemented for the Riva TTS service is based on a two-stage pipeline. Riva first generates a mel-spectrogram using the first model, and then generates speech using the second model. This pipeline forms a TTS system that enables you to synthesize natural sounding speech from raw transcripts without any additional information such as patterns or rhythms of speech.

This webserver wraps the Nvidia Riva gRPC client within an easy-to-use HTTP JSON API. It also handles some shortcomings of using Riva TTS directly, these are:
- sentence tokenization (Riva does not support more than once sentence per inference request)
- automatic retry (inference fails for unknown reasons, randomly, rarely, but annoyingly. This can be safely retried without being seen by the client and happens so fast it is not noticed, so we do it here.)
- streaming output of batch-mode inference outputs (batch mode sounds better, but means you can't stream, but we are tokenizing sentences anyway, so we stream batch mode)
- transcoding into various (per-request, user-selected) formats using PyAV

## Requirements

* Docker
* [Nvidia Riva](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/quick-start-guide.html)
    - NVIDIA GPU with >=15 GB of VRAM (works great on a 4090)

Note about memory usage: I tried to turn off the other features in Riva but it seems to load all models regardless. This may be because I would have to run "riva_init.sh" again, but it takes very long so I'm unwilling to perform that test. "riva_start.sh" should just be respecting the config, but it loads all the models, therefore I cannot recommend people try this without a large enough GPU.

With that said, the [support matrix](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/support-matrix.html) indicates that you only need 2.1GB for the TTS model.

## Getting Riva

1. You need to setup an Nvidia NGC account so that you can generate an API key here https://ngc.nvidia.com/setup/api-key
2. Install NGC client from here https://ngc.nvidia.com/setup/installers/cli -- N.B. I use it from WSL2, so I grab the linux amd64 binary and add it to my PATH. 
3. Follow the quick start guide here https://docs.nvidia.com/deeplearning/riva/user-guide/docs/quick-start-guide.html which will tell you how to install Riva by downloading their scripts with NGC CLI.

## Usage

Start the server. Be sure to forward port 5000 to somewhere on your host.

```
docker run -d -p 5000:5000 --restart unless-stopped --name riva_tts_proxy -t keyvanfatehi/riva_tts_proxy:latest
```

Now you can use it, for example, from the ReadAloud extension by entering http://localhost:5000 into the Riva TTS proxy server section.

## Configuration

The system will not work without a functional Riva stack. By default, this is expected to run on the same docker host. To change this, you may configure the RIVA_URI environment variable.

You may also wish to increase the amount of web workers. This is possible using the WEB_CONCURRENCY environment variable.

## Building

You may build the image like so:

```
docker build -t keyvanfatehi/riva_tts_proxy:latest .
```

## Endpoints

### GET /voices

Response with a JSON of supported voices.

### POST /tts

* Riva TTS does not support multiple sentences is one request, so this endpoint will automatically split them for you using the NLTK package.
* Riva TTS has a streaming function, but it produces audio artifacts compared to batch, so we feed the synthesized audio for each sentence into the batch mode.
* If you chose an encoding (Accept header), the audio is transcoded automatically. The output stream of the transcoder is shipped to your client as soon as possible.
* If you did not choose an encoding, the outputs (per sentence) from the batch-mode synthesizer are shipped to your client as soon as possible

Headers:

```
Content-Type: application/json
Accept: audio/webm
```

Body:

```
{
    "voice_name"     : "English-US.Female-1",
    "text"           : "Input text from which to generate speech. Feel free to use multiple sentences. There is no artificial pause between sentences. Want there to be? Contribute to the project."
}
```

N.B.

Response is an audio stream based on provided Accept header. If you do not provide one, you will receive audio/wav.

If you would like to use an encoding, set Accept to one of:
- audio/webm
- audio/ogg
- audio/mpeg

I've found that audio/mpeg provides the greatest compatibility with browser APIs, mainly, the picky, yet powerful [MediaSource](https://developer.mozilla.org/en-US/docs/Web/API/MediaSource) API

## Known Uses

- Python: Linux client using `aplay` (written for the Comma 3, which is an ARM computer) https://github.com/kfatehi/tici-developer-setup/blob/master/scripts/riva-tts.py
- JavaScript: A Text-To-Speech browser extension called Read Aloud https://github.com/ken107/read-aloud/pull/321

Are you using this project? Please add it to the list.
