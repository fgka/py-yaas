## BASE_IMAGE must be a python3.10+ supporting image
ARG BASE_IMAGE="python:buster"
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}

## Source: https://github.com/phusion/baseimage-docker/issues/58
ENV DEBIAN_FRONTEND noninteractive

## Required for GCloud CLI install
# hadolint ignore=DL3008
RUN apt-get update \
  && apt-get --no-install-recommends --yes install apt-utils \
  && apt-get --yes upgrade \
  && apt-get --no-install-recommends --yes install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
  && apt-get --yes autoclean \
  && rm -rf /var/lib/apt/lists/*

## Install Python3 and clean-up APT for cleaner/smaller images
# hadolint ignore=DL3008
RUN apt-get update \
  && apt-get --yes upgrade \
  && apt-get --no-install-recommends --yes install \
    python3 \
    python3-pip \
  && apt-get --yes autoclean \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /

## Transfer the wheel
ARG DIST_DIR
ENV ENV_DIST_DIR ${DIST_DIR}
RUN echo "Dest dir '${ENV_DIST_DIR}'"
COPY ${DIST_DIR}/*.whl ./

## Install the target package
RUN echo "Content to install" \
    && ls -l ./*.whl \
    && python3 -m pip install --no-cache-dir ./*.whl \
    && python3 -m pip cache purge

## Copy gunicorn starter script
ARG CR_CONCURRENCY
ENV ENV_CR_CONCURRENCY ${CR_CONCURRENCY}

COPY docker/scripts/start_gunicorn.sh ./
RUN chmod 755 ./start_gunicorn.sh

## Runtime definitions
ARG PY_PACKAGE="yaas_scheduler_service"
ENV FLASK_APP=${PY_PACKAGE}.main:APPLICATION

## Start daemon
CMD ["sh", "-c", "./start_gunicorn.sh ${FLASK_APP}"]
