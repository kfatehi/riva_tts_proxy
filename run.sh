#!/bin/bash
mkdir -p $PWD/public
docker run --rm -v $PWD/public:/home/user/app/public \
    -e RIVA_URI="172.17.0.1:50051" -p 5000:5000 -t riva_tts_proxy