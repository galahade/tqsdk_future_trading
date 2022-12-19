## Docker Command

```
# Apple M1 build command
docker buildx build --platform linux/amd64 -t  galahade/future-trade-docker .
docker build --tag galahade/future-trade-docker .
docker build --no-cache --tag galahade/future-trade-docker .
docker run -e TZ=Asia/Shanghai --rm -ti galahade/future-trade-docker /bin/bash
docker run --rm -ti galahade/future-trade-docker /bin/bash

docker tag galahade/future-trade-docker galahade/future-trade-docker:v1.2
```
### Build test image

```
docker build --tag galahade/future-trade-test-docker .
docker tag galahade/future-trade-test-docker galahade/future-trade-test-docker:v1.0
```

### Docker Compose Command

```
docker-compose up -d
docker-compose down
```

### Docker swarm Command

```
docker stack deploy -c docker-compose.yml future-trade-dev
docker stack deploy -c docker-compose-test.yml future-trade-test
docker stack deploy -c docker-compose-deploy.yml future-trade

docker stack deploy -c docker-compose-backtest.yml future-trade-backtest

docker stack rm future-trade-dev
docker stack rm future-trade-test
docker stack rm future-trade-backtest
```

### Docker create a log volume

```
docker volume create future-trade-log-data

docker run -it -v future-trade-log-data:/log --rm bash:4.4

```
