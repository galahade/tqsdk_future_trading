# 期货自动化检测交易系统

该系统使用天勤量化提供的`tqsdk`包作为后台交易工具。交易策略为我公司在多年中期交易策略的基础上自主研发。适用于各种品种的期货品种。

## 运行系统

### 系统要求

* python 使用`3.9`版

* 最新版的`tqsdk`

* `mangoDB`的支持

### 环境变量

* `MONGO_CONF_FILE`: `mongo`数据库相关信息配置文件位置
* `TQ_CONF_FILE`: 天勤账户相关信息配置文件位置
* `ROHON_CONF_FILE`: 融航账户相关信息配置文件位置
* `ACCOUNT_TYPE`: 交易用户类型：
  * 0: 测试用户
  * 1: 融航用户
  * 2: 个人用户

#### unix like 系统配置

在`Mac_OS`或`Linux`系统中，可以使用命令配置以上环境变量：

```
export MONGO_CONF_FILE=secrets/mongo_conf_file
export TQ_CONF_FILE=secrets/tq_conf_file
export ROHON_CONF_FILE=secrets/rohon_conf_file
exprot ACCOUNT_TYPE=1
```

`docker`在`compse`文件中配置环境变量，具体方法参考相关`docker-compse`文件.

### 运行命令

该系统可以运行在**两种模式**下：

1. 回测：根据过去某段时间的数据测试某些品种的收益率。

   `python main.py -t -s 2018 -m 1 -tt 0`

   其中：

   * `-t`指定系统运行在回测模式中。**必填**
   * `-y` 指定回测开始的年份。**必填**
   * `-m` 指定回测开始的月份。默认值为1
   * `-tt` 指定回测类型：
     * 0: 做空
     * 1: 做多
     * 2: 多空

2. 实时监测：在交易时段运行，监测实时数据，根据策略进行开仓操作。

```
python main.py
```

3. 导入配置数据: 将期货交易初始配置数据导入数据库中：

    `python init_db.py -p 27018 -h localhost -u root -p example -n future_trade`

    其中：

    * `-p, --port`: 默认值：27017, 指定数据库端口号
    * `-l, --host`: 默认值：localhost, 指定数据库地址 
    * `-u, --user`: 默认值：root, 指定数据库用户名
    * `-s, --password`: 默认值：example, 指定数据库密码
    * `-n, --name`: 默认值：future_trade, 指定数据库集合名称

4. 将回测数据导出到Excel表中

    `python generate_excel.py -n fa9bd35c-d99f-4296-b884-3322c0defb46 -p 27016`

    * `-p, --port`: 默认值：27017, 指定数据库端口号
    * `-l, --host`: 默认值：localhost, 指定数据库地址 
    * `-u, --user`: 默认值：root, 指定数据库用户名
    * `-s, --password`: 默认值：example, 指定数据库密码
    * `-n, --name`: 默认值：future_trade, 指定数据库集合名称

## 部署

系统使用`Docker stack`进行部署。[详细命令见README_CMD](README_CMD.md)
