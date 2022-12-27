## Docker Command

```
# Apple M1 build command
docker buildx build --platform linux/amd64 -t  galahade/future-trade-dev.
docker build --tag galahade/future-trade-dev .
docker build --no-cache --tag galahade/future-trade-dev .
docker run -e TZ=Asia/Shanghai --rm -ti galahade/future-trade-dev /bin/bash
docker run --rm -ti galahade/future-trade-dev /bin/bash

docker tag galahade/future-trade-dev galahade/future-trade-dev:v1.2
```
### Build test image

* v1.**** 代表使用tqsdk 作为底层工具
* v2.* 代表使用tqsdk2 作为底层工具

因为tqsdk2 无法在苹果M1-2平台运行，故需要针对不同平台使用不同docker版本。
```
docker build --tag galahade/future-trade-test .
docker tag galahade/future-trade-test galahade/future-trade-test:v1.1
docker tag galahade/future-trade-test galahade/future-trade-test:v2.0
```

### Build prod image

* v1.**** 代表使用tqsdk 作为底层工具
* v2.* 代表使用tqsdk2 作为底层工具

因为tqsdk2 无法在苹果M1-2平台运行，故需要针对不同平台使用不同docker版本。
```
docker build --tag galahade/future-trade-prod .
docker tag galahade/future-trade-prod galahade/future-trade-prod:v1.1
docker tag galahade/future-trade-prod galahade/future-trade-prod:v2.0

### Docker Compose Command

```
docker-compose up -d
docker-compose down
```

### Docker swarm Command

```
docker stack deploy -c docker-compose.yml future-trade-dev
docker stack deploy -c docker-compose-test.yml future-trade-test
docker stack deploy -c docker-compose-prod.yml future-trade

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

### Backtest deploy

1. 首先使用`docker-compose-backtest-db.yml`部署回测数据库主机
    ```
    docker stack deploy -c docker-compose-backtest-db.yml backtest-db
    ```
2.
修改`conf/trade_config_backtest.yaml`中需要进行回测的品种的，分别使用`docker-compose-backtest.yml'部署回测执行主机。
    ```
    docker stack deploy -c docker-compose-backtest.yml backtest1
    ```
3. 记录每个回测使用的数据库名称，使用命令将结果导出到excel文件。
    ```
    python generate_excel.py -n DB_NAME -p 27016
    ```
