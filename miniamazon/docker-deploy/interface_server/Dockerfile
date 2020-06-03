FROM python:3
ENV PYTHONUNBUFFERED 1
# FROM ubuntu:18.04
# RUN apt-get update \
#     && apt-get install -y python3-pip python3-dev libpq-dev \
#     && cd /usr/local/bin \
#     && ln -s /usr/bin/python3 python \
#     && pip3 install --upgrade pip
RUN mkdir /interface_server
WORKDIR /interface_server
ADD requirements.txt /interface_server
RUN pip3 install -r requirements.txt
ADD . /interface_server