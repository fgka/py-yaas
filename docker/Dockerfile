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

## Debug
RUN echo "Content to install"
RUN ls -l ./*.whl

# Install the target package
RUN python3 -m pip install *.whl

## Clean-up pip cache
RUN python3 -m pip cache purge

## Copy gunicorn starter script
ARG CR_CONCURRENCY
ENV ENV_CR_CONCURRENCY ${CR_CONCURRENCY}

ADD docker/scripts/start_gunicorn.sh ./
RUN chmod 755 ./start_gunicorn.sh

## Runtime definitions
ARG PY_PACKAGE="yaas_scheduler_service"
ENV FLASK_APP=${PY_PACKAGE}.main:APPLICATION

## Start daemon
CMD ./start_gunicorn.sh ${FLASK_APP}
