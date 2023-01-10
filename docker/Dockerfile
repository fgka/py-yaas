## BASE_IMAGE must be a python3.10+ supporting image
ARG BASE_IMAGE="python:buster"
FROM ${BASE_IMAGE}

## Source: https://github.com/phusion/baseimage-docker/issues/58
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

## Transfer the wheel
ARG DIST_DIR
ENV ENV_DIST_DIR ${DIST_DIR}
RUN echo "Dest dir <${ENV_DIST_DIR}>"
COPY ${DIST_DIR}/*.whl ./

## Install the target package
ARG PIP_INSTALL_ARG
ENV ENV_PIP_INSTALL_ARG ${PIP_INSTALL_ARG}
RUN echo "PIP install arg <${ENV_PIP_INSTALL_ARG}>"
RUN python3 -m pip install "${PIP_INSTALL_ARG}"

## Clean-up pip cache
RUN python3 -m pip cache purge

## Runtime definitions
ENV PORT=8080
ENV FLASK_APP=yaas.entry_point.flask_gunicorn:APPLICATION

## Start daemon
CMD gunicorn --bind ":${PORT}" --workers 1 --threads 8 --timeout 0 ${FLASK_APP}
