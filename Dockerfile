FROM ubuntu:22.04
ARG DEBIAN_FRONTEND=noninteractive
ARG TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get update
RUN apt install -y curl wget git
RUN adduser --disabled-password --gecos '' --shell /bin/bash user
USER user
ENV HOME=/home/user
WORKDIR $HOME
RUN mkdir $HOME/.cache $HOME/.config && chmod -R 777 $HOME
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-py310_23.1.0-1-Linux-x86_64.sh
RUN chmod +x Miniconda3-py310_23.1.0-1-Linux-x86_64.sh
RUN ./Miniconda3-py310_23.1.0-1-Linux-x86_64.sh -b -p /home/user/miniconda
ENV PATH="$HOME/miniconda/bin:$PATH"
RUN conda init
RUN conda install python=3.10.10
RUN python3 -m pip install --upgrade pip
RUN pip install numpy
RUN pip install nvidia-riva-client
RUN pip install flask
RUN pip install ffmpeg-python
USER root
RUN apt update
RUN apt install -y ffmpeg
USER user
ADD . app
WORKDIR app
ENV PORT=5000
EXPOSE 5000
CMD ["python", "main.py"]
