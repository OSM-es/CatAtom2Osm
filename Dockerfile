FROM ubuntu:18.04

LABEL maintainer="emilio.gomez.fdez@gmail.com"

ARG REQUISITES="requisites.txt"
ARG user=catastro
ARG group=catastro
ARG uid=1000
ARG gid=1000
ARG home=/catastro

# System deps
ENV APP_PATH=/opt/CatAtom2Osm
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y \
  && apt-get upgrade -y \
  && apt-get install -y language-pack-es-base language-pack-ca-base \
    language-pack-gl-base language-pack-eu-base python python-pip git qgis nano
ENV LANG=es_ES.UTF-8
ENV PYTHONIOENCODING=utf-8
ENV QT_QPA_PLATFORM=offscreen

# Create application user and home
RUN mkdir -p "$home" && chown $uid:$gid "$home" \
  && addgroup --gid $gid $group \
  && useradd -d "$home" -u $uid -g $group -s /bin/bash $user
RUN mkdir -p "/tmp/runtime-$user" && chown $uid:$gid "/tmp/runtime-$user"
ENV XDG_RUNTIME_DIR="/tmp/runtime-$user"

# Copy only requirements to cache them in docker layer
WORKDIR $APP_PATH
COPY $REQUISITES ./
RUN pip install -r $REQUISITES

# Install app
COPY . .
RUN make install
RUN chown -R $user:$group $APP_PATH

USER $user
WORKDIR $home
