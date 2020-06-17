
# Use official ubuntu base image
FROM ubuntu:16.04

# enables print in docker logs 
ENV PYTHONUNBUFFERED=0
ARG DEBIAN_FRONTEND=noninteractive

# Update package list and isntall pacman
RUN apt -y update
RUN apt install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt -y update

# Install python 3.8
RUN apt install -y python3.6
RUN apt install -y python3.6-dev
RUN apt install -y python3.6-venv

# Install pip
WORKDIR /workdir
RUN apt install -y wget
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3.6 get-pip.py

RUN python3.6 --version | cat

# Install clips
RUN apt install -y clips

# Install akashic 
COPY . /usr/src/app
RUN python3.6 -m pip install -e /usr/src/app

# Set app workdir
WORKDIR /usr/src/app/akashic/webapi

CMD ["python3.6","-u","wsgi.py"]