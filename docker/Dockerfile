ARG BASE_IMAGE="python:buster"

FROM ${BASE_IMAGE}

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
  && apt-get -y autoclean \

ARG PIP_INSTALL_ARG=./py_yaas_playground-1.0-py2.py3-none-any.whl
ARG PIP_INDEX_URL=""

COPY dist/*.whl ./

ENV PIP_INDEX_URL=${PIP_INDEX_URL}

RUN python3 -m pip install ${PIP_INSTALL_ARG}

ENV FLASK_APP=yaas.entry_point.flask_gunicorn:APPLICATION

CMD gunicorn --bind ":${PORT}" --workers 1 --threads 8 --timeout 0 ${FLASK_APP}
