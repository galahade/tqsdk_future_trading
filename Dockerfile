# syntax=docker/dockerfile:1
FROM  --platform=$BUILDPLATFORM python:3.10-bullseye
WORKDIR /app

COPY requirements.txt requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt
ENV TZ Asia/Shanghai

COPY . .

ENTRYPOINT ["python3"]
CMD ["main.py"]
