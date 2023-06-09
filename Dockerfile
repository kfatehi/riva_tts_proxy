FROM python:alpine3.17
RUN apk add --no-cache gcc g++ make python3-dev ffmpeg-dev && \
    pip3 --no-cache-dir install nltk numpy nvidia-riva-client flask av gunicorn retry && \
    apk del python3-dev make g++ gcc
RUN python -c "import nltk;nltk.download('punkt')"
ADD . /app
WORKDIR /app
ENV PORT 5000
ENV WEB_CONCURRENCY 1
ENV RIVA_URI host.docker.internal:50051
EXPOSE 5000
CMD exec gunicorn app:app