# Docker file for a slim Ubuntu-based Python3 image

FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV PACKAGE=Code-a-saurus-Rex/aws_launch_control
ENV VERSION=develop_v1
ARG GITHUB_PAT

RUN apt-get update \
  && apt-get install -y python3-pip python3-dev \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip

RUN apt-get install -y git

##install package via github
RUN pip install git+https://${GITHUB_PAT}@github.com/${PACKAGE}.git@${VERSION}

# ENTRYPOINT ["python3"]