# Nvidia Riva TTS Proxy

This webserver wraps the Nvidia Riva gRPC client within an easy-to-use HTTP JSON API

Nvidia Riva is a next-gen text-to-speech system. The text-to-speech (TTS) pipeline implemented for the Riva TTS service is based on a two-stage pipeline. Riva first generates a mel-spectrogram using the first model, and then generates speech using the second model. This pipeline forms a TTS system that enables you to synthesize natural sounding speech from raw transcripts without any additional information such as patterns or rhythms of speech.

## Requirements

* Docker
* [Nvidia Riva](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/quick-start-guide.html)
    - NVIDIA GPU with >=15 GB of VRAM (works great on a 4090)

Note about memory usage: I tried to turn off the other features in Riva but it seems to load all models regardless. This may be because I would have to run "riva_init.sh" again, but it takes very long so I'm unwilling to perform that test. "riva_start.sh" should just be respecting the config, but it loads all the models, therefore I cannot recommend people try this without a large enough GPU.

## Usage

Start the server. Be sure to forward port 5000 to somewhere on your host.

```
docker run --rm -p 5000:5000 -t keyvanfatehi/riva_tts_proxy:latest
```

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

Synthesize text using Riva TTS in streaming mode. When making a streaming request, audio chunks are returned as soon as they are generated, significantly reducing the latency (as measured by time to first audio) for large requests.

Request JSON body:

```
{
    "voice_name"     : "English-US.Female-1",
    "text"           : "Input text from which to generate speech."
}
```

Response is an OGG vorbis audio stream.

### POST /tts_batch

Synthesize text using Riva TTS in batch mode.  In batch mode, audio is not returned until the full audio sequence for the requested text is generated and can achieve higher throughput.

Request JSON body:

```
{
    "voice_name"     : "English-US.Female-1",
    "text"           : "Input text from which to generate speech."
}
```

Response is an OGG vorbis audio stream.