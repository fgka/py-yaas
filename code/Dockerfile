FROM --platform=linux/amd64 python:buster

# Source: https://github.com/phusion/baseimage-docker/issues/58
ENV DEBIAN_FRONTEND noninteractive

## Required for GCloud CLI install
RUN apt-get update \
  && apt-get -y install apt-utils \
  && apt-get -y upgrade \
  && apt-get -y install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg

## Install Python3 and clean-up APT for cleaner/smaller images
RUN apt-get update \
  && apt-get -y upgrade \
  && apt-get -y install \
    python3 \
    python3-pip \
  && apt-get -y autoclean

ENV WHEEL_FILE py_yaas_playground-1.0-py2.py3-none-any.whl

COPY dist/${WHEEL_FILE} ./

RUN python3 -m pip install ./${WHEEL_FILE}
