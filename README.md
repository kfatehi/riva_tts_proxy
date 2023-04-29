# Riva GRPC to HTTP JSON API Proxy

Avoid GRPC protocol in clients by hiding it under an HTTP JSON proxy, making it easier to fast-prototype.

## Prerequisites

* Docker
* [Nvidia Riva](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/quick-start-guide.html)

## Usage

build the server's image with `./build.sh`

start the server with `./run.sh` (or run it with the python code easily editable by using `./hack.sh`)

make a test request with: `./test.sh`

## Endpoints

### POST /tts

Request JSON body:

```
{
    "language_code"  : "en-US",
    "voice_name"     : "English-US.Female-1",
    "text"           : "Input text from which to generate speech."
}
```

Response JSON body:
```
{
    "path": "/path/to/wav"
}
```

