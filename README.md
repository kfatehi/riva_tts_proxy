# Riva GRPC to HTTP JSON API Proxy

Avoid GRPC protocol in clients by hiding it under an HTTP JSON proxy, making it easier to fast-prototype.

## Prerequisites

* Docker
* [Nvidia Riva](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/quick-start-guide.html)

## Usage

Start the server. Be sure to forward port 5000 to somewhere on your host.

```
docker run --rm -p 5000:5000 -t riva_tts_proxy
```

## Configuration

The system will not work without a functional Riva stack. By default, this is expected to run on the same docker host. To change this, you may configure the RIVA_URI environment variable.

You may also wish to increase the amount of web workers. This is possible using the WEB_CONCURRENCY environment variable.

## Building

You may build the image like so:

```
docker build -t riva_tts_proxy .
```

## Endpoints

### POST /tts

Request JSON body:

```
{
    "voice_name"     : "English-US.Female-1",
    "text"           : "Input text from which to generate speech."
}
```

Optionally, you may pass in "pitch" which should be a number between 0 and 2. Internally it will be scaled to the [range expected by Riva](https://docs.nvidia.com/deeplearning/riva/archives/2-1-0/user-guide/docs/tutorials/tts-python-advanced-customizationwithssml.html#pitch-attribute) using numpy.

Response JSON body:
```
{
    "path": "/path/to/wav"
}
```

This route also accepts a GET request in a format like that of IBM Watson.
This was implemented in order to support this integration with the [ReadAloud browser extension](https://readaloud.app/).
See the related pull request here: https://github.com/ken107/read-aloud/pull/321