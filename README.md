# Riva GRPC to HTTP JSON API Proxy

Avoid GRPC protocol in clients by hiding it under an HTTP JSON proxy, making it easier to fast-prototype.

This project implements the streaming interface to Riva to get the data out as soon as possible,
This approach results in lower latency to first audio at the cost of lower throughput.

## Prerequisites

* Docker
* [Nvidia Riva](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/quick-start-guide.html)

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

Request JSON body:

```
{
    "voice_name"     : "English-US.Female-1",
    "text"           : "Input text from which to generate speech."
}
```

Response is an OGG vorbis audio stream.