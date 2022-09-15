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

### 融航系统信息

```
account:wxlg018
password:345678
BrokerID:RohonReal
app_id:MQT_MQT_1.0
auto_code:mVuQfsHT3qbTBEYV
交易地址：139.196.40.170:11001
电信行情地址：180.168.212.232:41214
联通行情地址：27.115.78.184:41214
随心易多账户平台编码：100170
```
