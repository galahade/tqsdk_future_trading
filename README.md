## Python 版本管理

使用 pyenv 安装python 3.9

使用pipenv创建虚拟环境管理包

## 初始化命令

```
pipenv --python 3.9.
pipenv install tqsdk
```
### 本机测试
#### 运行命令
```
# 回测命令
python main.py -t -s 2018 -m 1 -tt 0

# 正式交易命令
python main.py
```

#### 环境变量
```
export MONGO_ADMINUSERNAME='root'
export MONGO_ADMINPASSWORD='example'
export MONGO_PORT=27017
```

## Docker Command

```
docker build --tag galahade/future-trade-docker .
docker build --no-cache --tag galahade/future-trade-docker .
docker run -e TZ=Asia/Shanghai --rm -ti galahade/future-trade-docker /bin/bash
docker run --rm -ti galahade/future-trade-docker /bin/bash

```

### Docker Compose Command
```
docker-compose up -d
docker-compose down
```
