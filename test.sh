#!/bin/bash
set -exuo pipefail
origin="http://localhost:5000"
out=$(curl -H"Content-Type: application/json" -d'{"text":"hello world"}' "$origin/tts")
url="$origin/$(echo $out | jq -r '.path')"
echo $url
ffplay "$url"