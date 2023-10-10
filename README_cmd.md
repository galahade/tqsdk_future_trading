# 构建运行环境

## 构建镜像文件

### 构建开发/回测镜像

开发过程中，使用以下命令构建运行环境，对代码进行测试

```
# Apple M1 build command
docker buildx build --platform linux/amd64 -t  galahade/future-trade-dev.
# 使用缓存构建image
docker build --tag galahade/future-trade-dev .
# 不使用缓存，从头构建image
docker build --no-cache --tag galahade/future-trade-dev .
# 构建完成镜像后进行连接测试
docker run -e TZ=Asia/Shanghai --rm -ti galahade/future-trade-dev /bin/bash
docker run --rm -ti galahade/future-trade-dev /bin/bash
# 对镜像打标签
docker tag galahade/future-trade-dev galahade/future-trade-dev:v1.2
```
### 构建测试镜像

当开发工作完成后，将代码提交到`main`分支，然后构建测试环境，用来监测各品种的开仓情况。

* **v1.** 代表使用tqsdk 作为底层工具
* **v2.** 代表使用tqsdk2 作为底层工具

因为tqsdk2 无法在苹果M1-2平台运行，故需要针对不同平台使用不同docker版本。
```
docker build --tag galahade/future-trade-test .
docker tag galahade/future-trade-test galahade/future-trade-test:v1.1
docker tag galahade/future-trade-test galahade/future-trade-test:v2.0
```

### 构建生产镜像

该环境用来进行实盘交易，需要配置交易信息，以实现自动化交易。

* **v1.** 代表使用tqsdk 作为底层工具
* **v2.** 代表使用tqsdk2 作为底层工具

因为tqsdk2 无法在苹果M1-2平台运行，故需要针对不同平台使用不同docker版本。
```
docker build --tag galahade/future-trade-prod .
docker tag galahade/future-trade-prod galahade/future-trade-prod:v1.1
docker tag galahade/future-trade-prod galahade/future-trade-prod:v2.0
```

## 部署运行环境

运行环境均使用 **Docker Swarm** 进行部署。

在部署前，需要做的准备工作：

### 创建Docker volume

```
docker volume create future-trade-log-data
# 查看 volume 内容的命令
docker run -it -v future-trade-log-data:/log --rm bash:4.4
```

### 部署运行环境

```
# 开发环境
docker stack deploy -c docker-compose.yml main-trade-dev
docker stack rm main-trade-dev

# 回测环境
docker stack deploy -c docker-compose-backtest.yml main-trade-backtest
docker stack rm main-trade-backtest

# 测试环境
docker stack deploy -c docker-compose-test.yml main-trade-test
docker stack rm main-trade-test

# 生产环境
docker stack deploy -c docker-compose-prod.yml main-trade
docker stack rm main-trade

# 特殊环境
docker stack deploy -c docker-compose-young.yml main-trade-young
docker stack rm main-trade-young
```

#### 部署回测环境

回测环境根据其特点有专门的部署步骤

1. 首先使用`docker-compose-backtest-db.yml`部署回测数据库主机

   ```
   docker stack deploy -c docker-compose-backtest-db.yml main-backtest-db
   ```

2. 修改`conf/trade_config_backtest.yaml`中需要进行回测的品种的，使用`docker-compose-backtest.yml`加不同名称为每个品种部署回测环境。

   ```
   docker stack deploy -c docker-compose-backtest.yml main-backtest-1
   docker stack rm main-backtest-1
   ```

3. 在日志中找到并记录每个回测环境使用的数据库名称，使用以下命令将结果导出到excel文件。

   ```
   python generate_excel.py -p 27016 -n DB_NAME 
   ```
