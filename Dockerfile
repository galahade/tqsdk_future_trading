# syntax=docker/dockerfile:1

FROM python:3.9-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
ENV TZ Asia/Shanghai

COPY . .
CMD [ "python3", "main.py", "-t", "-s", "2018", "-tt", "1"]


