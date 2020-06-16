
# Use official ubuntu base image
FROM ubuntu:16.04

# set to noninteractive mode 
ARG DEBIAN_FRONTEND=noninteractive

# Update package list and isntall pacman
RUN apt-get update -y

# Install python 3.8 and pip
RUN apt-get install -y python3-pip

# Install clips
RUN apt-get install -y clips

# Install akashic 
COPY . /usr/src/app
RUN pip3 install -e /usr/src/app

# Install gunnicorn
RUN pip3 install gunicorn

# Set app workdir
WORKDIR /usr/src/app/akashic/webapi