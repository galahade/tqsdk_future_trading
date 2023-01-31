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
* `ACCOUNT_BALANCE`: 计算开仓手数的虚拟资金额。缺省值为一千万。

#### unix like 系统配置

在`Mac_OS`或`Linux`系统中，可以使用命令配置以上环境变量：

```
export MONGO_CONF_FILE=secrets/mongo_conf_file
export TQ_CONF_FILE=secrets/tq_conf_file
export ROHON_CONF_FILE=secrets/rohon_conf_file
exprot ACCOUNT_TYPE=1
exprot ACCOUNT_BALANCE=100000
```

`docker`在`compse`文件中配置环境变量，具体方法参考相关`docker-compse`文件.

### 配置文件

#### 交易信息配置

交易相关初始化信息在`conf/trade_config*.yaml`文件中存储。包括：交易品种，交易参数。

其中：

* `defaults`中是所有品种一致的参数，包括：

  * `switch_days`: 换月周期，第一项为当前合约有成交距离交割日的期限。第二项为当前合约没有成交距离交割日的期限。

  * `long`: 做多需要用到的参数。包括：

    * `base_scale`: 止盈/损的基本百分比。
    * `stop_loss_scale`: 止损价格在基本百分比上浮动的倍数。
    * `profit_start_scale_1`:开始需要监控止盈条件1的价格在基本百分比上浮动的倍数。
    * `profit_start_scale_2`: 开始需要监控止盈条件2的价格在基本百分比上浮动的倍数。

    * `promote_scale_1`: 提高止损条件1的价格在基本百分比上浮动的倍数。
    * `promote_scale_2`: 提高止损条件2的价格在基本百分比上浮动的倍数。
    * `promote_target_1`: 达到提高止损条件1的价格后，需要将止损价格提高到的价格在基本百分比上浮动的倍数。
    * `promote_target_2`: 达到提高止损条件2的价格后，需要将止损价格提高到的价格在基本百分比上浮动的倍数。

  * `short`: 做空需要用到的参数。包括：

    * `base_scale`: 止盈/损的基本百分比。
    * `stop_loss_scale`: 止损价格在基本百分比上浮动的倍数。
    * `profit_start_scale `: 开始需要监控止盈的价格在基本百分比上浮动的倍数。

    * `promote_scale`: 提高止损的价格在基本百分比上浮动的倍数。
    * `promote_target`: 达到提高止损的价格后，需要将止损价格提高到的价格在基本百分比上浮动的倍数。

* `open_pos_scale`: 单个品种开仓使用的保证金，占资金总量的比例。

* `futures`: 需要监控和交易的具体期货品种及相关参数：

  * `symbol`: 期货品种的天勤主连合约代码
  * `name`: 期货品种名称
  * `is_active`: 是否交易该品种
  * `contract_m`: 合约乘数
  * `switch_days`: 换月距离交割日的期限
  * `long`: 做多相关参数
  * `short`: 做空相关参数

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

    ```
    # 使用默认配置
    python init_db.py -p 27010 -l localhost -u root -s example
    
    python init_db.py -p 27010 -l localhost -u root -s example -n bottom_future_trade -c trade_config_young.yaml
    ```

    其中：

    * `-p, --port`: 默认值：27017, 指定数据库端口号
    * `-l, --host`: 默认值：localhost, 指定数据库地址 
    * `-u, --user`: 默认值：root, 指定数据库用户名
    * `-s, --password`: 默认值：example, 指定数据库密码
    * `-n, --name`: 默认值：future_trade, 指定数据库集合名称
    * `-c, --configfile`: 默认值：trade_config.yaml, 要导入数据库的配置文件名

4. 将回测数据导出到Excel表中

    `python generate_excel.py -n fa9bd35c-d99f-4296-b884-3322c0defb46 -p 27016`

    * `-p, --port`: 默认值：27017, 指定数据库端口号
    * `-l, --host`: 默认值：localhost, 指定数据库地址 
    * `-u, --user`: 默认值：root, 指定数据库用户名
    * `-s, --password`: 默认值：example, 指定数据库密码
    * `-n, --name`: 默认值：future_trade, 指定数据库集合名称

## 部署

系统使用`Docker stack`进行部署。[详细命令见README_CMD](README_CMD.md)
